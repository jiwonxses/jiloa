from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_model = None

def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    return _model

def get_db():
    try:
        return psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            dbname=os.environ.get("DB_NAME", "movies"),
            user=os.environ.get("DB_USER", "jiwonie"),
            password=os.environ.get("DB_PASS", "")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur BDD : {str(e)}")

def fix_poster(url):
    if url and not url.startswith('http'):
        return f"https://image.tmdb.org/t/p/w500{url}"
    return url

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


@app.on_event("startup")
def create_extra_tables():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL
        );
        CREATE TABLE IF NOT EXISTS user_favorite (
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            movie_id INTEGER REFERENCES movie(id) ON DELETE CASCADE,
            PRIMARY KEY (user_id, movie_id)
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()


# ──────────────────────────────────────────
# MOVIES
# ──────────────────────────────────────────

@app.get("/hello")
def hello():
    return {"message": "Hello World, mon API est connectée à ma BDD !"}


@app.get("/movies/popular")
def get_popular(limit: int = Query(default=20, ge=1, le=100)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT id, title, date_publication, overview, poster, vote_average, popularity
            FROM movie
            WHERE popularity IS NOT NULL
            ORDER BY popularity DESC
            LIMIT %s
        """, (limit,))
        movies = cursor.fetchall()
        for m in movies:
            m['poster'] = fix_poster(m['poster'])
        return movies
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.get("/movies/recommended")
def get_recommended(limit: int = Query(default=20, ge=1, le=100)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT id, title, date_publication, overview, poster, vote_average, popularity
            FROM movie
            WHERE vote_average IS NOT NULL AND vote_count > 100
            ORDER BY vote_average DESC
            LIMIT %s
        """, (limit,))
        movies = cursor.fetchall()
        for m in movies:
            m['poster'] = fix_poster(m['poster'])
        return movies
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.get("/movies/search")
def search_movies(
    title: str | None = Query(None, description="Recherche partielle par titre"),
    genre: str | None = Query(None, description="Filtrer par nom de genre (ex: Action)"),
    year: int | None = Query(None, description="Filtrer par année de sortie"),
    limit: int = Query(default=20, ge=1, le=100)
):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = "SELECT DISTINCT m.id, m.title, m.date_publication, m.overview, m.poster, m.vote_average FROM movie m"
    filters = []
    params = []

    if genre:
        query += " JOIN movie_genre mg ON m.id = mg.movie_id JOIN genre g ON mg.genre_id = g.id"
        filters.append("g.genre ILIKE %s")
        params.append(f"%{genre}%")

    if title:
        filters.append("m.title ILIKE %s")
        params.append(f"%{title}%")

    if year:
        filters.append("EXTRACT(YEAR FROM m.date_publication) = %s")
        params.append(year)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY m.vote_average DESC NULLS LAST LIMIT %s"
    params.append(limit)

    try:
        cursor.execute(query, params)
        movies = cursor.fetchall()
        for m in movies:
            m['poster'] = fix_poster(m['poster'])
        return movies
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.get("/movies/search/synopsis")
def search_by_synopsis(q: str = Query(...), limit: int = Query(default=20, ge=1, le=100)):
    model = get_model()
    embedding = model.encode(q)

    conn = get_db()
    from pgvector.psycopg2 import register_vector
    register_vector(conn)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT id, title, date_publication, overview, poster, vote_average,
                   embedding_synopsis <=> %s AS distance
            FROM movie
            WHERE embedding_synopsis IS NOT NULL
            ORDER BY distance ASC
            LIMIT %s
        """, (embedding, limit))
        movies = cursor.fetchall()
        for m in movies:
            m['poster'] = fix_poster(m['poster'])
            m.pop('distance', None)
        return movies
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.get("/movies/{movie_id}")
def get_movie(movie_id: int):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT id, title, date_publication, overview, poster, vote_average, popularity
            FROM movie WHERE id = %s
        """, (movie_id,))
        movie = cursor.fetchone()
        if not movie:
            raise HTTPException(status_code=404, detail="Film non trouvé")

        cursor.execute("""
            SELECT g.genre FROM genre g
            JOIN movie_genre mg ON g.id = mg.genre_id
            WHERE mg.movie_id = %s
        """, (movie_id,))
        movie['genres'] = [row['genre'] for row in cursor.fetchall()]
        movie['poster'] = fix_poster(movie['poster'])
        return movie
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.get("/movies/{movie_id}/similar")
def get_similar(movie_id: int, limit: int = Query(default=12, ge=1, le=50)):
    conn = get_db()
    from pgvector.psycopg2 import register_vector
    register_vector(conn)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT id, title, date_publication, overview, poster, vote_average,
                   embedding_synopsis <=> (SELECT embedding_synopsis FROM movie WHERE id = %s) AS distance
            FROM movie
            WHERE id != %s AND embedding_synopsis IS NOT NULL
            ORDER BY distance ASC
            LIMIT %s
        """, (movie_id, movie_id, limit))
        movies = cursor.fetchall()
        for m in movies:
            m['poster'] = fix_poster(m['poster'])
            m.pop('distance', None)
        return movies
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# ──────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────

class AuthBody(BaseModel):
    username: str
    password: str


@app.post("/auth/register")
def do_register(body: AuthBody):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id, username",
            (body.username, hash_password(body.password))
        )
        conn.commit()
        return cursor.fetchone()
    except psycopg2.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Ce nom d'utilisateur existe déjà")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.post("/auth/login")
def do_login(body: AuthBody):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Check if username exists
        cursor.execute("SELECT id, username, password FROM users WHERE username = %s", (body.username,))
        existing = cursor.fetchone()

        if existing is None:
            # First time: auto-create the account
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id, username",
                (body.username, hash_password(body.password))
            )
            conn.commit()
            return cursor.fetchone()

        # Account exists: check password
        if existing['password'] != hash_password(body.password):
            raise HTTPException(status_code=401, detail="Mot de passe incorrect")

        return {"id": existing['id'], "username": existing['username']}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# ──────────────────────────────────────────
# FAVORIS
# ──────────────────────────────────────────

@app.get("/users/me/favorites")
def get_favorites(user_id: int = Query(...)):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT m.id, m.title, m.date_publication, m.overview, m.poster, m.vote_average
            FROM movie m
            JOIN user_favorite uf ON m.id = uf.movie_id
            WHERE uf.user_id = %s
        """, (user_id,))
        movies = cursor.fetchall()
        for m in movies:
            m['poster'] = fix_poster(m['poster'])
        return movies
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.post("/users/me/favorites/{movie_id}")
def add_favorite(movie_id: int, user_id: int = Query(...)):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO user_favorite (user_id, movie_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (user_id, movie_id)
        )
        conn.commit()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.delete("/users/me/favorites/{movie_id}")
def remove_favorite(movie_id: int, user_id: int = Query(...)):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM user_favorite WHERE user_id = %s AND movie_id = %s",
            (user_id, movie_id)
        )
        conn.commit()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

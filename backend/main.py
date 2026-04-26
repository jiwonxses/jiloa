from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fonction pour obtenir une connexion à la base de données
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            dbname=os.environ.get("DB_NAME", "movies"),
            user=os.environ.get("DB_USER", "jiwonie"),
            password=os.environ.get("DB_PASS", "")
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de connexion à la BDD : {str(e)}")

@app.get("/hello")
def hello():
    return {"message": "Hello World, mon API est connectée à ma BDD !"}

@app.get("/movies/search")
def search_movies(
    title: str | None = Query(None, description="Recherche partielle par titre"),
    genre: str | None = Query(None, description="Filtrer par nom de genre (ex: Action)"),
    year: int | None = Query(None, description="Filtrer par année de sortie"),
    limit: int = Query(default=12, ge=1, le=100)
):
    """
    Retourne une liste de films depuis TA base de données locale.
    Construit la requête SQL dynamiquement selon les filtres fournis.
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # La base de la requête. On utilise DISTINCT au cas où les jointures créent des doublons
    query = """
        SELECT DISTINCT m.id, m.original_title, m.date_publication, m.overview, m.poster, m.vote_average
        FROM movie m
    """
    
    filters = []
    params = []

    # 1. Si on filtre par genre, il faut faire les jointures (Many-to-Many)
    if genre:
        query += """
            JOIN movie_genre mg ON m.id = mg.movie_id
            JOIN genre g ON mg.genre_id = g.id
        """
        filters.append("g.genre ILIKE %s") # ILIKE = insensible à la casse
        params.append(f"%{genre}%")

    # 2. Si on filtre par titre
    if title:
        filters.append("m.original_title ILIKE %s")
        params.append(f"%{title}%")

    # 3. Si on filtre par année (on extrait juste l'année de la date SQL)
    if year:
        filters.append("EXTRACT(YEAR FROM m.date_publication) = %s")
        params.append(year)

    # 4. Assemblage final de la requête
    if filters:
        query += " WHERE " + " AND ".join(filters)

    # 5. Tri et Limite
    query += " ORDER BY m.vote_average DESC NULLS LAST LIMIT %s"
    params.append(limit)

    try:
        cursor.execute(query, params)
        movies = cursor.fetchall()
        
        # Nettoyage optionnel pour s'assurer que les URLs des posters sont complètes
        for m in movies:
            if m['poster'] and not m['poster'].startswith('http'):
                m['poster'] = f"https://image.tmdb.org/t/p/w500{m['poster']}"
                
        return movies
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur SQL : {str(e)}")
    finally:
        cursor.close()
        conn.close()
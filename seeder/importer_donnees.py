import ast
import csv
import logging
import os
import sys

import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.extras import execute_batch
from sentence_transformers import SentenceTransformer

# === Configuration via variables d'environnement ===
DB_HOST = os.environ["DB_HOST"]
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ["DB_NAME"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]

DATA_DIR = os.environ.get("DATA_DIR", "/data")
MODEL_PATH = os.environ.get("MODEL_PATH", "/app/models/minilm-multilingual")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "500"))
SKIP_VECTORIZATION = os.environ.get("SKIP_VECTORIZATION", "false").lower() == "true"

# === Logging ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("seeder")


# === Idempotence ===
def is_already_initialized(cursor) -> bool:
    cursor.execute("SELECT 1 FROM db_init_status WHERE step = 'full_import';")
    return cursor.fetchone() is not None


def mark_completed(cursor, step: str) -> None:
    cursor.execute(
        "INSERT INTO db_init_status (step) VALUES (%s) ON CONFLICT (step) DO NOTHING;",
        (step,),
    )


# === Importation des films ===
def import_movies(conn, cursor, csv_path: str, batch_size: int = 500) -> None:
    log.info("Importing movies from %s", csv_path)

    movies_buf: list[tuple] = []
    genres_buf: list[tuple] = []
    movie_genres_buf: list[tuple] = []
    countries_buf: list[tuple] = []
    movie_countries_buf: list[tuple] = []
    languages_buf: list[tuple] = []
    movie_languages_buf: list[tuple] = []
    companies_buf: list[tuple] = []
    movie_companies_buf: list[tuple] = []

    inserted = 0
    errors = 0

    def flush() -> None:
        nonlocal inserted

        # Tables parentes d'abord (pour respecter les FK)
        if movies_buf:
            execute_batch(
                cursor,
                "INSERT INTO movie (id, title, date_publication, poster, adult, "
                "overview, popularity, vote_average, vote_count) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (id) DO NOTHING;",
                movies_buf,
                page_size=500,
            )
            inserted += len(movies_buf)
        if genres_buf:
            execute_batch(
                cursor,
                "INSERT INTO genre (id, genre) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;",
                genres_buf, page_size=500,
            )
        if countries_buf:
            execute_batch(
                cursor,
                "INSERT INTO country (id, name_country) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;",
                countries_buf, page_size=500,
            )
        if languages_buf:
            execute_batch(
                cursor,
                "INSERT INTO language (id, name_language) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;",
                languages_buf, page_size=500,
            )
        if companies_buf:
            execute_batch(
                cursor,
                "INSERT INTO company (id, name_company) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;",
                companies_buf, page_size=500,
            )

        # Tables de liaison ensuite
        if movie_genres_buf:
            execute_batch(
                cursor,
                "INSERT INTO movie_genre (movie_id, genre_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
                movie_genres_buf, page_size=500,
            )
        if movie_countries_buf:
            execute_batch(
                cursor,
                "INSERT INTO movie_country (movie_id, country_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
                movie_countries_buf, page_size=500,
            )
        if movie_languages_buf:
            execute_batch(
                cursor,
                "INSERT INTO movie_language (movie_id, language_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
                movie_languages_buf, page_size=500,
            )
        if movie_companies_buf:
            execute_batch(
                cursor,
                "INSERT INTO movie_company (movie_id, company_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
                movie_companies_buf, page_size=500,
            )

        conn.commit()

        for buf in (
            movies_buf, genres_buf, movie_genres_buf,
            countries_buf, movie_countries_buf,
            languages_buf, movie_languages_buf,
            companies_buf, movie_companies_buf,
        ):
            buf.clear()

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                movie_id = row.get("id")
                if not movie_id or not str(movie_id).isdigit():
                    continue

                title = row.get("title") or row.get("original_title") or "Titre inconnu"

                movies_buf.append((
                    row["id"], title,
                    row["release_date"] if row.get("release_date") else None,
                    row.get("poster_path"), row.get("adult", False),
                    row.get("overview"),
                    row["popularity"] if row.get("popularity") else None,
                    row["vote_average"] if row.get("vote_average") else None,
                    row["vote_count"] if row.get("vote_count") else 0,
                ))

                if row.get("genres"):
                    for g in ast.literal_eval(row["genres"]):
                        genres_buf.append((g["id"], g["name"]))
                        movie_genres_buf.append((movie_id, g["id"]))

                if row.get("production_countries"):
                    for c in ast.literal_eval(row["production_countries"]):
                        countries_buf.append((c["iso_3166_1"], c["name"]))
                        movie_countries_buf.append((movie_id, c["iso_3166_1"]))

                if row.get("spoken_languages"):
                    for lang in ast.literal_eval(row["spoken_languages"]):
                        languages_buf.append((lang["iso_639_1"], lang["name"]))
                        movie_languages_buf.append((movie_id, lang["iso_639_1"]))

                if row.get("production_companies"):
                    for c in ast.literal_eval(row["production_companies"]):
                        companies_buf.append((c["id"], c["name"]))
                        movie_companies_buf.append((movie_id, c["id"]))

                if len(movies_buf) >= batch_size:
                    flush()
                    log.info("  ...%d movies processed", inserted)

            except Exception as e:
                errors += 1
                log.debug("Movie row error %s: %s", row.get("id"), e)

    flush()
    log.info("Movies import done: %d inserted, %d errors", inserted, errors)


def import_links_and_tags(
    conn, cursor, links_path: str, tags_path: str, batch_size: int = 1000
) -> None:
    log.info("Building MovieLens -> TMDB ID mapping from %s", links_path)
    ml_to_tmdb: dict[str, str] = {}
    tmdb_updates: list[tuple] = []

    with open(links_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                if row["tmdbId"] and row["movieId"]:
                    ml_to_tmdb[row["movieId"]] = row["tmdbId"]
                    tmdb_updates.append((row["tmdbId"], row["tmdbId"]))
            except Exception as e:
                log.debug("Link error: %s", e)

    if tmdb_updates:
        execute_batch(
            cursor,
            "UPDATE movie SET tmdb_id = %s WHERE id = %s;",
            tmdb_updates, page_size=1000,
        )
        conn.commit()

    # Pré-charger les IDs de films existants pour éviter les violations FK
    log.info("Loading existing movie IDs to filter tags")
    cursor.execute("SELECT id FROM movie;")
    existing_movies = {str(row[0]) for row in cursor.fetchall()}
    log.info("%d movies in DB", len(existing_movies))

    log.info("Importing user tags from %s", tags_path)
    seen_tags: set[str] = set()
    tags_buf: list[tuple] = []
    movie_tags_buf: list[tuple] = []

    inserted = 0
    skipped = 0
    errors = 0

    def flush() -> None:
        nonlocal inserted
        if tags_buf:
            execute_batch(
                cursor,
                "INSERT INTO tag (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;",
                tags_buf, page_size=500,
            )
        if movie_tags_buf:
            execute_batch(
                cursor,
                "INSERT INTO movie_tag (movie_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
                movie_tags_buf, page_size=500,
            )
            inserted += len(movie_tags_buf)
        conn.commit()
        tags_buf.clear()
        movie_tags_buf.clear()

    with open(tags_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                ml_id = row.get("movieId")
                tag_name = row.get("tag")
                if not (tag_name and ml_id in ml_to_tmdb):
                    continue

                tmdb_id = ml_to_tmdb[ml_id]

                # Skip si le film n'est pas dans notre DB (évite les violations FK)
                if tmdb_id not in existing_movies:
                    skipped += 1
                    continue

                tag_clean = tag_name.strip().lower()
                tag_id = abs(hash(tag_clean)) % (10 ** 8)

                if tag_clean not in seen_tags:
                    tags_buf.append((tag_id, tag_clean))
                    seen_tags.add(tag_clean)

                movie_tags_buf.append((tmdb_id, tag_id))

                if len(movie_tags_buf) >= batch_size:
                    flush()

            except Exception as e:
                errors += 1
                log.debug("Tag error: %s", e)

    flush()
    log.info(
        "Tags import done: %d inserted, %d skipped (movie not in DB), %d errors",
        inserted, skipped, errors,
    )


def import_keywords(conn, cursor, csv_path: str, batch_size: int = 1000) -> None:
    log.info("Importing keywords from %s", csv_path)

    keywords_buf: list[tuple] = []
    movie_keywords_buf: list[tuple] = []

    inserted = 0
    errors = 0

    def flush() -> None:
        nonlocal inserted
        if keywords_buf:
            execute_batch(
                cursor,
                "INSERT INTO keyword (id, word) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;",
                keywords_buf, page_size=500,
            )
        if movie_keywords_buf:
            execute_batch(
                cursor,
                "INSERT INTO movie_keyword (movie_id, keyword_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
                movie_keywords_buf, page_size=500,
            )
            inserted += len(movie_keywords_buf)
        conn.commit()
        keywords_buf.clear()
        movie_keywords_buf.clear()

    with open(csv_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                if row["keywords"]:
                    for kw in ast.literal_eval(row["keywords"]):
                        keywords_buf.append((kw["id"], kw["name"]))
                        movie_keywords_buf.append((row["id"], kw["id"]))

                if len(movie_keywords_buf) >= batch_size:
                    flush()

            except Exception as e:
                errors += 1
                log.debug("Keyword error: %s", e)

    flush()
    log.info("Keywords import done: %d inserted, %d errors", inserted, errors)


def import_credits(conn, cursor, csv_path: str, batch_size: int = 1000) -> None:
    log.info("Importing cast and crew from %s", csv_path)

    important_jobs = {
        "Director", "Producer", "Screenplay", "Novel",
        "Original Music Composer", "Director of Photography",
    }

    humans_buf: list[tuple] = []
    movie_humans_buf: list[tuple] = []

    inserted = 0
    errors = 0

    def flush() -> None:
        nonlocal inserted
        if humans_buf:
            execute_batch(
                cursor,
                "INSERT INTO human (id, name_human) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;",
                humans_buf, page_size=500,
            )
        if movie_humans_buf:
            execute_batch(
                cursor,
                "INSERT INTO movie_human (movie_id, human_id, role_human, character_name) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING;",
                movie_humans_buf, page_size=500,
            )
            inserted += len(movie_humans_buf)
        conn.commit()
        humans_buf.clear()
        movie_humans_buf.clear()

    with open(csv_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                movie_id = row.get("id")
                if not movie_id:
                    continue

                if row.get("cast"):
                    for c in ast.literal_eval(row["cast"]):
                        if c["order"] <= 15:
                            humans_buf.append((c["id"], c["name"]))
                            movie_humans_buf.append(
                                (movie_id, c["id"], "Actor", c["character"])
                            )

                if row.get("crew"):
                    for c in ast.literal_eval(row["crew"]):
                        if c["job"] in important_jobs:
                            humans_buf.append((c["id"], c["name"]))
                            movie_humans_buf.append(
                                (movie_id, c["id"], c["job"], None)
                            )

                if len(movie_humans_buf) >= batch_size:
                    flush()
                    log.info("  ...%d cast/crew entries inserted", inserted)

            except Exception as e:
                errors += 1
                log.debug("Credits error: %s", e)

    flush()
    log.info("Credits import done: %d inserted, %d errors", inserted, errors)


def vectorize_movies(conn, cursor, model: SentenceTransformer) -> None:
    log.info("Fetching movies to vectorize")
    cursor.execute("""
        SELECT m.id, m.overview,
            (SELECT STRING_AGG(k.word, ', ')
             FROM movie_keyword mk JOIN keyword k ON mk.keyword_id = k.id
             WHERE mk.movie_id = m.id) AS keywords,
            (SELECT STRING_AGG(g.genre, ', ')
             FROM movie_genre mg JOIN genre g ON mg.genre_id = g.id
             WHERE mg.movie_id = m.id) AS genres,
            (SELECT STRING_AGG(t.name, ', ')
             FROM movie_tag mt JOIN tag t ON mt.tag_id = t.id
             WHERE mt.movie_id = m.id) AS tags
        FROM movie m
        WHERE m.embedding_synopsis IS NULL AND m.overview IS NOT NULL;
    """)
    movies = cursor.fetchall()
    total = len(movies)
    log.info("%d movies to vectorize", total)

    if not movies:
        return

    update_query = (
        "UPDATE movie SET embedding_synopsis = %s, "
        "embedding_keyword = %s, embedding_tag = %s WHERE id = %s"
    )

    for i in range(0, total, BATCH_SIZE):
        batch = movies[i:i + BATCH_SIZE]
        synopses, metadatas, tag_texts, ids = [], [], [], []

        for film_id, overview, keywords, genres, tags in batch:
            synopses.append(overview)
            meta_parts = []
            if genres:
                meta_parts.append(f"Genres : {genres}")
            if keywords:
                meta_parts.append(f"Mots-clés : {keywords}")
            metadatas.append(" | ".join(meta_parts))
            tag_texts.append(f"Tags : {tags}" if tags else "")
            ids.append(film_id)

        log.info(
            "Encoding batch %d-%d / %d",
            i + 1, min(i + BATCH_SIZE, total), total,
        )
        emb_syn = model.encode(synopses)
        emb_meta = model.encode(metadatas)
        emb_tag = model.encode(tag_texts)

        updates = [
            (
                emb_syn[idx].tolist(),
                emb_meta[idx].tolist() if metadatas[idx] else None,
                emb_tag[idx].tolist() if tag_texts[idx] else None,
                ids[idx],
            )
            for idx in range(len(batch))
        ]

        execute_batch(cursor, update_query, updates)
        conn.commit()


def main() -> None:
    try:
        log.info("Connecting to database %s@%s:%s", DB_NAME, DB_HOST, DB_PORT)
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT,
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        )

        # autocommit AVANT register_vector pour éviter ProgrammingError
        conn.autocommit = True
        register_vector(conn)
        cursor = conn.cursor()

        if is_already_initialized(cursor):
            log.info("Database already initialized — exiting (idempotent run)")
            cursor.close()
            conn.close()
            sys.exit(0)

        # Phase 1 : import textuel — autocommit OFF pour les batchs
        conn.autocommit = False

        import_movies(conn, cursor, os.path.join(DATA_DIR, "movies_metadata.csv"))
        import_links_and_tags(
            conn, cursor,
            os.path.join(DATA_DIR, "link.csv"),
            os.path.join(DATA_DIR, "tag.csv"),
        )
        import_keywords(conn, cursor, os.path.join(DATA_DIR, "keywords.csv"))
        import_credits(conn, cursor, os.path.join(DATA_DIR, "credits.csv"))

        # Phase 2 : vectorisation
        if SKIP_VECTORIZATION:
            log.info("Skipping vectorization (SKIP_VECTORIZATION=true)")
        else:
            log.info("Loading SentenceTransformer model from %s", MODEL_PATH)
            model = SentenceTransformer(MODEL_PATH)
            vectorize_movies(conn, cursor, model)

        # Phase 3 : marqueur d'idempotence
        conn.autocommit = True
        mark_completed(cursor, "full_import")
        log.info("Seeding complete!")

        cursor.close()
        conn.close()
    except Exception as e:
        log.error("Seeding failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
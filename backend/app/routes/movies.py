import logging

from fastapi import APIRouter, HTTPException, Query

from ..database import get_connection
from ..ml import get_model
from ..schemas import MovieDetail, MovieSummary, SearchResult, SearchVariants

router = APIRouter(prefix="/movies", tags=["movies"])
log = logging.getLogger(__name__)


def with_poster_url(poster_path: str | None) -> str | None:
    """Préfixe le path TMDB avec l'URL de base pour avoir une URL complète."""
    if not poster_path:
        return None
    if poster_path.startswith("http"):
        return poster_path  # déjà préfixé
    return f"https://image.tmdb.org/t/p/w500{poster_path}"


@router.get("/popular", response_model=list[MovieSummary])
def get_popular_movies(limit: int = 20):
    sql = """
        SELECT id, title, overview, poster, date_publication, vote_average, popularity
        FROM movie
        WHERE popularity IS NOT NULL
          AND adult IS NOT TRUE
        ORDER BY popularity DESC NULLS LAST
        LIMIT %s;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()
    return [
        MovieSummary(
            id=r[0], title=r[1], overview=r[2],
            poster=with_poster_url(r[3]),
            date_publication=r[4], vote_average=r[5], popularity=r[6],
        )
        for r in rows
    ]


@router.get("/search", response_model=list[MovieSummary])
def search_by_title(
    q: str = Query(..., min_length=1, description="Titre à rechercher (typo-tolerant)"),
    limit: int = Query(10, ge=1, le=50),
    threshold: float = Query(0.1, ge=0.0, le=1.0, description="Seuil minimum de similarité"),
) -> list[MovieSummary]:
    """
    Recherche lexicale par titre, tolérante aux fautes de frappe.
    Utilise pg_trgm (trigrammes) pour matcher des titres approchants.
    """
    sql = """
        SELECT id, title, overview, poster, date_publication,
               vote_average, popularity,
               similarity(title, %s) AS score
        FROM movie
        WHERE title %% %s
          AND similarity(title, %s) >= %s
          AND adult IS NOT TRUE
        ORDER BY score DESC, popularity DESC NULLS LAST
        LIMIT %s;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (q, q, q, threshold, limit))
            rows = cur.fetchall()

    return [
        MovieSummary(
            id=r[0], title=r[1], overview=r[2],
            poster=with_poster_url(r[3]),
            date_publication=r[4], vote_average=r[5], popularity=r[6],
        )
        for r in rows
    ]


@router.get("/search/multi", response_model=SearchVariants)
def search_multi(
    q: str = Query(..., min_length=2),
    limit: int = Query(5, ge=1, le=20),
) -> SearchVariants:
    """
    Recherche sémantique avec 3 tris différents :
    - pure : pure similarité (le plus pertinent intellectuellement)
    - by_popularity : favorise les films connus
    - by_rating : favorise les films bien notés
    """
    model = get_model()
    embedding = model.encode(q).tolist()

    sql = """
        WITH calculs AS (
            SELECT id, title, overview, poster, date_publication,
                   vote_average, vote_count, popularity,
                   (1 - (embedding_synopsis <=> %s::vector)) AS s_syn,
                   COALESCE((1 - (embedding_keyword <=> %s::vector)), 0) AS s_key,
                   COALESCE((1 - (embedding_tag <=> %s::vector)), 0) AS s_tag
            FROM movie
            WHERE embedding_synopsis IS NOT NULL
              AND adult IS NOT TRUE
        ),
        maxima AS (
            SELECT GREATEST(MAX(s_syn), 0.001) AS m_syn,
                   GREATEST(MAX(s_key), 0.001) AS m_key,
                   GREATEST(MAX(s_tag), 0.001) AS m_tag
            FROM calculs
        ),
        scored AS (
            SELECT c.id, c.title, c.overview, c.poster, c.date_publication,
                   c.vote_average, c.vote_count, c.popularity,
                   (c.s_syn * (m.m_syn / (m.m_syn + m.m_key + m.m_tag)) +
                    c.s_key * (m.m_key / (m.m_syn + m.m_key + m.m_tag)) +
                    c.s_tag * (m.m_tag / (m.m_syn + m.m_key + m.m_tag))) AS score_pure
            FROM calculs c CROSS JOIN maxima m
        )
        SELECT id, title, overview, poster, date_publication,
               vote_average, vote_count, popularity,
               score_pure,
               -- Bonus popularite (jusqu a 50 pourcent en plus)
               score_pure * (1.0 + 0.5 * LEAST(COALESCE(popularity, 0) / 100.0, 1.0)) AS score_pop,
               -- Bonus note (jusqu a 50 pourcent, pondere par nombre de votes)
               score_pure * (1.0 + 0.5 * (COALESCE(vote_average, 0) / 10.0)
                                       * LEAST(COALESCE(vote_count, 1) / 50.0, 1.0)) AS score_rating
        FROM scored
        WHERE score_pure > 0.25
        ORDER BY score_pure DESC
        LIMIT 100;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (embedding, embedding, embedding))
            rows = cur.fetchall()

    def to_result(row, score_idx: int) -> SearchResult:
        return SearchResult(
            id=row[0], title=row[1], overview=row[2],
            poster=with_poster_url(row[3]),
            date_publication=row[4], vote_average=row[5], popularity=row[7],
            score=float(row[score_idx]),
        )

    pure = sorted(rows, key=lambda r: r[8], reverse=True)[:limit]
    by_pop = sorted(rows, key=lambda r: r[9], reverse=True)[:limit]
    by_rating = sorted(rows, key=lambda r: r[10], reverse=True)[:limit]

    return SearchVariants(
        pure=[to_result(r, 8) for r in pure],
        by_popularity=[to_result(r, 9) for r in by_pop],
        by_rating=[to_result(r, 10) for r in by_rating],
    )


@router.get("/{movie_id}", response_model=MovieDetail)
def get_movie(movie_id: int) -> MovieDetail:
    """Détail complet d'un film avec genres, acteurs, réalisateurs, keywords."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, overview, poster, date_publication,
                       vote_average, popularity
                FROM movie 
                WHERE id = %s
                  AND adult IS NOT TRUE;
                """,
                (movie_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Movie not found")

            cur.execute(
                """
                SELECT g.genre FROM genre g
                JOIN movie_genre mg ON g.id = mg.genre_id
                WHERE mg.movie_id = %s;
                """,
                (movie_id,),
            )
            genres = [r[0] for r in cur.fetchall()]

            cur.execute(
                """
                SELECT k.word FROM keyword k
                JOIN movie_keyword mk ON k.id = mk.keyword_id
                WHERE mk.movie_id = %s LIMIT 20;
                """,
                (movie_id,),
            )
            keywords = [r[0] for r in cur.fetchall()]

            cur.execute(
                """
                SELECT h.name_human FROM human h
                JOIN movie_human mh ON h.id = mh.human_id
                WHERE mh.movie_id = %s AND mh.role_human = 'Director';
                """,
                (movie_id,),
            )
            directors = [r[0] for r in cur.fetchall()]

            cur.execute(
                """
                SELECT h.name_human FROM human h
                JOIN movie_human mh ON h.id = mh.human_id
                WHERE mh.movie_id = %s AND mh.role_human = 'Actor'
                LIMIT 10;
                """,
                (movie_id,),
            )
            actors = [r[0] for r in cur.fetchall()]

    return MovieDetail(
        id=row[0], title=row[1], overview=row[2],
        poster=with_poster_url(row[3]),
        date_publication=row[4], vote_average=row[5], popularity=row[6],
        genres=genres, keywords=keywords, directors=directors, actors=actors,
    )


@router.get("/{movie_id}/similar", response_model=list[SearchResult])
def get_similar_movies(
    movie_id: int,
    limit: int = Query(5, ge=1, le=20),
) -> list[SearchResult]:
    """Films sémantiquement similaires à un film donné."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT embedding_synopsis, embedding_keyword, embedding_tag
                FROM movie 
                WHERE id = %s 
                  AND embedding_synopsis IS NOT NULL
                  AND adult IS NOT TRUE;
                """,
                (movie_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="Movie not found or not vectorized",
                )

            emb_syn, emb_key, emb_tag = row
            empty_vec = [0.0001] * 384
            emb_key = emb_key if emb_key is not None else empty_vec
            emb_tag = emb_tag if emb_tag is not None else empty_vec

            cur.execute(
                """
                WITH calculs AS (
                    SELECT id, title, overview, poster, date_publication,
                           vote_average, popularity,
                           (1 - (embedding_synopsis <=> %s::vector)) AS s_syn,
                           COALESCE((1 - (embedding_keyword <=> %s::vector)), 0) AS s_key,
                           COALESCE((1 - (embedding_tag <=> %s::vector)), 0) AS s_tag
                    FROM movie
                    WHERE embedding_synopsis IS NOT NULL 
                      AND id != %s
                      AND adult IS NOT TRUE
                ),
                maxima AS (
                    SELECT GREATEST(MAX(s_syn), 0.001) AS m_syn,
                           GREATEST(MAX(s_key), 0.001) AS m_key,
                           GREATEST(MAX(s_tag), 0.001) AS m_tag
                    FROM calculs
                )
                SELECT c.id, c.title, c.overview, c.poster, c.date_publication,
                       c.vote_average, c.popularity,
                       (c.s_syn * (m.m_syn / (m.m_syn + m.m_key + m.m_tag)) +
                        c.s_key * (m.m_key / (m.m_syn + m.m_key + m.m_tag)) +
                        c.s_tag * (m.m_tag / (m.m_syn + m.m_key + m.m_tag))) AS score
                FROM calculs c CROSS JOIN maxima m
                ORDER BY score DESC
                LIMIT %s;
                """,
                (emb_syn, emb_key, emb_tag, movie_id, limit),
            )
            rows = cur.fetchall()

    return [
        SearchResult(
            id=r[0], title=r[1], overview=r[2],
            poster=with_poster_url(r[3]),
            date_publication=r[4], vote_average=r[5], popularity=r[6],
            score=float(r[7]),
        )
        for r in rows
    ]   
from fastapi import APIRouter, Depends, HTTPException
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import logging
log = logging.getLogger(__name__)

from .movies import with_poster_url
from .auth import get_current_user_id
from ..database import get_connection
from ..schemas import MovieSummary, SearchResult


router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=list[MovieSummary])
def list_favorites(user_id: int = Depends(get_current_user_id)) -> list[MovieSummary]:
    sql = """
        SELECT m.id, m.title, m.overview, m.poster, m.date_publication,
               m.vote_average, m.popularity
        FROM movie m
        JOIN user_favorite uf ON m.id = uf.movie_id
        WHERE uf.user_id = %s
          AND m.adult IS NOT TRUE
        ORDER BY uf.added_at DESC;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            rows = cur.fetchall()

    return [
        MovieSummary(
            id=r[0], title=r[1], overview=r[2], poster=with_poster_url(r[3]),
            date_publication=r[4], vote_average=r[5], popularity=r[6],
        )
        for r in rows
    ]


@router.post("/{movie_id}", status_code=201)
def add_favorite(
    movie_id: int,
    user_id: int = Depends(get_current_user_id),
) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM movie WHERE id = %s AND adult IS NOT TRUE;",
                (movie_id,),
            )
            if not cur.fetchone():
                raise HTTPException(404, "Movie not found")

            cur.execute(
                """
                INSERT INTO user_favorite (user_id, movie_id)
                VALUES (%s, %s) ON CONFLICT DO NOTHING;
                """,
                (user_id, movie_id),
            )
            conn.commit()
    return {"message": "Favorite added"}


@router.delete("/{movie_id}", status_code=204)
def remove_favorite(
    movie_id: int,
    user_id: int = Depends(get_current_user_id),
) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_favorite WHERE user_id = %s AND movie_id = %s;",
                (user_id, movie_id),
            )
            conn.commit()


def choose_n_clusters(embeddings: np.ndarray) -> int:
    """Choix dynamique du nombre de clusters selon la dispersion des favoris."""
    n = len(embeddings)
    if n < 3:
        return 1
    
    sim_matrix = cosine_similarity(embeddings)
    mask = ~np.eye(n, dtype=bool)
    avg_sim = sim_matrix[mask].mean()
    
    if avg_sim > 0.7:
        return 1
    elif avg_sim > 0.5:
        return 2
    elif avg_sim > 0.35:
        return 3
    else:
        return min(4, n // 3)


@router.get("/recommendations", response_model=list[SearchResult])
def get_recommendations(
    limit: int = 10,
    user_id: int = Depends(get_current_user_id),
) -> list[SearchResult]:
    """
    Recommandations adaptatives :
    - Détermine automatiquement le nombre de clusters selon la cohérence des goûts
    - Retourne des films proches du(des) centroïde(s)
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT m.id, m.embedding_synopsis
                FROM movie m
                JOIN user_favorite uf ON uf.movie_id = m.id
                WHERE uf.user_id = %s 
                  AND m.embedding_synopsis IS NOT NULL;
                """,
                (user_id,),
            )
            rows = cur.fetchall()

            if not rows:
                raise HTTPException(400, "Ajoute au moins un film en favori")

            favorite_ids = [r[0] for r in rows]
            embeddings = np.array([r[1] for r in rows])

            n_clusters = choose_n_clusters(embeddings)
            log.info(
                "User %d : %d favoris, %d cluster(s) choisi(s)",
                user_id, len(rows), n_clusters,
            )

            if n_clusters == 1:
                centroids = [embeddings.mean(axis=0)]
            else:
                kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
                kmeans.fit(embeddings)
                centroids = kmeans.cluster_centers_

            per_cluster = max(limit // n_clusters + 2, 5)
            scores: dict[int, float] = {}

            for centroid in centroids:
                cur.execute(
                    """
                    SELECT id, 1 - (embedding_synopsis <=> %s::vector) AS score
                    FROM movie
                    WHERE embedding_synopsis IS NOT NULL
                      AND id != ALL(%s)
                      AND adult IS NOT TRUE
                    ORDER BY embedding_synopsis <=> %s::vector
                    LIMIT %s;
                    """,
                    (centroid.tolist(), favorite_ids, centroid.tolist(), per_cluster),
                )
                for movie_id, score in cur.fetchall():
                    scores[movie_id] = max(scores.get(movie_id, 0), float(score))

            top_ids = sorted(scores.keys(), key=lambda i: scores[i], reverse=True)[:limit]

            cur.execute(
                """
                SELECT id, title, overview, poster, date_publication,
                       vote_average, popularity
                FROM movie 
                WHERE id = ANY(%s)
                  AND adult IS NOT TRUE;
                """,
                (top_ids,),
            )
            movies_data = {row[0]: row for row in cur.fetchall()}

    return [
        SearchResult(
            id=movies_data[mid][0],
            title=movies_data[mid][1],
            overview=movies_data[mid][2],
            poster=with_poster_url(movies_data[mid][3]),
            date_publication=movies_data[mid][4],
            vote_average=movies_data[mid][5],
            popularity=movies_data[mid][6],
            score=scores[mid],
        )
        for mid in top_ids if mid in movies_data
    ]
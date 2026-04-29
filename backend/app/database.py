import logging
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool
from pgvector.psycopg2 import register_vector

from .config import settings

log = logging.getLogger(__name__)

# Pool de 2 à 10 connexions, réutilisées entre les requêtes
_pool: pool.SimpleConnectionPool | None = None


def init_pool() -> None:
    """Initialise le pool de connexions au démarrage de l'app."""
    global _pool
    log.info(
        "Initializing DB pool to %s@%s:%s",
        settings.db_name, settings.db_host, settings.db_port,
    )
    _pool = pool.SimpleConnectionPool(
        minconn=2,
        maxconn=10,
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
    )
    # On enregistre vector sur une connexion test (pour valider que ça marche)
    conn = _pool.getconn()
    register_vector(conn)
    _pool.putconn(conn)
    log.info("DB pool initialized")


def close_pool() -> None:
    """Ferme toutes les connexions à l'arrêt de l'app."""
    if _pool:
        _pool.closeall()


@contextmanager
def get_connection():
    """
    Context manager pour obtenir une connexion du pool.

    Usage :
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(...)
    """
    if _pool is None:
        raise RuntimeError("DB pool not initialized")

    conn = _pool.getconn()
    try:
        register_vector(conn)
        yield conn
    finally:
        _pool.putconn(conn)
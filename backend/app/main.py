import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_pool, close_pool
from .ml import load_model
from .routes import health, movies, auth, favorites

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Setup et teardown de l'application."""
    log.info("Starting up...")
    init_pool()
    load_model()
    log.info("Startup complete")
    yield
    log.info("Shutting down...")
    close_pool()


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    lifespan=lifespan,
)

# CORS pour le frontend (à restreindre plus tard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(movies.router)
app.include_router(auth.router)
app.include_router(favorites.router)

@app.get("/")
def root() -> dict:
    return {"message": "Movie API", "docs": "/docs"}
from datetime import date

from pydantic import BaseModel, Field


class MovieSummary(BaseModel):
    """Résumé d'un film (pour les listes de résultats)."""
    id: int
    title: str
    overview: str | None = None
    poster: str | None = None
    date_publication: date | None = None
    vote_average: float | None = None
    popularity: float | None = None


class MovieDetail(MovieSummary):
    """Détail complet d'un film avec ses relations."""
    genres: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    directors: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)


class SearchResult(MovieSummary):
    """Film résultat de recherche, avec score de similarité."""
    score: float

class SearchVariants(BaseModel):
    """Trois listes de résultats avec des tris différents."""
    pure: list[SearchResult]           # Sans biais : pure similarité sémantique
    by_popularity: list[SearchResult]  # Biaisé par popularité (+50% max)
    by_rating: list[SearchResult]      # Biaisé par note (+50% max)


class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    model_loaded: bool






class UserRegister(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    id: int
    username: str


class TokenResponse(BaseModel):
    token: str
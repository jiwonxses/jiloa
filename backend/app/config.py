from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration de l'application, chargée depuis les variables d'env."""

    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str

    model_path: str = "/app/models/minilm-multilingual"

    api_title: str = "Movie API"
    api_version: str = "0.1.0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Singleton global
settings = Settings()
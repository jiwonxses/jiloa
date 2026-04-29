import logging

from sentence_transformers import SentenceTransformer

from .config import settings

log = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


def load_model() -> SentenceTransformer:
    """Charge le modèle depuis le disque local. Pas de réseau."""
    global _model
    log.info("Loading SentenceTransformer from %s", settings.model_path)
    _model = SentenceTransformer(settings.model_path)
    log.info("Model loaded, dim=%d", _model.get_sentence_embedding_dimension())
    return _model


def get_model() -> SentenceTransformer:
    """Retourne le modèle déjà chargé."""
    if _model is None:
        raise RuntimeError("Model not loaded — appeler load_model() d'abord")
    return _model
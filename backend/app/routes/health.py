from fastapi import APIRouter

from ..database import get_connection
from ..ml import get_model
from ..schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """
    Endpoint de santé. Vérifie que la DB est accessible et que le modèle est chargé.
    Utilisé par Docker/Kubernetes pour les healthchecks.
    """
    db_connected = False
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
                db_connected = True
    except Exception:
        pass

    model_loaded = False
    try:
        get_model()
        model_loaded = True
    except RuntimeError:
        pass

    status = "ok" if (db_connected and model_loaded) else "degraded"
    return HealthResponse(
        status=status,
        db_connected=db_connected,
        model_loaded=model_loaded,
    )
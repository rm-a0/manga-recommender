"""Liveness and readiness probe endpoints."""

import structlog
from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from manga_recommender.api.dependencies import DbSession
from manga_recommender.schemas.probes import Health, Readiness

logger = structlog.get_logger(__name__)

router: APIRouter = APIRouter(tags=["probes"])


def _database_reachable(db: Session) -> bool:
    """Return True when the database answers a trivial query."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("readiness_check_failed", dependency="database", exc_info=True)
        return False
    return True


@router.get("/health", response_model=Health)
def health_check() -> Health:
    """Report that the process is running.

    Touches no dependency. A failure here means the process itself is gone.
    """
    return Health(status="ok")


@router.get("/ready", response_model=Readiness)
def readiness_check(db: DbSession, response: Response) -> Readiness:
    """Report whether every dependency the API needs is reachable.

    Answers 503 when any check fails, so a caller can tell a degraded API
    from a healthy one without parsing the body.
    """
    checks = {"database": _database_reachable(db)}
    if not all(checks.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return Readiness(status="degraded", checks=checks)
    return Readiness(status="ready", checks=checks)

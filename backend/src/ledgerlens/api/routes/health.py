import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy import text

from ledgerlens.db.engine import get_engine
from ledgerlens.search.client import get_search_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


def check_postgresql(request: Request) -> bool:
    try:
        with get_engine(request).connect() as connection:
            return bool(connection.execute(text("SELECT 1")).scalar_one() == 1)
    except Exception:
        # Readiness converts dependency failures into a non-sensitive component state.
        logger.warning("PostgreSQL readiness check failed")
        return False


def check_typesense(request: Request) -> bool:
    try:
        return get_search_client(request).operations.is_healthy()
    except Exception:
        # Never return upstream exceptions, which may contain URLs or API keys.
        logger.warning("Typesense readiness check failed")
        return False


class ComponentState(BaseModel):
    postgresql: Literal["ok", "unavailable"]
    typesense: Literal["ok", "unavailable"]


class Readiness(BaseModel):
    status: Literal["ready", "not_ready"]
    components: ComponentState


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", response_model=Readiness, responses={503: {"model": Readiness}})
def ready(
    response: Response,
    postgresql: Annotated[bool, Depends(check_postgresql)],
    typesense_ok: Annotated[bool, Depends(check_typesense)],
) -> Readiness:
    available = postgresql and typesense_ok
    response.status_code = 200 if available else 503
    return Readiness(
        status="ready" if available else "not_ready",
        components=ComponentState(
            postgresql="ok" if postgresql else "unavailable",
            typesense="ok" if typesense_ok else "unavailable",
        ),
    )

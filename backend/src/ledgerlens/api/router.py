from fastapi import APIRouter

from ledgerlens.api.routes import demo, health

router = APIRouter(prefix="/api")
router.include_router(health.router)
router.include_router(demo.router)

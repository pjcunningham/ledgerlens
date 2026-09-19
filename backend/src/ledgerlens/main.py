from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ledgerlens.api.router import router
from ledgerlens.config import Settings, get_settings
from ledgerlens.db.engine import create_db_engine
from ledgerlens.search.client import create_search_client


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = create_db_engine(configuration)
        app.state.search_client = create_search_client(configuration)
        try:
            yield
        finally:
            app.state.engine.dispose()

    app = FastAPI(title="LedgerLens", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=configuration.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(router)
    return app


app = create_app()

from typing import cast

from fastapi import Request
from sqlalchemy import Engine
from sqlmodel import create_engine

from ledgerlens.config import Settings


def get_engine(request: Request) -> Engine:
    return cast(Engine, request.app.state.engine)


def create_db_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )

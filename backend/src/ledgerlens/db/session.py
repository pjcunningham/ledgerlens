from collections.abc import Iterator

from fastapi import Request
from sqlmodel import Session

from ledgerlens.db.engine import get_engine


def get_session(request: Request) -> Iterator[Session]:
    with Session(get_engine(request)) as session:
        yield session

from typing import cast

from fastapi import Request
from typesense.client import Client

from ledgerlens.config import Settings


def get_search_client(request: Request) -> Client:
    return cast(Client, request.app.state.search_client)


def create_search_client(settings: Settings) -> Client:
    return Client(
        {
            "nodes": [
                {
                    "host": settings.typesense_host,
                    "port": settings.typesense_port,
                    "protocol": settings.typesense_protocol,
                }
            ],
            "api_key": settings.typesense_api_key.get_secret_value(),
            "connection_timeout_seconds": 3,
            "num_retries": 0,
        }
    )

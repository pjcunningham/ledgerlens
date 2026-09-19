from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ledgerlens.config import Settings
from ledgerlens.main import create_app


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--run-integration", action="store_true", default=False)
    parser.addoption("--run-sage-integration", action="store_true", default=False)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not config.getoption("--run-sage-integration"):
        for item in items:
            if "sage_integration" in item.keywords:
                item.add_marker(
                    pytest.mark.skip(reason="Use --run-sage-integration with a real Sage DSN")
                )
    if not config.getoption("--run-integration"):
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(
                    pytest.mark.skip(reason="Use --run-integration with Docker running")
                )


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app(Settings(_env_file=None, env="test"))) as test_client:
        yield test_client

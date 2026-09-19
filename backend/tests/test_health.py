from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from ledgerlens.api.routes.health import check_postgresql, check_typesense


def test_liveness_does_not_probe_infrastructure(client: TestClient) -> None:
    engine = MagicMock()
    engine.connect.side_effect = AssertionError("Liveness must not connect")
    search = MagicMock()
    search.operations.is_healthy.side_effect = AssertionError("Liveness must not connect")
    client.app.state.engine = engine
    client.app.state.search_client = search
    assert client.get("/api/health/live").json() == {"status": "ok"}
    engine.connect.assert_not_called()
    search.operations.is_healthy.assert_not_called()


@pytest.mark.parametrize(
    "postgresql,typesense_ok", [(True, True), (False, True), (True, False), (False, False)]
)
def test_readiness_states(client: TestClient, postgresql: bool, typesense_ok: bool) -> None:
    client.app.dependency_overrides[check_postgresql] = lambda: postgresql
    client.app.dependency_overrides[check_typesense] = lambda: typesense_ok
    response = client.get("/api/health/ready")
    assert response.status_code == (200 if postgresql and typesense_ok else 503)
    assert response.json() == {
        "status": "ready" if postgresql and typesense_ok else "not_ready",
        "components": {
            "postgresql": "ok" if postgresql else "unavailable",
            "typesense": "ok" if typesense_ok else "unavailable",
        },
    }


@pytest.mark.parametrize("failed_component", ["postgresql", "typesense"])
def test_dependency_exceptions_never_leak_secrets(
    client: TestClient, failed_component: str
) -> None:
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.scalar_one.return_value = 1
    search = MagicMock()
    search.operations.is_healthy.return_value = True
    secret = "postgresql://user:secret-password@host/db?api_key=private-key"
    if failed_component == "postgresql":
        engine.connect.side_effect = RuntimeError(secret)
    else:
        search.operations.is_healthy.side_effect = RuntimeError(secret)
    client.app.state.engine = engine
    client.app.state.search_client = search
    response = client.get("/api/health/ready")
    assert response.status_code == 503
    assert response.json()["components"][failed_component] == "unavailable"
    for sensitive in ["secret-password", "private-key", "Traceback", "postgresql://"]:
        assert sensitive not in response.text


def test_real_probe_functions_with_successful_clients(client: TestClient) -> None:
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.scalar_one.return_value = 1
    search = MagicMock()
    search.operations.is_healthy.return_value = True
    client.app.state.engine = engine
    client.app.state.search_client = search
    assert client.get("/api/health/ready").status_code == 200


def test_typesense_unhealthy_response(client: TestClient) -> None:
    client.app.dependency_overrides[check_postgresql] = lambda: True
    search = MagicMock()
    search.operations.is_healthy.return_value = False
    client.app.state.search_client = search
    assert client.get("/api/health/ready").status_code == 503


def test_docs_and_cors(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    allowed = client.options(
        "/api/demo/customers/grid",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    forbidden = client.options(
        "/api/demo/customers/grid",
        headers={"Origin": "http://untrusted.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in forbidden.headers

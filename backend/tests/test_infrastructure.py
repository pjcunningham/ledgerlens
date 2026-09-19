import pytest
from fastapi.testclient import TestClient

from ledgerlens.main import create_app


@pytest.mark.integration
def test_real_infrastructure_readiness() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/health/ready")
        assert response.status_code == 200, response.text
        assert response.json() == {
            "status": "ready",
            "components": {"postgresql": "ok", "typesense": "ok"},
        }

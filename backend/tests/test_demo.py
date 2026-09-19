import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "skip,take,expected_ids",
    [
        (0, 25, list(range(1, 26))),
        (25, 25, list(range(26, 51))),
        (0, 10, list(range(1, 11))),
        (95, 25, list(range(96, 101))),
        (100, 10, []),
        (1000, 10, []),
    ],
)
def test_pages(client: TestClient, skip: int, take: int, expected_ids: list[int]) -> None:
    response = client.post(
        "/api/demo/customers/grid",
        json={"loadOptions": {"skip": skip, "take": take, "requireTotalCount": True}},
    )
    assert response.status_code == 200
    result = response.json()
    assert [row["id"] for row in result["data"]] == expected_ids
    assert result["totalCount"] == 100


def test_defaults_and_optional_count(client: TestClient) -> None:
    response = client.post("/api/demo/customers/grid", json={"loadOptions": {}})
    assert response.status_code == 200
    assert len(response.json()["data"]) == 25
    assert "totalCount" not in response.json()


def test_inactive_native_filter(client: TestClient) -> None:
    response = client.post("/api/demo/customers/grid", json={"loadOptions": {"filter": None}})
    assert response.status_code == 200
    assert len(response.json()["data"]) == 25


@pytest.mark.parametrize(
    "options",
    [
        {"skip": -1},
        {"take": -1},
        {"take": 0},
        {"take": 101},
        {"skip": 1_000_001},
        {"skip": 1.5},
        {"take": "10"},
        {"skip": True},
        {"take": None},
        {"requireTotalCount": "true"},
        {"sort": [{"selector": "__class__"}]},
        {"sort": [{"selector": "name; DROP TABLE customers"}]},
        {"sort": [{"selector": "name", "desc": "true"}]},
        {"sort": [{"selector": "name"}] * 6},
        {"filter": ["active", "=", True]},
        {"group": [{"selector": "active"}]},
        {"totalSummary": [{"summaryType": "count"}]},
    ],
)
def test_invalid_load_options(client: TestClient, options: dict[str, object]) -> None:
    assert client.post("/api/demo/customers/grid", json={"loadOptions": options}).status_code == 422


@pytest.mark.parametrize("selector", ["id", "account_ref", "name", "balance", "active"])
@pytest.mark.parametrize("descending", [False, True])
def test_whitelisted_sorts(client: TestClient, selector: str, descending: bool) -> None:
    result = client.post(
        "/api/demo/customers/grid",
        json={"loadOptions": {"take": 100, "sort": [{"selector": selector, "desc": descending}]}},
    ).json()
    values = [row[selector] for row in result["data"]]
    assert values == sorted(values, reverse=descending)


def test_multisort_and_stable_tiebreak(client: TestClient) -> None:
    result = client.post(
        "/api/demo/customers/grid",
        json={"loadOptions": {"take": 100, "sort": [{"selector": "active", "desc": False}]}},
    ).json()
    inactive = [row["id"] for row in result["data"] if not row["active"]]
    assert inactive == list(range(4, 101, 4))
    result = client.post(
        "/api/demo/customers/grid",
        json={
            "loadOptions": {
                "take": 5,
                "sort": [{"selector": "active", "desc": False}, {"selector": "id", "desc": True}],
            }
        },
    ).json()
    assert [row["id"] for row in result["data"]] == [100, 96, 92, 88, 84]


def test_request_envelope_is_required(client: TestClient) -> None:
    assert client.post("/api/demo/customers/grid", json={"take": 10}).status_code == 422

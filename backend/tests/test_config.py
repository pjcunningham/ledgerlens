import pytest
from pydantic import ValidationError

from ledgerlens.config import Settings


def test_environment_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "ENV": "test",
        "DATABASE_URL": "postgresql+psycopg://demo:password@db:5433/demo",
        "TYPESENSE_HOST": "search",
        "TYPESENSE_PORT": "8109",
        "TYPESENSE_PROTOCOL": "https",
        "TYPESENSE_API_KEY": "private-key",
        "CORS_ORIGINS": "http://localhost:5173, http://127.0.0.1:5173",
    }
    for key, value in values.items():
        monkeypatch.setenv(f"LEDGERLENS_{key}", value)
    settings = Settings(_env_file=None)
    assert settings.env == "test"
    assert settings.database_url.get_secret_value() == values["DATABASE_URL"]
    assert settings.typesense_host == "search"
    assert settings.typesense_port == 8109
    assert settings.typesense_protocol == "https"
    assert settings.typesense_api_key.get_secret_value() == "private-key"
    assert settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]
    assert "private-key" not in repr(settings)
    assert "password" not in repr(settings)


@pytest.mark.parametrize(
    "key,value",
    [
        ("ENV", "typo"),
        ("DATABASE_URL", "sqlite:///demo.db"),
        ("DATABASE_URL", "not-a-url-with-secret"),
        ("TYPESENSE_PORT", "0"),
        ("TYPESENSE_PORT", "65536"),
        ("TYPESENSE_PROTOCOL", "ftp"),
        ("TYPESENSE_HOST", ""),
        ("TYPESENSE_API_KEY", ""),
        ("CORS_ORIGINS", "*"),
        ("CORS_ORIGINS", "https://example.com/path"),
        ("CORS_ORIGINS", "https://user:password@example.com"),
    ],
)
def test_invalid_settings(monkeypatch: pytest.MonkeyPatch, key: str, value: str) -> None:
    monkeypatch.setenv(f"LEDGERLENS_{key}", value)
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)
    assert key.lower() in str(error.value)
    assert "input_value" not in str(error.value)

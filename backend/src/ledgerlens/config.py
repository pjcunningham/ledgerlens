from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

# The documented backend/ working directory also loads root .env.
ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LEDGERLENS_", env_file=ROOT_ENV, extra="ignore", hide_input_in_errors=True
    )

    env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://ledgerlens:ledgerlens_dev@localhost:5432/ledgerlens"
    )
    typesense_host: str = Field(default="localhost", min_length=1, pattern=r"^[\w.-]+$")
    typesense_port: int = Field(default=8108, ge=1, le=65535)
    typesense_protocol: Literal["http", "https"] = "http"
    typesense_api_key: SecretStr = SecretStr("ledgerlens-development-key")
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
        except ArgumentError as exc:
            raise ValueError("database_url must be a PostgreSQL Psycopg 3 URL") from exc
        if url.drivername != "postgresql+psycopg" or not url.host or not url.database:
            raise ValueError("database_url must be a PostgreSQL Psycopg 3 URL")
        return value

    @field_validator("typesense_api_key")
    @classmethod
    def validate_api_key(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("typesense_api_key must not be empty")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or "*" in origin
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    "cors_origins must contain HTTP(S) origins without paths or wildcards"
                )
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()

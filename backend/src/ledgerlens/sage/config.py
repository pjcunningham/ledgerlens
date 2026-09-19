from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from ledgerlens.config import ROOT_ENV


class SageError(Exception):
    """Safe, user-facing diagnostic; never contains driver exception text."""


class SageSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LEDGERLENS_SAGE_",
        env_file=ROOT_ENV,
        extra="ignore",
        hide_input_in_errors=True,
    )
    dsn: SecretStr = SecretStr("")
    username: SecretStr = SecretStr("")
    password: SecretStr = SecretStr("")
    query_timeout_seconds: int = Field(default=30, ge=1, le=300)

    def require_connection(self) -> None:
        if not self.dsn.get_secret_value().strip() or not self.username.get_secret_value().strip():
            raise SageError("Configure LEDGERLENS_SAGE_DSN and LEDGERLENS_SAGE_USERNAME locally.")
        if any(
            "\x00" in value.get_secret_value() for value in (self.dsn, self.username, self.password)
        ):
            raise SageError("Sage connection settings contain an invalid character.")

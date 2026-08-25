"""Application configuration loaded and validated from the environment."""

from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    AnyHttpUrl,
    Field,
    PostgresDsn,
    SecretStr,
    computed_field,
    field_validator,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_LOCAL_FRONTEND_ORIGIN = "http://localhost:5173"


class Settings(BaseSettings):
    """Required configuration for the backend service."""

    model_config = SettingsConfigDict(
        env_file=_BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    supabase_url: AnyHttpUrl
    supabase_anon_key: SecretStr = Field(min_length=1)
    supabase_service_role_key: SecretStr = Field(min_length=1)
    database_url: PostgresDsn

    openai_api_key: SecretStr = Field(min_length=1)
    openai_chat_model: str = Field(min_length=1)
    openai_embedding_model: str = Field(min_length=1)
    openai_embedding_dimensions: int = Field(gt=0)

    allowed_origins: Annotated[list[AnyHttpUrl], NoDecode]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    backend_log_path: Path = _BACKEND_DIR / "logs" / "backend.log"

    @computed_field
    @property
    def sqlalchemy_database_url(self) -> str:
        """Use psycopg 3 when SQLAlchemy opens the direct database connection."""
        url = str(self.database_url)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        return url

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @field_validator("openai_embedding_dimensions")
    @classmethod
    def match_embedding_schema(cls, dimensions: int) -> int:
        if dimensions != 1536:
            raise ValueError("must match the database vector dimension of 1536")
        return dimensions

    @field_validator("allowed_origins")
    @classmethod
    def restrict_allowed_origins(cls, origins: list[AnyHttpUrl]) -> list[AnyHttpUrl]:
        configured_origins = [str(origin).rstrip("/") for origin in origins]
        if configured_origins != [_LOCAL_FRONTEND_ORIGIN]:
            raise ValueError(f"must be exactly {_LOCAL_FRONTEND_ORIGIN}")
        return origins


# Importing application code validates configuration immediately so startup fails
# before the service accepts traffic.
settings = Settings()

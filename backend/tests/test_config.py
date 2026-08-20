import pytest
from pydantic import ValidationError

from app.config import Settings

REQUIRED_ENV = {
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_ANON_KEY": "test-anon-key",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
    "DATABASE_URL": "postgresql://postgres:password@db.example.supabase.co:5432/postgres",
    "OPENAI_API_KEY": "test-openai-key",
    "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",
    "OPENAI_EMBEDDING_DIMENSIONS": "1536",
    "ALLOWED_ORIGINS": "http://localhost:5173",
}


def test_settings_load_required_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in REQUIRED_ENV.items():
        monkeypatch.setenv(name, value)

    loaded = Settings(_env_file=None)

    assert loaded.openai_embedding_dimensions == 1536
    assert [str(origin) for origin in loaded.allowed_origins] == [
        "http://localhost:5173/",
    ]


def test_settings_reject_missing_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in REQUIRED_ENV:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    missing_fields = {
        item["loc"][0] for item in error.value.errors() if item["type"] == "missing"
    }
    assert missing_fields == {
        "supabase_url",
        "supabase_anon_key",
        "supabase_service_role_key",
        "database_url",
        "openai_api_key",
        "openai_embedding_model",
        "openai_embedding_dimensions",
        "allowed_origins",
    }


@pytest.mark.parametrize(
    "origins",
    ["", "http://localhost:3000", "https://localhost:5173", "http://example.com"],
)
def test_settings_reject_disallowed_origins(
    monkeypatch: pytest.MonkeyPatch,
    origins: str,
) -> None:
    for name, value in REQUIRED_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("ALLOWED_ORIGINS", origins)

    with pytest.raises(ValidationError, match="must be exactly http://localhost:5173"):
        Settings(_env_file=None)

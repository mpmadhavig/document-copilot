import os

_TEST_ENV = {
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_ANON_KEY": "test-anon-key",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
    "DATABASE_URL": "postgresql://postgres:password@db.example.supabase.co:5432/postgres",
    "OPENAI_API_KEY": "test-openai-key",
    "OPENAI_CHAT_MODEL": "test-chat-model",
    "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",
    "OPENAI_EMBEDDING_DIMENSIONS": "1536",
    "ALLOWED_ORIGINS": "http://localhost:5173",
}

for name, value in _TEST_ENV.items():
    os.environ.setdefault(name, value)

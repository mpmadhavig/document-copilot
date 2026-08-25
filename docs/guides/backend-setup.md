# Backend setup guide

The FastAPI backend owns authorization, chat orchestration, retrieval,
grounding, persistence, and corpus ingestion.

## First setup

```bash
cd backend
cp .env.example .env
# Replace every placeholder in .env.
uv sync --locked
uv run alembic upgrade head
```

Use the direct/session Supabase Postgres connection in `DATABASE_URL`; migrations
must not use the transaction pooler. `app/config.py` validates every required
setting when application code is imported.

## Run and check

```bash
uv run uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
curl http://127.0.0.1:8000/health
uv run pytest -m "not integration"
uv run ruff check app ingest tests scripts
```

## Change the schema

SQLAlchemy models describe tables and columns. Alembic owns every schema change:

```bash
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
```

Review generated migrations. Add `pgvector`, generated `tsvector`, HNSW/GIN
indexes, RLS, policies, grants, triggers, and RPC functions explicitly because
autogenerate cannot fully represent them.

## Next steps

- [Root setup and corpus loading](../../README.md)
- [Backend command reference](../../backend/README.md)
- [Technical guide](../technical-guide.md)
- [Contribution and migration policy](../../CONTRIBUTING.md)

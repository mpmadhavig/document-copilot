# Document Copilot backend

The backend is a FastAPI service that verifies Supabase users, runs hybrid
filing retrieval and the grounded PydanticAI agent, persists chats, and emits
AI SDK-compatible server-sent events.

Read the [root README](../README.md) for complete setup and corpus-loading
instructions, and [the technical guide](../docs/technical-guide.md) for the
algorithms and request lifecycle.

## Configure and run

```bash
cp .env.example .env
# Replace every placeholder in .env.
uv sync --locked
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

- Health: <http://127.0.0.1:8000/health>
- OpenAPI UI: <http://127.0.0.1:8000/docs>

The database URL must be the Supabase direct/session Postgres connection.
Configuration is validated in `app/config.py` before the service starts.

## Module map

```text
app/api/          HTTP routes and SSE boundary
app/auth/         Supabase bearer-token dependencies
app/assistant/    PydanticAI agent, evidence tools, typed output
app/chat/         stored-history conversion, orchestration, stream encoding
app/database/     Supabase clients, persistence helpers, SQLAlchemy models
app/grounding/    citation validation and deterministic rendering
app/retrieval/    vector/text queries, RRF, neighbor expansion
ingest/           offline corpus conversion and import commands
scripts/          opt-in live evaluation commands
tests/            fast tests plus marked integration tests
```

## Checks

```bash
uv run pytest -m "not integration"
uv run ruff check app ingest tests scripts
uv run alembic heads
```

Live checks require the configured Supabase/OpenAI services. The grounding
evaluation makes paid model calls and requires its confirmation flag:

```bash
uv run python -m scripts.evaluate_retrieval
uv run python -m scripts.evaluate_grounding --confirm-live-calls
```

## Migrations

After changing a SQLAlchemy model:

```bash
uv run alembic revision --autogenerate -m "describe the change"
```

Review every generated migration. Add RLS, policies, grants, triggers, Postgres
functions, generated search columns, and vector/index operations explicitly.
Apply schema changes only through Alembic.

## Logs

Backend errors go to stderr and rotating JSON lines in `logs/backend.log` by
default. Find a user-visible reference with:

```bash
rg 'be-reference-from-the-ui' logs/backend.log*
```

`BACKEND_LOG_PATH` changes the file location and `LOG_LEVEL` controls verbosity.

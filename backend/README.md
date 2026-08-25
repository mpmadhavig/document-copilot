# Document Copilot API

```bash
cd backend
cp .env.example .env  # Add your Supabase and OpenAI credentials.
uv sync
uv run uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/docs> to try the API, or check it with:

```bash
curl http://127.0.0.1:8000/health
```

Run the fast backend checks with:

```bash
uv run pytest -m "not integration"
uv run ruff check app ingest tests scripts
```

Backend failures are written as rotating JSON lines to `logs/backend.log` by
default. Override the path with `BACKEND_LOG_PATH`. A user-visible `be-...`
reference can be located with:

```bash
rg 'be-reference-from-the-ui' logs/backend.log*
```

After applying the migrations and ingesting the corpus, run the live retrieval
evaluation with:

```bash
uv run python -m scripts.evaluate_retrieval
```

The grounded-agent evaluation makes paid OpenAI calls and requires an explicit
confirmation flag:

```bash
uv run python -m scripts.evaluate_grounding --confirm-live-calls
```

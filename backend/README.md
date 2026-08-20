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

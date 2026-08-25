# Document Copilot

Document Copilot is an authenticated research assistant for querying a curated
corpus of SEC filings. It combines semantic and full-text retrieval, generates a
structured answer, and only displays factual answers whose citations pass a
server-side grounding check.

The repository contains a complete local vertical slice: email authentication,
chat history, corpus ingestion, hybrid retrieval, grounded answer generation,
citations, source inspection, and structured error logging. Before a production
release, complete the items in the [project review](docs/project-review.md).

## What the application does

- Signs analysts in with Supabase email authentication.
- Stores private chat threads and messages behind Postgres row-level security.
- Searches normalized filings with OpenAI embeddings, `pgvector`, and Postgres
  full-text search.
- Fuses semantic and lexical rankings with Reciprocal Rank Fusion (RRF).
- Gives the model bounded tools for searching and reading filing passages.
- Rejects unsupported citations and persists a completed turn atomically.
- Streams AI SDK-compatible answer and citation events to the React client.

The fictional product brief is in [docs/client-brief.md](docs/client-brief.md).
The implementation is explained in
[docs/technical-guide.md](docs/technical-guide.md).

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | Vite, React, TypeScript, Tailwind CSS, AI SDK UI |
| Backend | Python 3.12+, FastAPI, PydanticAI |
| Data and auth | Supabase Auth and Postgres |
| Retrieval | `pgvector`, Postgres full-text search, Python RRF |
| Schema | SQLAlchemy models and Alembic migrations |
| Models | OpenAI chat and embedding models |
| Intended hosting | Railway frontend and backend services |

## Repository map

```text
document-copilot/
├── AGENTS.md                 # repository-wide engineering rules
├── CONTRIBUTING.md           # development and repository-content policy
├── backend/
│   ├── app/                  # FastAPI, auth, chat, retrieval, and grounding
│   ├── alembic/versions/     # ordered database migrations
│   ├── ingest/               # conversion, chunking, embedding, and import CLIs
│   ├── scripts/              # opt-in live retrieval/grounding evaluations
│   └── tests/                # fast unit/contract tests and marked integration tests
├── data/
│   ├── download.py           # SEC EDGAR sample downloader
│   ├── downloads/            # raw files and manifest; generated and ignored
│   └── markdown/             # reviewed normalized sample corpus
├── docs/                     # product, setup, technical, and readiness docs
└── frontend/
    ├── server/               # Vite middleware for browser error collection
    └── src/                  # React routes, components, and typed clients
```

## Prerequisites

- Python 3.12 or newer
- [`uv`](https://docs.astral.sh/uv/)
- Node.js 20 or newer
- `pnpm` (the only supported frontend package manager)
- A Supabase project
- An OpenAI API key

Use [docs/guides/supabase-setup.md](docs/guides/supabase-setup.md) to create the
Supabase project and collect the required values.

## Run locally

### 1. Configure both services

From the repository root:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Replace every placeholder. Keep the Supabase service-role key, database URL,
and OpenAI key in `backend/.env` only. The frontend file may contain only the
public Supabase URL, anon key, and backend URL.

For local development, keep:

```dotenv
# backend/.env
ALLOWED_ORIGINS=http://localhost:5173

# frontend/.env
VITE_API_BASE_URL=http://localhost:8000
```

### 2. Install the backend and apply the schema

```bash
cd backend
uv sync --locked
uv run alembic upgrade head
```

Alembic must use the direct/session Supabase Postgres URL, not the transaction
pooler. Apply migrations before creating application users so the auth-user sync
trigger and public user table are available.

### 3. Load a corpus when the database is empty

The checked-in `data/markdown/` directory is a reviewed normalized sample. The
generated manifest still comes from the downloader.

First edit `USER_AGENT` in `data/download.py`, then run:

```bash
# From the repository root:
uv run data/download.py

cd backend
uv run python -m ingest.convert_filings ../data/downloads ../data/markdown
uv run python -m ingest.import_documents \
  ../data/downloads/manifest.json ../data/markdown
uv run python -m ingest.import_chunks \
  ../data/downloads/manifest.json ../data/markdown --estimate
```

Review the estimate before making paid embedding calls. Then use the printed
token count as the spending guard and your account's token-per-minute limit:

```bash
uv run python -m ingest.import_chunks \
  ../data/downloads/manifest.json ../data/markdown \
  --all --max-total-tokens ESTIMATED_TOKENS \
  --tokens-per-minute ACCOUNT_TPM_LIMIT
```

The import is idempotent at the document/chunk-version level. See
[data/README.md](data/README.md) for previews and one-call embedding checks.

### 4. Start the API

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

Check <http://127.0.0.1:8000/health> and the OpenAPI UI at
<http://127.0.0.1:8000/docs>.

### 5. Start the frontend

In another terminal:

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Open <http://localhost:5173>, create an email account, and sign in. Supabase
email confirmation may be disabled for local development; re-enable it before
production use.

## Use the product

1. Create a research thread from the left sidebar.
2. Ask a focused question that names the company, fiscal year, filing type, or
   disclosure where possible.
3. Open inline citation markers or source chips beside the answer.
4. Compare the exact quote, filing metadata, and original SEC source before
   using an answer downstream.
5. Treat `insufficient_evidence` as a deliberate result: the available corpus
   did not support a grounded answer.

The assistant summarizes filing evidence; it does not provide stock picks,
price targets, or personalized investment advice.

## Verify a change

Backend fast checks:

```bash
cd backend
uv run pytest -m "not integration"
uv run ruff check app ingest tests scripts
uv run alembic heads
```

Frontend checks:

```bash
cd frontend
pnpm lint
pnpm build
```

Live retrieval and grounding evaluations use Supabase/OpenAI and may incur cost:

```bash
cd backend
uv run python -m scripts.evaluate_retrieval
uv run python -m scripts.evaluate_grounding --confirm-live-calls
```

## Troubleshooting

User-visible failures contain a `be-...` or `fe-...` reference. Local logs are
rotating newline-delimited JSON:

```bash
rg 'be-reference' backend/logs/backend.log*
rg 'fe-reference' frontend/logs/frontend.log*
```

Chat text, credentials, tokens, and API response bodies are intentionally not
included in browser error reports. Railway filesystems are ephemeral, so use a
persistent volume or a production log sink before relying on file retention.

## Contributing and repository contents

Read [CONTRIBUTING.md](CONTRIBUTING.md) and the relevant `AGENTS.md` before
changing code. In short:

- Commit source, tests, reviewed migrations, docs, lockfiles, example env files,
  and small reviewed corpus fixtures needed for reproducibility.
- Do not commit secrets, real `.env` files, raw downloads, database dumps, logs,
  virtual environments, `node_modules`, build output, or unreviewed large data.
- Update docs and `.env.example` files whenever behavior or configuration
  changes.
- Keep the fast backend suite, Ruff, frontend lint, and frontend build green.

## Further documentation

| Document | Purpose |
| --- | --- |
| [Technical guide](docs/technical-guide.md) | Current architecture, data model, request flows, and algorithms |
| [Project review](docs/project-review.md) | Prioritized release blockers and optimizations |
| [Implementation checklist](docs/todo.md) | Remaining manual validation and deployment work |
| [Supabase setup](docs/guides/supabase-setup.md) | Hosted Postgres and email auth setup |
| [Backend README](backend/README.md) | Backend commands and module map |
| [Frontend README](frontend/README.md) | Frontend commands and runtime notes |

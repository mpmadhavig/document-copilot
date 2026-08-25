# Document Copilot

An internal AI chatbot that lets analysts query a corpus of documents in plain English and get sourced, citable answers.

## The client

**Driftwood Capital** — fictional independent investment research firm. Their analysts spend half their week reading 10-Ks and 10-Qs before they can produce any original analysis. Document Copilot eats that intake work so they can skip straight to insight.

Full brief: [docs/client-brief.md](docs/client-brief.md)

## Stack

| Layer              | Choice                                               |
| ------------------ | ---------------------------------------------------- |
| Backend            | Python + FastAPI                                     |
| Frontend           | Vite + React SPA + TypeScript                        |
| Database           | Supabase Postgres (users, chats, documents, chunks)  |
| Migrations         | SQLAlchemy models + Alembic                          |
| Retrieval          | Supabase `pgvector` + Postgres full-text search      |
| Auth               | Supabase Auth (email only)                           |
| Hosting            | Railway                                              |
| LLM + embeddings   | OpenAI                                               |

## Repo layout

```text
document-copilot/
├── AGENTS.md           # agent instructions (read first)
├── README.md           # this file
├── data/               # local corpus + download script (payloads gitignored)
├── docs/
│   └── client-brief.md # the client one-pager
├── backend/            # FastAPI service
└── frontend/           # React SPA (Vite)
```

## Prerequisites

Install these before setting up `backend/` or `frontend/`:

| Tool | Version | Used for | Install |
| ---- | ------- | -------- | ------- |
| [Python](https://www.python.org/downloads/) | 3.12+ | Backend runtime | OS package manager or python.org |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | Backend deps + `data/download.py` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Node.js](https://nodejs.org/) | 20+ (LTS) | Frontend toolchain | nodejs.org or `nvm install --lts` |
| [pnpm](https://pnpm.io/installation) | latest | Frontend package manager | `corepack enable && corepack prepare pnpm@latest --activate` |

You also need accounts/keys for external services once the app is wired up. Start with [docs/guides/supabase-setup.md](docs/guides/supabase-setup.md) (account + project), then create an [OpenAI API key](https://platform.openai.com/api-keys) when the LLM layer is wired up.

## Running locally

Use two terminals from the repository root. On first setup, copy each example environment file and replace its placeholder values.

Terminal 1 — FastAPI:

```bash
cd backend
test -f .env || cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Confirm the API at <http://127.0.0.1:8000/health>.

Terminal 2 — React:

```bash
cd frontend
test -f .env || cp .env.example .env
pnpm install
pnpm dev
```

Open the URL printed by Vite, normally <http://localhost:5173>. The frontend origin must appear in the backend `ALLOWED_ORIGINS` setting.

### Citation acceptance check

1. Sign in, create a research thread, and ask a question that the ingested corpus can answer.
2. Wait for the grounded answer and confirm that inline markers such as `[1]` and source chips appear.
3. Click an inline marker. Confirm that the source panel shows the expected company, filing, page or section, and an exact supporting quote.
4. Click the corresponding source chip and confirm it selects the same passage.
5. Open the original filing and search for a distinctive phrase from the quote when you want to verify it against the SEC document itself.
6. Reload the browser, reopen the thread, and repeat steps 3–4 to verify persisted citation metadata.

### Troubleshooting with error references

User-visible failures include a reference beginning with `be-` or `fe-` and the
log file that contains its technical details. Logs are newline-delimited JSON,
rotate at 5 MB, and retain five backups.

```bash
# Backend/API/model/database failures
tail -f backend/logs/backend.log

# Browser/React/network/auth failures collected by the Vite server
tail -f frontend/logs/frontend.log

# Find one reported failure
rg 'be-123456789abc' backend/logs/backend.log*
rg 'fe-12345678-1234' frontend/logs/frontend.log*
```

The frontend collector runs with both `pnpm dev` and `pnpm preview`. Reports are
size-limited and contain only the error name/message/stack, route, browser user
agent, operation name, and reference IDs. Chat text, credentials, access tokens,
and API response bodies are not logged.

Railway container filesystems are ephemeral. Attach a persistent volume to each
service's `logs/` directory if these files must survive a restart or redeploy;
the same entries continue to be available in the live service output.

Additional setup guides:

- [Supabase](docs/guides/supabase-setup.md) — account, hosted project (dashboard or CLI)
- [Backend](docs/guides/backend-setup.md)
- [Frontend](docs/guides/frontend-setup.md)

## Sample SEC data

Use the standalone downloader to fetch a small local 10-K sample from SEC EDGAR.
Edit the params at the top of `data/download.py`, especially `USER_AGENT`, then run:

```bash
uv run data/download.py
```

By default this downloads the latest 5 10-K filings for AAPL, MSFT, NVDA, AMZN, and GOOGL into year folders under `data/downloads/` and writes a `manifest.json`.
Downloaded files are gitignored; the `data/` folder itself stays in git for the script and notes.

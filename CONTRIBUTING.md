# Contributing to Document Copilot

This guide is for future development of the existing FastAPI, React, Supabase,
and OpenAI implementation. The stack is intentionally fixed; read
[`AGENTS.md`](AGENTS.md), then the `AGENTS.md` inside the service you are
changing.

## Start a change

1. Create a focused branch from the current integration branch.
2. Copy the example environment files locally; never edit them with real keys.
3. Install from the committed lockfiles with `uv sync --locked` and
   `pnpm install --frozen-lockfile`.
4. Make the smallest change that completes one behavior.
5. Add or update tests at the same boundary as the changed backend behavior.
6. Update user, configuration, deployment, or technical documentation when its
   contract changes.
7. Run the checks below before opening a pull request.

## Engineering conventions

### Configuration

- Backend environment access belongs in `backend/app/config.py`.
- Frontend environment access belongs in `frontend/src/lib/env.ts`.
- Required configuration must fail at startup; do not add silent defaults for
  credentials or production URLs.
- Add safe placeholders and comments to the relevant `.env.example` whenever a
  setting is introduced.

### Backend

- Keep request-path network I/O asynchronous.
- Validate HTTP, model, database, and external-service boundaries; trust typed
  internal callers.
- Preserve the grounding invariant: no answered statement without at least one
  exact quote from evidence exposed during the current run.
- Put normal schema changes in SQLAlchemy models. Put Postgres functions,
  `pgvector`, indexes, RLS, triggers, and policies explicitly in reviewed
  Alembic migrations.
- Mark tests requiring Supabase or OpenAI with `@pytest.mark.integration`.

### Frontend

- Keep the application a Vite React SPA.
- Use `@/` imports, Tailwind classes, native `fetch` through the existing API
  clients, and Supabase email auth.
- Do not add a frontend test runner. Verify with strict TypeScript compilation,
  ESLint, and the production build, as required by `frontend/AGENTS.md`.
- Never expose the Supabase service-role key, database URL, or OpenAI key in a
  `VITE_*` variable.

### Dependencies

Prefer platform and standard-library APIs. Before adding a runtime dependency,
document in the commit message:

1. What it does that cannot be written clearly in fewer than about 30 lines.
2. How often the project uses it.
3. Its maintenance and transitive-dependency footprint.

Use `uv` for Python and `pnpm` for JavaScript. Commit the updated lockfile with
the dependency declaration.

## Database changes

From `backend/`:

```bash
uv run alembic revision --autogenerate -m "describe the schema change"
```

Review the generated file rather than treating it as final. In particular,
confirm:

- upgrade and downgrade order;
- indexes and constraints;
- foreign-key deletion behavior;
- RLS enabled on every user-facing table;
- least-privilege grants for functions and triggers;
- compatibility with the existing `vector(1536)` schema.

Apply the complete chain to a non-production Supabase project:

```bash
uv run alembic upgrade head
uv run alembic heads
```

Never modify production tables manually in the Supabase dashboard.

## Required checks

```bash
cd backend
uv run pytest -m "not integration"
uv run ruff check app ingest tests scripts
uv run alembic heads

cd ../frontend
pnpm lint
pnpm build
```

Run live evaluations when retrieval, prompts, tools, model configuration, or
grounding changes. They use external services and the grounding run incurs
OpenAI cost:

```bash
cd backend
uv run python -m scripts.evaluate_retrieval
uv run python -m scripts.evaluate_grounding --confirm-live-calls
```

Manually check sign-in, thread creation, a supported answer, an insufficient
evidence answer, a refused investment recommendation, citation selection, and
history after reload for release-affecting changes.

## What belongs in Git

| Include | Exclude |
| --- | --- |
| Application and ingestion source | Real `.env` files and credentials |
| Backend tests and evaluation case definitions | Live API responses containing sensitive data |
| Reviewed Alembic migrations | Database dumps and ad hoc production SQL |
| Root/service docs and operational runbooks | Logs, coverage, caches, build output |
| `uv.lock` and `pnpm-lock.yaml` | `.venv`, `node_modules`, editor state |
| Safe `.env.example` files | Raw SEC downloads under `data/downloads/` |
| Small, reviewed normalized fixtures/corpus files | Unreviewed generated or large binary data |

Before adding a data file, confirm its provenance, redistribution terms,
purpose, expected update process, and size. Prefer a reproducible downloader and
checksum-bearing manifest over committing raw payloads. Update `.gitignore`
before generating a new artifact class.

## Pull request checklist

- The change has one clear purpose and no unrelated cleanup.
- Configuration remains centralized and examples are current.
- Database changes include a reviewed migration and RLS impact.
- Backend tests and static checks pass.
- Frontend lint and build pass when frontend code changed.
- Live evaluations were run or explicitly marked not run with a reason.
- User-facing and technical documentation matches the new behavior.
- No secrets, logs, generated output, or unexpected large files are present in
  `git diff --cached`.

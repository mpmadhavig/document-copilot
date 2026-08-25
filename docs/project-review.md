# Project review and release priorities

Review date: 2026-08-25

## Assessment

Document Copilot has a strong local pilot foundation. The core RAG path is
implemented end to end, the backend test suite is healthy, persistence is
transactional, RLS is present, and grounding is enforced in code rather than
left entirely to a prompt.

It is not production-ready yet. The highest-risk gaps are deployment
configuration, live acceptance evidence, request/cost controls, and operational
readiness. Address the release blockers below before inviting external users.

## What is already strong

- The semantic and lexical retrievers are independent and fused deterministically.
- Grounding fails closed against request-scoped evidence and exact quotes.
- The model output, SSE data parts, stored messages, and citation UI share a
  clear typed contract.
- The database RPC writes both sides of a turn and all citations atomically.
- RLS protects user chats while keeping the curated corpus readable to signed-in
  analysts.
- Ingestion is reproducible, idempotent, budget-gated, and well covered by unit
  tests.
- Error references connect safe UI messages to structured backend/frontend logs.
- Dependencies and lockfiles are present, and the repository has a conservative
  dependency policy.

## P0: complete before production deployment

### 1. Make production CORS configuration possible

`backend/app/config.py` currently requires `ALLOWED_ORIGINS` to equal only
`http://localhost:5173`. Any Railway frontend URL makes backend startup fail.

Change the validator to accept a non-empty, explicit comma-separated allowlist;
reject wildcards and invalid schemes. Keep the local origin in `.env.example`,
add tests for one and multiple HTTPS production origins, and deploy with the
exact Railway frontend origin.

### 2. Define and test the Railway runtime contract

There is no committed Railway configuration or production start script. The
frontend's browser-log endpoint exists only in Vite development/preview
middleware, while `vite preview` is not yet documented as an intentional
production server.

Choose and document the service root, install/build/start commands, health-check
path, port binding, SPA fallback, migration step, and frontend log-collector
behavior. Then deploy a staging environment from a clean checkout. Decide
whether file logs use persistent volumes or whether stdout is the source of
truth.

### 3. Run the live acceptance matrix

The remaining checks in `docs/todo.md` are product-critical: the 10 client-brief
questions, citation-to-source verification, refusal/insufficient-evidence cases,
history across sessions, concurrent users, and deployed end-to-end behavior.

Run both evaluation scripts against the production-shaped corpus, save summary
metrics without prompts or secrets, and manually review the evidence rather than
treating term presence as answer quality. Include latency and cost per case.

### 4. Establish production data operations

Dry-run the full Alembic chain on a disposable/staging Supabase project, confirm
the Auth trigger for existing and new users, and write rollback/restore steps.
Define backup ownership, corpus refresh ownership, retention for chats/logs, and
the procedure for rotating Supabase/OpenAI credentials.

## P1: high-value hardening and optimization

### 5. Add automated CI gates

No CI workflow currently enforces the checks. Add a pipeline for the fast
backend tests, Ruff, frontend lint, and frontend production build. Pin the Node
and pnpm versions (for example with `packageManager` and the CI runtime) so local
and CI installs use the same toolchain.

Keep live Supabase/OpenAI evaluations manual or scheduled with protected secrets;
they should not run on every pull request.

### 6. Bound input size, concurrency, and model spend

Thread titles and model outputs are bounded, but incoming UI message IDs, part
counts, part payloads, and prompt text have no explicit maximum. The server also
has per-run tool/token limits but no per-user request rate or concurrency limit.

Accept and persist a canonical latest user text part, impose request/prompt
limits, reject oversized bodies at the API/proxy boundary, and add per-user
concurrency/rate controls. Record model/embedding usage, duration, status, and
request reference without recording prompt content. Add budget alerts before a
larger pilot.

### 7. Improve perceived streaming and measure latency

The API sends an immediate SSE start event, but it waits for structured model
completion and database persistence before sending answer text. Word deltas then
simulate progressive delivery.

First measure time to stream-open, first progress, first text, completed model,
and completed persistence. Add safe progress/heartbeat events so proxies and
users can see activity. If true token streaming is later introduced, preserve
the rule that unvalidated content must never appear as a trusted grounded answer.

### 8. Reduce request-path client and auth overhead

Authenticated routes currently construct separate Supabase clients for token
verification and database work. Thread authorization also constructs a
service-role client for each ownership check and exposes `403` versus `404` for
UUIDs outside the user's RLS view.

Use one request-scoped auth context where practical, close/reuse underlying HTTP
clients correctly, and prefer the user-scoped RLS lookup with a uniform `404`
unless the product genuinely needs cross-user existence disclosure. Load-test
these changes before optimizing further.

### 9. Add readiness and service-level telemetry

`GET /health` proves only that FastAPI can answer. Add a separate readiness
check for required runtime dependencies, while keeping liveness cheap. Track
request counts, error categories, retrieval/model/database duration, time to
first text, token usage, and answer status. Do not place prompts or source text in
metrics.

### 10. Strengthen retrieval evaluation before tuning

The current retrieval evaluator passes when any expected term appears anywhere
in the returned passages. Add labeled relevant chunk/document IDs and calculate
Recall@k, MRR, and per-case regressions. Then tune semantic/lexical weights,
candidate limits, neighbor windows, and relevance cutoffs from evidence rather
than intuition. Consider a small standard-library-only query/result cache only
after measuring repeated-query load and defining user/data invalidation rules.

## P2: product and repository polish

- Add thread deletion and define whether it is soft delete, hard delete, or
  retention-driven deletion.
- Remove unused Vite starter files/assets and change the HTML title from
  `frontend` to `Document Copilot`.
- Replace hard-coded UI corpus counts with backend-provided corpus metadata or
  remove the count so it cannot drift after ingestion.
- Replace scaffold-oriented setup docs with operational runbooks as deployment
  decisions are finalized.
- Add a license only after the owner chooses the intended reuse terms; do not
  infer one.
- Document accessibility and browser checks for keyboard navigation, focus,
  narrow screens, reduced motion, and the citation panel.

## Verification performed for this review

| Check | Result |
| --- | --- |
| `uv run pytest -m "not integration"` | 84 passed, 1 deselected |
| `uv run ruff check app ingest tests scripts` | Passed |
| `uv run alembic heads` | One head: `20260824_06` |
| Python bytecode compilation | Passed |
| Tracked-secret pattern scan | No non-example credential found |
| Frontend lint/build | Not run: Node.js was not available on the review machine's active PATH |
| Live retrieval integration | Not run: requires live Supabase/OpenAI access |
| Paid grounding evaluation | Not run: requires explicit paid-call confirmation |

The unrun frontend and live checks are verification gaps, not observed failures.

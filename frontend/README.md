# Document Copilot frontend

The frontend is a Vite React SPA for Supabase email authentication, private chat
threads, AI SDK-compatible streaming, and citation/source inspection.

Read the [root README](../README.md) for complete setup and
[the technical guide](../docs/technical-guide.md) for the wire contract and
component boundaries.

## Configure and run

```bash
cp .env.example .env
# Set the backend URL and public Supabase values.
pnpm install --frozen-lockfile
pnpm dev
```

Open <http://localhost:5173>. Only browser-safe values belong in `.env`:

- `VITE_API_BASE_URL`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

Never place the service-role key, database URL, or OpenAI key in a `VITE_*`
variable.

## Checks

```bash
pnpm lint
pnpm build
```

This project intentionally has no frontend test runner. Follow
[`frontend/AGENTS.md`](AGENTS.md) and manually verify auth, chat, citations,
source selection, errors, and reload behavior for release-affecting changes.

## Runtime map

```text
src/Router.tsx             auth and protected chat routes
src/components/auth/       session gate
src/components/chat/       conversation, citation, source, and sidebar UI
src/lib/env.ts             validated build-time configuration
src/lib/http.ts            JSON fetch client and typed errors
src/lib/chatTransport.ts   chat fetch errors and auth recovery
src/lib/chat.ts            message and data-part types
src/lib/supabase.ts        browser auth client
server/clientLogPlugin.ts  same-origin Vite client-error collector
```

## Browser error logs

During `pnpm dev` and `pnpm preview`, browser and React failures are posted to
the same-origin Vite middleware and written as rotating JSON lines in
`logs/frontend.log`:

```bash
rg 'fe-reference-from-the-ui' logs/frontend.log*
```

The collector excludes prompts, passwords, tokens, and API response bodies. The
production serving/logging decision is still a release blocker; see the
[project review](../docs/project-review.md).

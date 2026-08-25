# Frontend setup guide

The browser application is a Vite React SPA. It uses Supabase email auth and
sends authenticated JSON/SSE requests to the separate FastAPI service.

## First setup

```bash
cd frontend
cp .env.example .env
# Set the public Supabase values and backend URL.
pnpm install --frozen-lockfile
```

Do not put server credentials in the frontend environment. Any `VITE_*` value is
available to browser code.

## Run and check

```bash
pnpm dev
pnpm lint
pnpm build
```

The application normally opens at <http://localhost:5173>; the backend's
`ALLOWED_ORIGINS` must contain the exact browser origin.

The project intentionally does not use a frontend test runner. Manually verify
authentication, threads, streaming, errors, citations, source selection, and
history reload after release-affecting changes.

## Next steps

- [Root setup and usage](../../README.md)
- [Frontend command reference](../../frontend/README.md)
- [Technical guide](../technical-guide.md)
- [Contribution policy](../../CONTRIBUTING.md)

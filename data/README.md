# Data

Local data artifacts for development live here.

- `downloads/` holds raw source files fetched from SEC EDGAR, grouped by year.
- `markdown/` holds normalized Markdown generated from the HTML filings.
- Downloaded payloads are gitignored because the corpus can get large.
- Fetch a sample corpus with `uv run data/download.py`.

Convert the downloaded filings from the backend directory so Docling and the
normalization dependencies are available:

```bash
cd backend
uv run python -m ingest.convert_filings ../data/downloads ../data/markdown
```

The converter collapses SEC presentation-grid spans into semantic columns,
removes empty layout rows, retains exhibit links, and adds Markdown section
headings. Source images are represented by comments because the standalone
HTML downloads do not include their referenced image assets.

Import or update the normalized documents in the configured database:

```bash
cd backend
uv run python -m ingest.import_documents \
  ../data/downloads/manifest.json ../data/markdown
```

Preview Docling hierarchical chunks without calling OpenAI or writing to the
database:

```bash
cd backend
uv run python -m ingest.chunk_documents \
  ../data/downloads/manifest.json ../data/markdown \
  --ticker AAPL --year 2021 --find "net sales"
```

After reviewing the chosen chunk, make exactly one embedding request. This
command never writes to the database:

```bash
uv run python -m ingest.embed_chunks \
  ../data/downloads/manifest.json ../data/markdown \
  --ticker AAPL --year 2021 --chunk-index CHUNK_INDEX \
  --confirm-one-api-call
```

Estimate the remaining corpus before making paid requests:

```bash
uv run python -m ingest.import_chunks \
  ../data/downloads/manifest.json ../data/markdown --estimate
```

Use the exact estimate as an explicit spending guard when importing all
remaining chunks. Completed documents are skipped on reruns:

```bash
uv run python -m ingest.import_chunks \
  ../data/downloads/manifest.json ../data/markdown \
  --all --max-total-tokens ESTIMATED_TOKENS \
  --tokens-per-minute ACCOUNT_TPM_LIMIT
```

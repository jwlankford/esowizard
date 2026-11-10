# ESO Wizard

ESO Wizard answers natural-language questions about The Elder Scrolls Online using **retrieval-augmented generation (RAG)**: answers are grounded in a knowledge base stored in Neon PostgreSQL (pgvector), not in the LLM's memory. **The knowledge base starts empty; no ESO content is included or invented.** No scraping exists; knowledge is added only through a controlled manual import.

Stack: Vue 3 + TypeScript + Vite + Pinia + Tailwind · FastAPI + SQLAlchemy (async) + Alembic · Neon PostgreSQL + pgvector · Google Gemini (generation and embeddings).

## RAG architecture

```
User
 ↓
Vue  (never sees secrets)
 ↓
FastAPI  /api/v1/ask
 ↓
RAGService ── normalise query, detect category hint
 ↓
Gemini embeddings (RETRIEVAL_QUERY)
 ↓
Neon + pgvector (cosine search, optional category filter)
 ↓
Score threshold ── nothing relevant? → "insufficient_knowledge" (Gemini is NOT called)
 ↓
Retrieved ESO context (numbered excerpts)
 ↓
Google Gemini (grounded system instruction)
 ↓
Backend maps cited excerpt numbers → documents → sources (URLs never come from the model)
 ↓
Structured answer { status, answer, sources } → Vue
```

Ingestion (manual, offline files only): `JSON file → loader → Pydantic validation → normaliser (+ SHA-256 hash) → chunker → Gemini embeddings (RETRIEVAL_DOCUMENT) → Neon`.

Key modules (`backend/`):

| Path | Responsibility |
| --- | --- |
| `app/core/config.py` | All settings (database URLs, pooling, embedding dimensions, chunking, threshold) |
| `app/core/categories.py` | `ESOCategory` enum (single source of category values) and `SourceType` |
| `app/db/session.py` | Async engine/session factory; the only place pooling is configured |
| `app/models/knowledge.py` | `KnowledgeSource`, `KnowledgeDocument`, `KnowledgeChunk` (pgvector) |
| `app/repositories/knowledge.py` | All knowledge SQL, including the vector search |
| `app/services/ai/` | `AIProvider`, `EmbeddingProvider` abstractions and Gemini implementations |
| `app/services/knowledge/` | `normalizer`, `chunking`, `ingestion`, `embeddings`, `retrieval`, `context` |
| `app/services/rag.py` | `RAGService` orchestration |
| `ingestion/` | CLIs: `import_document`, `search`, `check_db` |

## Neon setup

1. Create a Neon project and database. In the Neon console copy the **pooled** connection string (host contains `-pooler`) and the **direct** one.
2. `cp .env.example .env` and set `DATABASE_URL` (pooled) and, recommended, `DATABASE_DIRECT_URL` (direct; used by Alembic). `postgresql://…?sslmode=require` URLs are accepted as-is; they are converted internally for asyncpg (`ssl=require`) and psycopg. `.env` is git-ignored; never commit it.
3. Neon's pooler already multiplexes connections, so the app pool is small by default (`DB_POOL_SIZE=3`, `DB_MAX_OVERFLOW=2`) and asyncpg's prepared-statement cache is off (`DB_STATEMENT_CACHE_SIZE=0`), as PgBouncer transaction pooling requires. Adjust in `.env`/`app/db/session.py` only.
4. `python -m ingestion.check_db` confirms connectivity and that pgvector is installed.

## pgvector

Migration `0001` runs `CREATE EXTENSION IF NOT EXISTS vector`. Embeddings are stored in `knowledge_chunks.embedding` (`vector(EMBEDDING_DIMENSIONS)`, default **768**, requested from Gemini via `output_dimensionality`). The width is configured in one place (`EMBEDDING_DIMENSIONS`) and validated on every provider response. Changing the model or dimension requires a new migration and re-embedding all chunks. Similarity is cosine; `score = 1 − cosine distance`. No ANN index is created yet: exact search is correct and fast for a small corpus. Add an HNSW index (`USING hnsw (embedding vector_cosine_ops)`) in a later migration when the corpus grows.

## Configuration

Backend-only environment variables (see `.env.example`; none reach Vue):

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Neon connection string used by the API (pooled recommended) |
| `DATABASE_DIRECT_URL` | Optional direct string for Alembic/admin; falls back to `DATABASE_URL` |
| `GOOGLE_API_KEY` | Gemini API key |
| `GEMINI_MODEL` / `GEMINI_EMBEDDING_MODEL` | Generation / embedding models (defaults `gemini-2.5-flash`, `gemini-embedding-001`) |
| `EMBEDDING_DIMENSIONS` | Vector width (default 768) |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Chunk size/overlap in characters (1000 / 150) |
| `RAG_TOP_K` | Chunks retrieved for `/ask` (5) |
| `RETRIEVAL_MIN_SCORE` | Minimum cosine similarity to use a chunk as context (0.5) |

> **`RETRIEVAL_MIN_SCORE` is an untested development default.** Tune it against real data and the chosen embedding model: use `/api/v1/search` or `python -m ingestion.search` to inspect scores for answerable and unanswerable questions, then set a threshold separating them.

## Migrations

```sh
cd backend
alembic upgrade head      # runs against DATABASE_DIRECT_URL, else DATABASE_URL
alembic current
```

Alembic is the only source of schema changes (`create_all` is never used). Revision `0002` upgrades the Phase 1 schema in place: it preserves existing rows, creates `knowledge_sources` from the legacy per-document source columns and maps legacy display-name categories (e.g. `Fishing`) to the new enum values. Existing embeddings are kept; legacy documents are re-embedded the next time they are re-imported with changed content.

## Importing knowledge

Only authorised, locally supplied content may be imported. Import format (one object or a list):

```json
{
  "title": "Example document",
  "category": "CRAFTING",
  "source": { "name": "Example Source", "url": "https://example.com", "source_type": "manual" },
  "external_id": "optional-stable-id",
  "canonical_url": "https://example.com/page",
  "content": "# Heading\n\nKnowledge content goes here.",
  "metadata": {}
}
```

Documents are validated (categories, `http(s)` URLs, size limits, no unknown fields), normalised, hashed and chunked on headings/paragraphs/lists (every chunk carries its title, category and section). A document is identified by `(source, external_id)` (defaults to a slug of the title):

- new → chunk, embed, store;
- changed (title/category/content hash differs) → old chunks replaced, new embeddings generated;
- unchanged → no embedding calls.

```sh
cd backend
python -m ingestion.import_document --file ../data/example.json --dry-run   # validate only
python -m ingestion.import_document --file ../data/example.json
```

`data/example.json` is a clearly **synthetic** format demonstration, not game knowledge. Prefer concise factual summaries, metadata and source references over copying third-party pages, and do not ingest a third-party source until its licensing strategy is decided.

## Semantic search and ask

```sh
python -m ingestion.search "Perfect Roe" --category FISHING --limit 5   # from backend/
```

- `POST /api/v1/search` `{ "query", "category"?, "limit" }` → ranked chunks with `document_id`, `title`, `category`, `content`, `score`, `source_name`, `source_url`. No Gemini generation and no threshold, so it is useful for tuning.
- `POST /api/v1/ask` `{ "question", "category"? }` → `{ question, answer, category, status, sources[], related_queries[] }` where `status` is `answered`, `insufficient_knowledge` or `error` (`error` is returned with HTTP 502). When retrieval finds nothing above the threshold, or Gemini reports the excerpts are insufficient, the answer is the fixed insufficient-knowledge message with no sources; Gemini is never asked to answer from memory.
- `GET /api/v1/health` (liveness), `/health/database` (Neon + pgvector), `/health/ai` (configuration only, no Gemini call), `GET /api/v1/categories`.

Logs include request ID (`X-Request-ID` header), category, retrieval count, embedding/search/LLM/total durations, and never API keys, connection strings or full prompts.

## Running

Docker Compose runs only the frontend and backend; Neon is remote and read from `.env`.

```sh
cp .env.example .env     # set DATABASE_URL, GOOGLE_API_KEY
docker compose up --build
```

Open http://localhost:5173 (API docs: http://localhost:8000/docs). Run migrations first (below).

Local development (Python 3.12+, Node 24):

```sh
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
# another terminal
cd frontend && npm ci && npm run dev
```

A `Makefile` wraps these: `make backend`, `make frontend`, `make test`, `make lint`, `make migrate`, `make db-check`, `make import FILE=data/example.json`, `make search Q="Perfect Roe"`.

## Tests and linting

```sh
cd backend
ruff check app tests alembic ingestion && ruff format --check app tests alembic ingestion
pytest -q -m "not integration"      # unit tests: fakes only, no Gemini, no database
pytest -q -m integration            # needs TEST_DATABASE_URL (disposable, migrated, pgvector)
cd ../frontend && npm run lint && npm run build
```

Tests never call Gemini or need Neon credentials. Test fixtures are labelled synthetic.

## Troubleshooting database connectivity

- Run `python -m ingestion.check_db`; it prints the error class only, never the connection string.
- `ssl`/`sslmode` errors: keep `?sslmode=require` in the URL; it is translated for asyncpg.
- Timeouts right after idle: Neon computes auto-suspend; the first connection can take a few seconds (`DB_CONNECT_TIMEOUT_SECONDS`).
- `prepared statement … does not exist` / PgBouncer errors: keep `DB_STATEMENT_CACHE_SIZE=0`.
- Migration errors on the pooled endpoint: set `DATABASE_DIRECT_URL` to the direct endpoint.
- `pgvector extension is not installed`: run `alembic upgrade head` (or `CREATE EXTENSION vector;` as a privileged user).
- Dimension errors: `EMBEDDING_DIMENSIONS` must match the migrated column and the data already stored.

## Security

`GOOGLE_API_KEY` and database credentials are backend-only and never logged; `.env` is git-ignored; inputs and imported metadata/URLs are validated; all SQL is parameterised and confined to the repository layer; retrieved text and questions are treated as data in the prompt, and citations are resolved server-side from retrieved documents.

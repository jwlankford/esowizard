# ESO Wizard

ESO Wizard is a starter application for asking natural-language questions about The Elder Scrolls Online. It uses a Vue 3 frontend, a FastAPI backend, PostgreSQL with pgvector, and Google's Gemini API. The knowledge base starts empty; no ESO content is included or invented.

## Start with Docker Compose

1. Copy `.env.example` to `.env` and set `GOOGLE_API_KEY` to your own Gemini API key. Never commit `.env`. The health and categories endpoints work without a key; search and ask require one.
2. Run `docker compose up --build`. The API applies Alembic migrations when it starts.
3. Open http://localhost:5173. API documentation is at http://localhost:8000/docs.

The database and application ports bind to localhost. Compose uses PostgreSQL trust authentication **for local development only**; do not expose this database or use this configuration in production. Data persists in the `postgres_data` volume. Use `docker compose down` to stop, or `docker compose down -v` to also delete local data.

## Local development

With Python 3.12, Node.js 24 and a PostgreSQL database with the pgvector extension available:

```sh
cp .env.example .env
# Set GOOGLE_API_KEY and DATABASE_URL in .env.
set -a; . ./.env; set +a
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

The Vite development server proxies `/api` to the backend. `DATABASE_URL`, `GOOGLE_API_KEY`, `GEMINI_MODEL`, and `GEMINI_EMBEDDING_MODEL` configure the backend. The default Gemini embedding model is configured to produce 768-dimensional vectors; documents must be indexed with the same model and dimensions as queries. Changing embedding models requires re-embedding existing chunks.

## API and architecture

- `GET /api/v1/health` reports API process health (not database or provider readiness).
- `GET /api/v1/categories` lists supported ESO domains.
- `POST /api/v1/search` takes `query`, optional `category`, and `limit` (1–50) and returns matching source chunks.
- `POST /api/v1/ask` takes `question` and optional `category`, retrieves source chunks, and returns an answer and ordered sources. Citation numbers in the answer correspond to the returned source order. If no chunks are found, no generated answer is requested.

The API uses an `AIProvider` interface, with Gemini implemented separately. Retrieval embeds the normalized query and ranks stored chunks by cosine distance. The ask service constructs a grounded prompt from retrieved sources. Source data is untrusted: generated answers and citations should be verified. No relevance threshold or automatic intent classification is implemented yet; category filtering is explicit.

Alembic creates document and chunk tables and the pgvector extension. Ingestion, source licensing, cleaning, chunking, and indexing are intentionally not implemented yet; add only appropriately licensed, verified sources, and record their URLs and metadata. No seed data is provided. Retrieval requires chunks with 768-dimensional embeddings in the database.

## Checks

```sh
cd backend
ruff check app tests alembic
ruff format --check app tests alembic
pytest -q
cd ../frontend
npm run lint
npm run format:check
npm run build
```

Set `TEST_DATABASE_URL` to a migrated, disposable PostgreSQL database to run the database integration test. Tests use fake AI providers and do not call Gemini.

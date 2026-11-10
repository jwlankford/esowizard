from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# libpq-only parameters that asyncpg does not understand.
_ASYNCPG_DROPPED_PARAMS = {"channel_binding", "sslmode"}
_SSL_MODES = {"require", "verify-ca", "verify-full"}


def _rewrite_url(url: str, driver: str) -> str:
    """Return ``url`` using the SQLAlchemy driver ``driver``, translating Neon/libpq parameters."""
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    if driver == "asyncpg":
        ssl_required = any(k == "sslmode" and v in _SSL_MODES for k, v in query)
        query = [(k, v) for k, v in query if k not in _ASYNCPG_DROPPED_PARAMS]
        if ssl_required and not any(k == "ssl" for k, _ in query):
            query.append(("ssl", "require"))
    scheme = f"postgresql+{driver}"
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Neon PostgreSQL. DATABASE_URL is typically Neon's pooled endpoint; DATABASE_DIRECT_URL
    # (optional) is used for migrations and admin tasks. Either may be written as postgresql://,
    # postgresql+asyncpg:// or postgresql+psycopg://; it is converted to the right driver.
    database_url: str = "postgresql+asyncpg://localhost:5432/esowizard"
    database_direct_url: str = ""
    # Pooling is centralised here. Neon's pooler (PgBouncer) already multiplexes connections, so
    # the application-side pool is kept small.
    db_pool_size: int = Field(default=3, ge=1)
    db_max_overflow: int = Field(default=2, ge=0)
    db_pool_recycle_seconds: int = Field(default=300, ge=30)
    db_connect_timeout_seconds: int = Field(default=15, ge=1)
    # 0 disables asyncpg's prepared-statement cache, required behind PgBouncer transaction pooling.
    db_statement_cache_size: int = Field(default=0, ge=0)

    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    # Single source of truth for vector width. Changing it needs a migration and re-embedding.
    embedding_dimensions: int = Field(default=768, ge=1)
    embedding_batch_size: int = Field(default=50, ge=1, le=100)

    chunk_size: int = Field(default=1000, ge=100, description="Maximum characters per chunk")
    chunk_overlap: int = Field(default=150, ge=0, description="Characters repeated between chunks")

    rag_top_k: int = Field(default=5, ge=1, le=20)
    # Minimum cosine similarity (1 - cosine distance) for a chunk to be used as RAG context.
    # DEVELOPMENT DEFAULT: it must be tuned against real data and the chosen embedding model.
    retrieval_min_score: float = Field(default=0.5, ge=0.0, le=1.0)

    log_level: str = "INFO"

    @model_validator(mode="after")
    def _check_chunking(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return self

    @property
    def async_database_url(self) -> str:
        return _rewrite_url(self.database_url, "asyncpg")

    @property
    def sync_database_url(self) -> str:
        """URL for Alembic and admin tasks: the direct URL when provided, else DATABASE_URL."""
        return _rewrite_url(self.database_direct_url or self.database_url, "psycopg")


@lru_cache
def get_settings() -> Settings:
    return Settings()

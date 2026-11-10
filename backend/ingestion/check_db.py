"""Check connectivity to the configured Neon database and the pgvector extension.

python -m ingestion.check_db
"""

import asyncio
import sys

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import dispose_engine, get_sessionmaker
from app.repositories.knowledge import KnowledgeRepository


async def run() -> int:
    settings = get_settings()
    print(f"Embedding dimensions: {settings.embedding_dimensions}")
    try:
        async with get_sessionmaker()() as session:
            vector_installed = await KnowledgeRepository(session).check_connection()
            version = await session.scalar(text("SHOW server_version"))
            tables = await session.scalar(
                text(
                    "SELECT count(*) FROM information_schema.tables WHERE table_name LIKE 'knowledge_%'"
                )
            )
    except Exception as exc:  # noqa: BLE001
        # Never print the exception message: it can echo connection details.
        print(f"error: cannot connect to the database ({type(exc).__name__}).", file=sys.stderr)
        print("Check DATABASE_URL, network access and Neon compute state.", file=sys.stderr)
        return 1
    finally:
        await dispose_engine()
    print(f"Connected. PostgreSQL {version}")
    print(f"pgvector installed: {vector_installed}")
    print(f"knowledge tables found: {tables} (run `alembic upgrade head` if 0)")
    return 0 if vector_installed else 1


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()

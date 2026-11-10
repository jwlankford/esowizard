"""Semantic search over the knowledge base from the command line (no Gemini generation).

python -m ingestion.search "Perfect Roe" --category FISHING --limit 5
"""

import argparse
import asyncio
import logging
import sys

from app.core.categories import ESOCategory
from app.core.config import get_settings
from app.db.session import dispose_engine, get_sessionmaker
from app.repositories.knowledge import KnowledgeRepository
from app.services.ai.provider import ProviderError
from app.services.knowledge.embeddings import create_embedding_provider
from app.services.knowledge.retrieval import KnowledgeRetrievalService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("query")
    parser.add_argument("--category", type=ESOCategory, choices=list(ESOCategory))
    parser.add_argument("--limit", type=int, default=5)
    return parser


async def run(query: str, category: ESOCategory | None, limit: int) -> int:
    try:
        embedder = create_embedding_provider(get_settings())
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        async with get_sessionmaker()() as session:
            service = KnowledgeRetrievalService(KnowledgeRepository(session), embedder)
            results = await service.retrieve(" ".join(query.split()), category, limit)
    except ProviderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"error: search failed ({type(exc).__name__})", file=sys.stderr)
        return 1
    finally:
        await dispose_engine()
    if not results:
        print("No results.")
    for rank, chunk in enumerate(results, start=1):
        excerpt = " ".join(chunk.content.split())[:160]
        print(f"{rank}. [{chunk.score:.3f}] {chunk.title} ({chunk.source_name})\n   {excerpt}")
    return 0


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(run(args.query, args.category, args.limit)))


if __name__ == "__main__":
    main()

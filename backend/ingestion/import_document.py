"""Import locally supplied, authorised knowledge documents.

    python -m ingestion.import_document --file data/example.json
    python -m ingestion.import_document --file data/example.json --dry-run

The file holds one document object or a JSON list of them. Nothing is fetched over the network
except the Gemini embedding request for new or changed documents.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from app.core.config import get_settings
from app.db.session import dispose_engine, get_sessionmaker
from app.repositories.knowledge import KnowledgeRepository
from app.services.ai.provider import ProviderError
from app.services.knowledge.chunking import Chunker
from app.services.knowledge.embeddings import create_embedding_provider
from app.services.knowledge.ingestion import DocumentLoadError, IngestionService, load_documents


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file", "-f", type=Path, required=True, help="JSON file to import")
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate the file only; touch no services"
    )
    return parser


async def run(path: Path, dry_run: bool) -> int:
    try:
        documents = load_documents(path)
    except DocumentLoadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if dry_run:
        print(f"OK: {len(documents)} valid document(s) in {path}")
        return 0

    settings = get_settings()
    try:
        embedder = create_embedding_provider(settings)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    chunker = Chunker(settings.chunk_size, settings.chunk_overlap)
    failures = 0
    try:
        for document in documents:
            try:
                # One transaction per document: a failure leaves earlier imports intact.
                async with get_sessionmaker()() as session, session.begin():
                    service = IngestionService(KnowledgeRepository(session), embedder, chunker)
                    result = await service.import_document(document)
                print(
                    f"{result.status.value}: {result.title!r} "
                    f"(id={result.document_id}, chunks={result.chunk_count})"
                )
            except (ProviderError, ValueError) as exc:
                failures += 1
                print(f"failed: {document.title!r}: {exc}", file=sys.stderr)
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"failed: {document.title!r}: {type(exc).__name__}", file=sys.stderr)
    finally:
        await dispose_engine()
    return 1 if failures else 0


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(run(args.file, args.dry_run)))


if __name__ == "__main__":
    main()

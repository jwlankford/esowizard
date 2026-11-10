import json
import logging
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from pydantic import ValidationError

from app.schemas.knowledge import ImportDocument
from app.services.ai.provider import EmbeddingProvider
from app.services.knowledge.chunking import Chunk, Chunker
from app.services.knowledge.embeddings import validate_embeddings
from app.services.knowledge.normalizer import NormalizedDocument, normalize_document

logger = logging.getLogger(__name__)


class ImportStatus(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class ImportResult:
    status: ImportStatus
    document_id: int
    title: str
    chunk_count: int


class DocumentLoadError(ValueError):
    """The input file could not be read or did not contain valid documents."""


class IngestionStore(Protocol):
    async def upsert_source(self, document: NormalizedDocument) -> int: ...

    async def get_document_state(self, source_id: int, external_id: str) -> Any: ...

    async def update_document_metadata(
        self, document_id: int, document: NormalizedDocument
    ) -> None: ...

    async def save_document(
        self,
        source_id: int,
        document: NormalizedDocument,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        existing_id: int | None = None,
    ) -> int: ...


# Loader + parser: local, explicitly supplied files only. No network access.
MAX_FILE_BYTES = 5_000_000


def load_documents(path: Path) -> list[ImportDocument]:
    """Load one document object or a list of them from a local JSON file and validate each."""
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            raise DocumentLoadError(f"{path} is larger than {MAX_FILE_BYTES} bytes")
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise DocumentLoadError(f"Cannot read {path}: {exc.strerror}") from exc
    except json.JSONDecodeError as exc:
        raise DocumentLoadError(f"{path} is not valid JSON: {exc}") from exc
    items = payload if isinstance(payload, list) else [payload]
    if not items:
        raise DocumentLoadError(f"{path} contains no documents")
    documents: list[ImportDocument] = []
    for position, item in enumerate(items):
        try:
            documents.append(ImportDocument.model_validate(item))
        except ValidationError as exc:
            problems = "; ".join(
                f"{'.'.join(str(p) for p in error['loc'])}: {error['msg']}"
                for error in exc.errors()
            )
            raise DocumentLoadError(f"Document #{position + 1} is invalid: {problems}") from exc
    return documents


class IngestionService:
    """validate -> normalise -> hash -> (skip | chunk -> embed -> store). Caller commits."""

    def __init__(self, store: IngestionStore, embedder: EmbeddingProvider, chunker: Chunker):
        self.store = store
        self.embedder = embedder
        self.chunker = chunker

    async def import_document(self, document: ImportDocument) -> ImportResult:
        normalized = normalize_document(document)
        source_id = await self.store.upsert_source(normalized)
        state = await self.store.get_document_state(source_id, normalized.external_id)
        if state is not None and state.content_hash == normalized.content_hash:
            await self.store.update_document_metadata(state.id, normalized)
            logger.info("ingestion.unchanged document_id=%s", state.id)
            return ImportResult(ImportStatus.UNCHANGED, state.id, normalized.title, 0)

        chunks = self.chunker.chunk(normalized.title, normalized.category, normalized.content)
        if not chunks:
            raise ValueError("Document produced no chunks")
        started = time.perf_counter()
        embeddings = validate_embeddings(
            await self.embedder.embed_documents([chunk.content for chunk in chunks]),
            len(chunks),
            self.embedder.dimensions,
        )
        document_id = await self.store.save_document(
            source_id, normalized, chunks, embeddings, state.id if state else None
        )
        logger.info(
            "ingestion.stored document_id=%s chunks=%d embed_ms=%d",
            document_id,
            len(chunks),
            (time.perf_counter() - started) * 1000,
        )
        status = ImportStatus.CREATED if state is None else ImportStatus.UPDATED
        return ImportResult(status, document_id, normalized.title, len(chunks))

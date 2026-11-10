from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.categories import ESOCategory
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeSource
from app.schemas.knowledge import RetrievedChunk
from app.services.knowledge.chunking import Chunk
from app.services.knowledge.normalizer import NormalizedDocument


@dataclass(frozen=True)
class DocumentState:
    id: int
    content_hash: str


class KnowledgeRepository:
    """All knowledge-base SQL lives here. Callers own the transaction (commit/rollback)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_source(self, document: NormalizedDocument) -> int:
        source = await self.session.scalar(
            select(KnowledgeSource).where(KnowledgeSource.name == document.source_name)
        )
        if source is None:
            source = KnowledgeSource(
                name=document.source_name,
                base_url=document.source_url,
                source_type=document.source_type.value,
            )
            self.session.add(source)
        elif document.source_url and source.base_url != document.source_url:
            source.base_url = document.source_url
        await self.session.flush()
        return source.id

    async def get_document_state(self, source_id: int, external_id: str) -> DocumentState | None:
        row = (
            await self.session.execute(
                select(KnowledgeDocument.id, KnowledgeDocument.content_hash).where(
                    KnowledgeDocument.source_id == source_id,
                    KnowledgeDocument.external_id == external_id,
                )
            )
        ).first()
        return DocumentState(row.id, row.content_hash) if row else None

    async def update_document_metadata(
        self, document_id: int, document: NormalizedDocument
    ) -> None:
        stored = await self.session.get(KnowledgeDocument, document_id)
        if stored is None:
            return
        if (stored.canonical_url, stored.doc_metadata) != (
            document.canonical_url,
            document.metadata,
        ):
            stored.canonical_url = document.canonical_url
            stored.doc_metadata = document.metadata
            await self.session.flush()

    async def save_document(
        self,
        source_id: int,
        document: NormalizedDocument,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        existing_id: int | None = None,
    ) -> int:
        stored = await self.session.get(KnowledgeDocument, existing_id) if existing_id else None
        if stored is None:
            stored = KnowledgeDocument(source_id=source_id, external_id=document.external_id)
            self.session.add(stored)
        stored.title = document.title
        stored.slug = document.slug
        stored.category = document.category.value
        stored.canonical_url = document.canonical_url
        stored.content = document.content
        stored.content_hash = document.content_hash
        stored.doc_metadata = document.metadata
        stored.indexed_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.document_id == stored.id)
        )
        self.session.add_all(
            KnowledgeChunk(
                document_id=stored.id,
                chunk_index=chunk.index,
                content=chunk.content,
                token_count=chunk.token_count,
                embedding=embedding,
                chunk_metadata={"section": chunk.section, "title": document.title},
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        )
        await self.session.flush()
        return stored.id

    async def search_chunks(
        self, embedding: list[float], category: ESOCategory | None, limit: int
    ) -> list[RetrievedChunk]:
        """Cosine-similarity search. ``score`` is similarity in [-1, 1] (1 - cosine distance)."""
        distance = KnowledgeChunk.embedding.cosine_distance(embedding)
        statement = (
            select(
                KnowledgeChunk.id,
                KnowledgeChunk.document_id,
                KnowledgeChunk.chunk_index,
                KnowledgeChunk.content,
                KnowledgeChunk.chunk_metadata,
                KnowledgeDocument.title,
                KnowledgeDocument.category,
                KnowledgeDocument.canonical_url,
                KnowledgeSource.name.label("source_name"),
                KnowledgeSource.base_url,
                (1 - distance).label("score"),
            )
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .join(KnowledgeSource, KnowledgeSource.id == KnowledgeDocument.source_id)
            .where(KnowledgeSource.is_active.is_(True))
            .order_by(distance)
            .limit(limit)
        )
        if category is not None:
            statement = statement.where(KnowledgeDocument.category == category.value)
        rows = (await self.session.execute(statement)).all()
        return [
            RetrievedChunk(
                chunk_id=row.id,
                document_id=row.document_id,
                chunk_index=row.chunk_index,
                title=row.title,
                category=_to_category(row.category),
                content=row.content,
                score=float(row.score),
                source_name=row.source_name,
                source_url=row.canonical_url or row.base_url,
                section=(row.chunk_metadata or {}).get("section"),
            )
            for row in rows
        ]

    async def check_connection(self) -> bool:
        """Verify connectivity and that the pgvector extension is installed."""
        await self.session.execute(text("SELECT 1"))
        installed = await self.session.scalar(
            text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        )
        return bool(installed)


def _to_category(value: str) -> ESOCategory | str:
    try:
        return ESOCategory(value)
    except ValueError:
        return value

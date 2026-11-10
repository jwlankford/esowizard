"""Requires a disposable, migrated Postgres with pgvector in TEST_DATABASE_URL (any driver form)."""

import os
from uuid import uuid4

import pytest
from fakes import FakeEmbedder
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.categories import ESOCategory
from app.core.config import Settings, get_settings
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import ImportDocument
from app.services.knowledge.chunking import Chunker
from app.services.knowledge.ingestion import ImportStatus, IngestionService
from app.services.knowledge.retrieval import KnowledgeRetrievalService

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set"),
]


async def test_ingest_search_and_update_roundtrip():
    url = Settings(database_url=os.environ["TEST_DATABASE_URL"]).async_database_url
    engine = create_async_engine(url)
    embedder = FakeEmbedder(get_settings().embedding_dimensions)
    source = f"Synthetic Source {uuid4()}"

    def document(content, category="FISHING"):
        return ImportDocument.model_validate(
            {
                "title": "SYNTHETIC Integration Doc",
                "category": category,
                "source": {"name": source, "url": "https://example.com"},
                "content": content,
            }
        )

    try:
        async with async_sessionmaker(engine)() as session:
            repository = KnowledgeRepository(session)
            service = IngestionService(repository, embedder, Chunker(500, 50))
            assert await repository.check_connection()
            created = await service.import_document(document("zorblax quimble frobnicate"))
            assert created.status is ImportStatus.CREATED
            assert (
                await service.import_document(document("zorblax quimble frobnicate"))
            ).status is (ImportStatus.UNCHANGED)
            retrieval = KnowledgeRetrievalService(repository, embedder)
            hits = await retrieval.retrieve("zorblax quimble", ESOCategory.FISHING, 3)
            assert hits and hits[0].title == "SYNTHETIC Integration Doc"
            assert hits[0].source_name == source
            assert not await retrieval.retrieve("zorblax", ESOCategory.CRAFTING, 3)
            updated = await service.import_document(document("plonk grumble sprocket"))
            assert updated.status is ImportStatus.UPDATED
            assert updated.document_id == created.document_id
            await session.rollback()
    finally:
        await engine.dispose()

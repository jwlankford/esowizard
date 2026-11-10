import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.schemas.api import Category
from app.services.ai.provider import AIProvider
from app.services.search.retrieval import RetrievalService


class FakeProvider(AIProvider):
    def generate(self, prompt):
        raise AssertionError("Retrieval must not generate an answer")

    def embed(self, text):
        return [1.0] + [0.0] * 767


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set")
def test_vector_retrieval_and_category_filter():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    try:
        with Session(engine) as session:
            for category, embedding in [
                (Category.ITEMS, [1.0] + [0.0] * 767),
                (Category.FISHING, [0.0, 1.0] + [0.0] * 766),
            ]:
                document = KnowledgeDocument(
                    title=category.value,
                    slug=str(uuid4()),
                    category=category.value,
                    source_name="Test source",
                    source_url="https://example.com",
                    content="Test document",
                )
                document.chunks.append(
                    KnowledgeChunk(content="Test chunk", chunk_number=0, embedding=embedding)
                )
                session.add(document)
            session.flush()
            retrieval = RetrievalService(session, FakeProvider())
            results = retrieval.search("test", None, 1)
            assert results[0].title == "Items"
            results = retrieval.search("test", Category.FISHING, 10)
            assert [result.title for result in results] == ["Fishing"]
            session.rollback()
    finally:
        engine.dispose()

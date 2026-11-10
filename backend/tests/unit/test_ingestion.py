import pytest
from fakes import FakeEmbedder, InMemoryRepository

from app.schemas.knowledge import ImportDocument
from app.services.ai.provider import ProviderError
from app.services.knowledge.chunking import Chunker
from app.services.knowledge.ingestion import ImportStatus, IngestionService


def make_document(content="Synthetic fact alpha.", **overrides) -> ImportDocument:
    data = {
        "title": "SYNTHETIC Doc",
        "category": "CRAFTING",
        "source": {"name": "Synthetic Source", "url": "https://example.com"},
        "content": content,
    }
    return ImportDocument.model_validate({**data, **overrides})


@pytest.fixture
def parts():
    repo, embedder = InMemoryRepository(), FakeEmbedder()
    return repo, embedder, IngestionService(repo, embedder, Chunker(500, 50))


async def test_new_document_is_created_chunked_and_embedded(parts):
    repo, embedder, service = parts
    result = await service.import_document(make_document("# A\n\nOne.\n\n# B\n\nTwo."))
    assert result.status is ImportStatus.CREATED
    assert result.chunk_count == 2
    assert len(embedder.document_calls) == 1 and len(embedder.document_calls[0]) == 2
    stored = next(iter(repo.docs.values()))
    assert [chunk.index for chunk, _ in stored.chunks] == [0, 1]
    assert all(len(vector) == embedder.dimensions for _, vector in stored.chunks)


async def test_unchanged_document_skips_embedding(parts):
    repo, embedder, service = parts
    await service.import_document(make_document())
    again = await service.import_document(make_document("Synthetic fact alpha.\r\n"))
    assert again.status is ImportStatus.UNCHANGED
    assert again.chunk_count == 0
    assert len(embedder.document_calls) == 1
    assert repo.metadata_updates == 1


async def test_changed_document_replaces_chunks(parts):
    repo, embedder, service = parts
    first = await service.import_document(make_document())
    updated = await service.import_document(make_document("Synthetic fact beta."))
    assert updated.status is ImportStatus.UPDATED
    assert updated.document_id == first.document_id
    assert len(embedder.document_calls) == 2
    assert len(repo.docs) == 1
    stored = next(iter(repo.docs.values()))
    assert "beta" in stored.chunks[0][0].content


async def test_same_title_in_different_sources_is_distinct(parts):
    repo, _, service = parts
    await service.import_document(make_document())
    await service.import_document(make_document(source={"name": "Other Synthetic Source"}))
    assert len(repo.docs) == 2


async def test_embedding_dimension_mismatch_is_rejected(parts):
    class BadEmbedder(FakeEmbedder):
        async def embed_documents(self, texts):
            return [[0.0] for _ in texts]

    repo = InMemoryRepository()
    service = IngestionService(repo, BadEmbedder(), Chunker(500, 50))
    with pytest.raises(ProviderError):
        await service.import_document(make_document())
    assert not repo.docs

import math
import re
from dataclasses import dataclass

from app.core.categories import ESOCategory
from app.repositories.knowledge import DocumentState
from app.schemas.knowledge import RetrievedChunk
from app.services.ai.provider import AIProvider, EmbeddingProvider
from app.services.knowledge.chunking import Chunk
from app.services.knowledge.normalizer import NormalizedDocument

DIMENSIONS = 16


class FakeEmbedder(EmbeddingProvider):
    """Deterministic bag-of-words embedder: shared words => higher cosine similarity."""

    def __init__(self, dimensions: int = DIMENSIONS):
        self._dimensions = dimensions
        self.document_calls: list[list[str]] = []
        self.query_calls: list[str] = []

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        for word in re.findall(r"[a-z]+", text.lower()):
            vector[sum(map(ord, word)) % self._dimensions] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    async def embed_query(self, text: str) -> list[float]:
        self.query_calls.append(text)
        return self._vector(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls.append(list(texts))
        return [self._vector(text) for text in texts]


class FakeLLM(AIProvider):
    def __init__(self, answer: str = "Synthetic answer [1]"):
        self.answer = answer
        self.calls: list[tuple[str, str | None]] = []

    async def generate(self, prompt: str, system_instruction: str | None = None) -> str:
        self.calls.append((prompt, system_instruction))
        return self.answer


@dataclass
class StoredDoc:
    id: int
    source_id: int
    document: NormalizedDocument
    chunks: list[tuple[Chunk, list[float]]]


class InMemoryRepository:
    """In-memory stand-in for KnowledgeRepository (ingestion store + vector search)."""

    def __init__(self):
        self.sources: dict[str, int] = {}
        self.docs: dict[tuple[int, str], StoredDoc] = {}
        self.metadata_updates = 0

    async def upsert_source(self, document: NormalizedDocument) -> int:
        return self.sources.setdefault(document.source_name, len(self.sources) + 1)

    async def get_document_state(self, source_id: int, external_id: str):
        stored = self.docs.get((source_id, external_id))
        return DocumentState(stored.id, stored.document.content_hash) if stored else None

    async def update_document_metadata(self, document_id: int, document: NormalizedDocument):
        self.metadata_updates += 1

    async def save_document(self, source_id, document, chunks, embeddings, existing_id=None):
        key = (source_id, document.external_id)
        doc_id = existing_id or len(self.docs) + 1
        self.docs[key] = StoredDoc(doc_id, source_id, document, list(zip(chunks, embeddings)))
        return doc_id

    async def search_chunks(self, embedding, category: ESOCategory | None, limit: int):
        hits: list[RetrievedChunk] = []
        for stored in self.docs.values():
            if category is not None and stored.document.category != category:
                continue
            for chunk, vector in stored.chunks:
                score = sum(a * b for a, b in zip(embedding, vector))
                hits.append(
                    RetrievedChunk(
                        chunk_id=stored.id * 100 + chunk.index,
                        document_id=stored.id,
                        chunk_index=chunk.index,
                        title=stored.document.title,
                        category=stored.document.category,
                        content=chunk.content,
                        score=score,
                        source_name=stored.document.source_name,
                        source_url=stored.document.canonical_url or stored.document.source_url,
                        section=chunk.section,
                    )
                )
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]

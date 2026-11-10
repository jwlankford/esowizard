import logging
import time

from app.core.categories import ESOCategory
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import RetrievedChunk
from app.services.ai.provider import EmbeddingProvider

logger = logging.getLogger(__name__)


class KnowledgeRetrievalService:
    """Embeds a normalised query and ranks stored chunks. Extension point for hybrid/rerank."""

    def __init__(self, repository: KnowledgeRepository, embedder: EmbeddingProvider):
        self.repository = repository
        self.embedder = embedder

    async def retrieve(
        self, query: str, category: ESOCategory | None = None, limit: int = 5
    ) -> list[RetrievedChunk]:
        started = time.perf_counter()
        embedding = await self.embedder.embed_query(query)
        embedded = time.perf_counter()
        results = await self.repository.search_chunks(embedding, category, limit)
        finished = time.perf_counter()
        logger.info(
            "retrieval.complete category=%s results=%d embed_ms=%d search_ms=%d",
            category.value if category else None,
            len(results),
            (embedded - started) * 1000,
            (finished - embedded) * 1000,
        )
        return sorted(results, key=lambda chunk: chunk.score, reverse=True)

import logging
import time

from sqlalchemy.exc import SQLAlchemyError

from app.core.categories import ESOCategory
from app.core.request_context import get_request_id
from app.schemas.api import AskResponse, AskStatus, SourceRef
from app.services.ai.provider import AIProvider, ProviderError
from app.services.knowledge.context import (
    INSUFFICIENT_ANSWER,
    SYSTEM_INSTRUCTION,
    build_context,
    detect_category,
    is_insufficient,
)
from app.services.knowledge.retrieval import KnowledgeRetrievalService

logger = logging.getLogger(__name__)

ERROR_ANSWER = "ESO Wizard could not answer right now. Please try again later."


def normalize_query(text: str) -> str:
    return " ".join(text.split())


class RAGService:
    """question -> retrieval -> threshold -> grounded prompt -> Gemini -> backend-resolved sources."""

    def __init__(
        self,
        retrieval: KnowledgeRetrievalService,
        provider: AIProvider,
        top_k: int,
        min_score: float,
    ):
        self.retrieval = retrieval
        self.provider = provider
        self.top_k = top_k
        self.min_score = min_score

    async def ask(self, question: str, category: ESOCategory | None = None) -> AskResponse:
        started = time.perf_counter()
        question = normalize_query(question)
        if not question:
            raise ValueError("Question cannot be blank")
        effective_category = category or detect_category(question)
        response = AskResponse(
            question=question,
            answer=INSUFFICIENT_ANSWER,
            category=effective_category,
            status=AskStatus.INSUFFICIENT_KNOWLEDGE,
        )
        llm_ms = 0
        chunks: list = []
        try:
            chunks = await self.retrieval.retrieve(question, category, self.top_k)
            relevant = [chunk for chunk in chunks if chunk.score >= self.min_score]
            if relevant:
                context = build_context(relevant)
                llm_started = time.perf_counter()
                answer = await self.provider.generate(context.prompt(question), SYSTEM_INSTRUCTION)
                llm_ms = int((time.perf_counter() - llm_started) * 1000)
                if not is_insufficient(answer):
                    response.status = AskStatus.ANSWERED
                    final_answer, sources = context.resolve(answer.strip())
                    response.answer = final_answer
                    response.sources = [
                        SourceRef(title=s.title, url=s.url, source_name=s.source_name)
                        for s in sources
                    ]
        except (ProviderError, SQLAlchemyError) as exc:
            logger.error("rag.failed error=%s", type(exc).__name__)
            response.status = AskStatus.ERROR
            response.answer = ERROR_ANSWER
            response.sources = []
        logger.info(
            "rag.ask request_id=%s category=%s status=%s retrieved=%d llm_ms=%d total_ms=%d",
            get_request_id(),
            effective_category.value if effective_category else None,
            response.status.value,
            len(chunks),
            llm_ms,
            (time.perf_counter() - started) * 1000,
        )
        return response

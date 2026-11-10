from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.repositories.knowledge import KnowledgeRepository
from app.services.ai.gemini import GeminiProvider
from app.services.ai.provider import AIProvider, EmbeddingProvider
from app.services.knowledge.embeddings import create_embedding_provider
from app.services.knowledge.retrieval import KnowledgeRetrievalService
from app.services.rag import RAGService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_embedding_provider(settings: SettingsDep) -> EmbeddingProvider:
    try:
        return create_embedding_provider(settings)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def get_ai_provider(settings: SettingsDep) -> AIProvider:
    try:
        return GeminiProvider(settings)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def get_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> KnowledgeRepository:
    return KnowledgeRepository(session)


def get_retrieval(
    repository: Annotated[KnowledgeRepository, Depends(get_repository)],
    embedder: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
) -> KnowledgeRetrievalService:
    return KnowledgeRetrievalService(repository, embedder)


def get_rag_service(
    retrieval: Annotated[KnowledgeRetrievalService, Depends(get_retrieval)],
    provider: Annotated[AIProvider, Depends(get_ai_provider)],
    settings: SettingsDep,
) -> RAGService:
    return RAGService(retrieval, provider, settings.rag_top_k, settings.retrieval_min_score)

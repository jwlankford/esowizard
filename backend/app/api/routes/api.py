import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.api.dependencies import SettingsDep, get_rag_service, get_repository, get_retrieval
from app.core.categories import ESOCategory
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.api import (
    AskRequest,
    AskResponse,
    AskStatus,
    CategoryInfo,
    HealthResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.knowledge.retrieval import KnowledgeRetrievalService
from app.services.rag import RAGService, normalize_query

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")


@router.get("/health/database", response_model=HealthResponse)
async def health_database(repository: Annotated[KnowledgeRepository, Depends(get_repository)]):
    try:
        vector_installed = await repository.check_connection()
    except Exception as exc:  # noqa: BLE001
        logger.error("health.database failed error=%s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Database is unavailable") from None
    if not vector_installed:
        raise HTTPException(status_code=503, detail="pgvector extension is not installed")
    return HealthResponse(status="ok", detail="Database reachable; pgvector installed")


@router.get("/health/ai", response_model=HealthResponse)
async def health_ai(settings: SettingsDep):
    """Configuration check only; makes no Gemini request."""
    if not settings.google_api_key:
        raise HTTPException(status_code=503, detail="GOOGLE_API_KEY is not configured")
    return HealthResponse(status="ok", detail="AI configuration present")


@router.get("/categories", response_model=list[CategoryInfo])
async def categories():
    return [CategoryInfo(value=category, label=category.label) for category in ESOCategory]


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    retrieval: Annotated[KnowledgeRetrievalService, Depends(get_retrieval)],
):
    query = normalize_query(request.query)
    if not query:
        raise HTTPException(status_code=422, detail="Query cannot be blank")
    results = await retrieval.retrieve(query, request.category, request.limit)
    return SearchResponse(query=query, results=results)


@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest, service: Annotated[RAGService, Depends(get_rag_service)]):
    if not normalize_query(request.question):
        raise HTTPException(status_code=422, detail="Question cannot be blank")
    response = await service.ask(request.question, request.category)
    if response.status is AskStatus.ERROR:
        return JSONResponse(status_code=502, content=response.model_dump(mode="json"))
    return response

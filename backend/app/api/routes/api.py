from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_ask_service, get_retrieval
from app.schemas.api import AskRequest, AskResponse, Category, SearchRequest, SearchResponse
from app.services.ask import AskService
from app.services.search.retrieval import RetrievalService

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/categories", response_model=list[Category])
def categories():
    return list(Category)


@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest, retrieval: Annotated[RetrievalService, Depends(get_retrieval)]):
    query = " ".join(request.query.split())
    if not query:
        raise HTTPException(status_code=422, detail="Query cannot be blank")
    return SearchResponse(results=retrieval.search(query, request.category, request.limit))


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, service: Annotated[AskService, Depends(get_ask_service)]):
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Question cannot be blank")
    return service.ask(request)

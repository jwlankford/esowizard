from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session
from app.services.ai.gemini import GeminiProvider
from app.services.ai.provider import AIProvider
from app.services.ask import AskService
from app.services.search.retrieval import RetrievalService


def get_provider() -> AIProvider:
    try:
        return GeminiProvider(get_settings())
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def get_retrieval(
    session: Annotated[Session, Depends(get_session)],
    provider: Annotated[AIProvider, Depends(get_provider)],
) -> RetrievalService:
    return RetrievalService(session, provider)


def get_ask_service(
    retrieval: Annotated[RetrievalService, Depends(get_retrieval)],
    provider: Annotated[AIProvider, Depends(get_provider)],
) -> AskService:
    return AskService(retrieval, provider)

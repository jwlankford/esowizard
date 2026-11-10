from enum import StrEnum

from pydantic import BaseModel, Field

from app.core.categories import ESOCategory
from app.schemas.knowledge import RetrievedChunk


class CategoryInfo(BaseModel):
    value: ESOCategory
    label: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    category: ESOCategory | None = None
    limit: int = Field(default=10, ge=1, le=50)


class SearchResponse(BaseModel):
    query: str
    results: list[RetrievedChunk]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    category: ESOCategory | None = None


class AskStatus(StrEnum):
    ANSWERED = "answered"
    INSUFFICIENT_KNOWLEDGE = "insufficient_knowledge"
    ERROR = "error"


class SourceRef(BaseModel):
    title: str
    url: str | None = None
    source_name: str


class AskResponse(BaseModel):
    question: str
    answer: str
    category: ESOCategory | None = None
    status: AskStatus
    sources: list[SourceRef] = Field(default_factory=list)
    related_queries: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    detail: str | None = None

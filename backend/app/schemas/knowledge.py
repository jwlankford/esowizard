import json
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.core.categories import ESOCategory, SourceType

MAX_CONTENT_CHARS = 200_000
MAX_METADATA_CHARS = 20_000


def _http_url(value: HttpUrl) -> str:
    return str(value)


UrlStr = Annotated[HttpUrl, AfterValidator(_http_url)]


class ImportSource(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=500)
    url: UrlStr | None = None
    source_type: SourceType = SourceType.MANUAL


class ImportDocument(BaseModel):
    """The structured format accepted by the manual import pipeline."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=500)
    category: ESOCategory
    source: ImportSource
    content: str = Field(min_length=1, max_length=MAX_CONTENT_CHARS)
    external_id: str | None = Field(default=None, min_length=1, max_length=500)
    canonical_url: UrlStr | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("content")
    @classmethod
    def _content_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content cannot be blank")
        return value

    @field_validator("metadata")
    @classmethod
    def _metadata_bounded(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            encoded = json.dumps(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata must be JSON-serialisable") from exc
        if len(encoded) > MAX_METADATA_CHARS:
            raise ValueError(f"metadata exceeds {MAX_METADATA_CHARS} characters")
        return value


class RetrievedChunk(BaseModel):
    """A search hit. Deliberately independent of the ORM models."""

    chunk_id: int
    document_id: int
    chunk_index: int
    title: str
    category: ESOCategory | str
    content: str
    score: float
    source_name: str
    source_url: str | None = None
    section: str | None = None

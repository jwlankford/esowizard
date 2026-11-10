import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from app.core.categories import ESOCategory, SourceType
from app.schemas.knowledge import ImportDocument


def normalize_text(text: str) -> str:
    """NFC-normalise, unify newlines, trim line-trailing space and collapse blank-line runs."""
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("\x00", "")
    lines = [re.sub(r"[ \t]+", " ", line).rstrip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")[:200] or "document"


def compute_content_hash(title: str, category: str, content: str) -> str:
    """Hash of everything that influences chunk text, and therefore embeddings."""
    payload = "\x1f".join([title, str(category), content]).encode()
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class NormalizedDocument:
    title: str
    slug: str
    external_id: str
    category: ESOCategory
    content: str
    content_hash: str
    source_name: str
    source_url: str | None
    source_type: SourceType
    canonical_url: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


def normalize_document(document: ImportDocument) -> NormalizedDocument:
    title = " ".join(normalize_text(document.title).split())
    content = normalize_text(document.content)
    if not title or not content:
        raise ValueError("title and content cannot be blank after normalisation")
    slug = slugify(title)
    return NormalizedDocument(
        title=title,
        slug=slug,
        external_id=document.external_id or slug,
        category=document.category,
        content=content,
        content_hash=compute_content_hash(title, document.category.value, content),
        source_name=" ".join(document.source.name.split()),
        source_url=document.source.url,
        source_type=document.source.source_type,
        canonical_url=document.canonical_url,
        metadata=document.metadata,
    )

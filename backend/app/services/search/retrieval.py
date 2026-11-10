from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.schemas.api import Category, Source
from app.services.ai.provider import AIProvider


class RetrievalService:
    def __init__(self, session: Session, provider: AIProvider):
        self.session = session
        self.provider = provider

    def search(self, query: str, category: Category | None, limit: int) -> list[Source]:
        embedding = self.provider.embed(query)
        statement = (
            select(KnowledgeChunk, KnowledgeDocument)
            .join(KnowledgeDocument)
            .order_by(KnowledgeChunk.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        if category is not None:
            statement = statement.where(KnowledgeDocument.category == category.value)
        return [
            Source(
                title=document.title,
                source_name=document.source_name,
                source_url=document.source_url,
                chunk_number=chunk.chunk_number,
                content=chunk.content,
            )
            for chunk, document in self.session.execute(statement)
        ]

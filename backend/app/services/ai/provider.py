from abc import ABC, abstractmethod


class ProviderError(RuntimeError):
    """An AI provider call failed. Messages must never contain credentials."""


class AIProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_instruction: str | None = None) -> str:
        raise NotImplementedError


class EmbeddingProvider(ABC):
    """Embeds text for storage (documents) and for search (queries)."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        raise NotImplementedError

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

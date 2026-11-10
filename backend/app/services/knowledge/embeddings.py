from app.core.config import Settings
from app.services.ai.gemini import GeminiEmbeddingProvider
from app.services.ai.provider import EmbeddingProvider, ProviderError


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Factory used by the API and CLIs so provider construction stays in one place."""
    return GeminiEmbeddingProvider(settings)


def validate_embeddings(
    vectors: list[list[float]], expected_count: int, dimensions: int
) -> list[list[float]]:
    if len(vectors) != expected_count or any(len(vector) != dimensions for vector in vectors):
        raise ProviderError(
            f"Expected {expected_count} embeddings of {dimensions} dimensions from the provider"
        )
    return vectors

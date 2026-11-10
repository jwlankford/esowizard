import logging

from google import genai
from google.genai import errors, types

from app.core.config import Settings
from app.services.ai.provider import AIProvider, EmbeddingProvider, ProviderError

logger = logging.getLogger(__name__)


def _make_client(settings: Settings) -> genai.Client:
    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY is not configured")
    return genai.Client(api_key=settings.google_api_key)


class GeminiProvider(AIProvider):
    def __init__(self, settings: Settings):
        self.client = _make_client(settings)
        self.settings = settings

    async def generate(self, prompt: str, system_instruction: str | None = None) -> str:
        try:
            response = await self.client.aio.models.generate_content(
                model=self.settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction, temperature=0.2
                ),
            )
        except errors.APIError as exc:
            logger.warning("Gemini generation failed: HTTP %s", getattr(exc, "code", "?"))
            raise ProviderError("The generation service failed to respond") from None
        return response.text or ""


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, settings: Settings):
        self.client = _make_client(settings)
        self.settings = settings

    @property
    def dimensions(self) -> int:
        return self.settings.embedding_dimensions

    async def embed_query(self, text: str) -> list[float]:
        return (await self._embed([text], "RETRIEVAL_QUERY"))[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        size = self.settings.embedding_batch_size
        for start in range(0, len(texts), size):
            vectors.extend(await self._embed(texts[start : start + size], "RETRIEVAL_DOCUMENT"))
        return vectors

    async def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = await self.client.aio.models.embed_content(
                model=self.settings.gemini_embedding_model,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=task_type, output_dimensionality=self.dimensions
                ),
            )
        except errors.APIError as exc:
            logger.warning("Gemini embedding failed: HTTP %s", getattr(exc, "code", "?"))
            raise ProviderError("The embedding service failed to respond") from None
        vectors = [list(item.values or []) for item in response.embeddings or []]
        if len(vectors) != len(texts) or any(len(v) != self.dimensions for v in vectors):
            raise ProviderError(
                f"Embedding service returned unexpected output (expected {len(texts)} vectors "
                f"of {self.dimensions} dimensions)"
            )
        return vectors

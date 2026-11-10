from google import genai
from google.genai import types

from app.core.config import Settings
from app.models.knowledge import EMBEDDING_DIMENSIONS
from app.services.ai.provider import AIProvider


class GeminiProvider(AIProvider):
    def __init__(self, settings: Settings):
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY is not configured")
        self.client = genai.Client(api_key=settings.google_api_key)
        self.settings = settings

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.settings.gemini_model, contents=prompt
        )
        return response.text or ""

    def embed(self, text: str) -> list[float]:
        response = self.client.models.embed_content(
            model=self.settings.gemini_embedding_model,
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONS),
        )
        if not response.embeddings or not response.embeddings[0].values:
            raise ValueError("Embedding provider returned no embedding")
        return response.embeddings[0].values

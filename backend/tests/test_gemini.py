from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.services.ai.gemini import GeminiProvider


def test_missing_api_key():
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        GeminiProvider(Settings(google_api_key=""))


def test_provider_uses_configured_models_and_dimensions(monkeypatch):
    class Models:
        def generate_content(self, **kwargs):
            assert kwargs == {"model": "generation-model", "contents": "prompt"}
            return SimpleNamespace(text="answer")

        def embed_content(self, **kwargs):
            assert kwargs["model"] == "embedding-model"
            assert kwargs["contents"] == "query"
            assert kwargs["config"].output_dimensionality == 768
            return SimpleNamespace(embeddings=[SimpleNamespace(values=[1.0] * 768)])

    monkeypatch.setattr(
        "app.services.ai.gemini.genai.Client", lambda **kwargs: SimpleNamespace(models=Models())
    )
    settings = Settings(
        google_api_key="test-key",
        gemini_model="generation-model",
        gemini_embedding_model="embedding-model",
    )
    provider = GeminiProvider(settings)
    assert provider.generate("prompt") == "answer"
    assert len(provider.embed("query")) == 768

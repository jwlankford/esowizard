from types import SimpleNamespace

import pytest
from google.genai import errors

from app.core.config import Settings
from app.services.ai.gemini import GeminiEmbeddingProvider, GeminiProvider
from app.services.ai.provider import ProviderError

DIMENSIONS = 6


class Models:
    def __init__(self):
        self.embed_calls = []
        self.fail = False

    async def generate_content(self, **kwargs):
        assert kwargs["model"] == "generation-model"
        assert kwargs["contents"] == "prompt"
        assert kwargs["config"].system_instruction == "system"
        return SimpleNamespace(text="answer")

    async def embed_content(self, **kwargs):
        if self.fail:
            raise errors.APIError(500, {"error": {"message": "secret-key-123 leaked"}})
        self.embed_calls.append(kwargs)
        vectors = [SimpleNamespace(values=[1.0] * DIMENSIONS) for _ in kwargs["contents"]]
        return SimpleNamespace(embeddings=vectors)


@pytest.fixture
def models(monkeypatch):
    models = Models()
    monkeypatch.setattr(
        "app.services.ai.gemini.genai.Client",
        lambda **kwargs: SimpleNamespace(aio=SimpleNamespace(models=models)),
    )
    return models


def settings(**overrides):
    return Settings(
        google_api_key="test-key",
        gemini_model="generation-model",
        gemini_embedding_model="embedding-model",
        embedding_dimensions=DIMENSIONS,
        embedding_batch_size=2,
        **overrides,
    )


def test_missing_api_key():
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        GeminiProvider(Settings(google_api_key=""))
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        GeminiEmbeddingProvider(Settings(google_api_key=""))


async def test_generation(models):
    assert await GeminiProvider(settings()).generate("prompt", "system") == "answer"


async def test_query_and_document_embeddings_use_task_types_and_batches(models):
    provider = GeminiEmbeddingProvider(settings())
    assert provider.dimensions == DIMENSIONS
    assert len(await provider.embed_query("question")) == DIMENSIONS
    query_config = models.embed_calls[-1]["config"]
    assert query_config.task_type == "RETRIEVAL_QUERY"
    assert query_config.output_dimensionality == DIMENSIONS

    vectors = await provider.embed_documents(["a", "b", "c", "d", "e"])
    assert len(vectors) == 5
    assert [len(call["contents"]) for call in models.embed_calls[1:]] == [2, 2, 1]
    assert models.embed_calls[1]["config"].task_type == "RETRIEVAL_DOCUMENT"
    assert models.embed_calls[1]["model"] == "embedding-model"
    assert await provider.embed_documents([]) == []


async def test_wrong_dimensions_raise(models):
    provider = GeminiEmbeddingProvider(settings())
    provider.settings = settings().model_copy(update={"embedding_dimensions": DIMENSIONS + 1})
    with pytest.raises(ProviderError):
        await provider.embed_query("question")


async def test_api_errors_are_wrapped_without_leaking_details(models):
    models.fail = True
    with pytest.raises(ProviderError) as excinfo:
        await GeminiEmbeddingProvider(settings()).embed_query("question")
    assert "secret-key-123" not in str(excinfo.value)

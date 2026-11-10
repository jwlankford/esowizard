from fastapi.testclient import TestClient

from app.api.dependencies import get_provider, get_retrieval
from app.main import app
from app.schemas.api import Category, Source
from app.services.ai.provider import AIProvider


class FakeProvider(AIProvider):
    def __init__(self):
        self.prompts = []

    def embed(self, text):
        return [0.0] * 768

    def generate(self, prompt):
        self.prompts.append(prompt)
        return "Grounded answer [1]"


class FakeRetrieval:
    def __init__(self, results=None):
        self.results = results or []
        self.calls = []

    def search(self, query, category, limit):
        self.calls.append((query, category, limit))
        return self.results


def test_health_and_categories():
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json() == {"status": "ok"}
        categories = client.get("/api/v1/categories").json()
        assert "Fishing" in categories
        assert "Cyrodiil" in categories
        assert len(categories) == 21


def test_search_normalizes_and_validates():
    retrieval = FakeRetrieval()
    app.dependency_overrides[get_retrieval] = lambda: retrieval
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/search",
                json={"query": "  a   question ", "category": "Fishing", "limit": 5},
            )
            assert response.json() == {"results": []}
            assert retrieval.calls == [("a question", Category.FISHING, 5)]
            assert client.post("/api/v1/search", json={"query": "  "}).status_code == 422
            assert (
                client.post("/api/v1/search", json={"query": "a", "limit": 51}).status_code == 422
            )
            assert (
                client.post(
                    "/api/v1/search", json={"query": "a", "category": "invalid"}
                ).status_code
                == 422
            )
    finally:
        app.dependency_overrides.clear()


def test_ask_uses_sources_and_does_not_generate_without_them():
    source = Source(
        title="Title",
        source_name="Source",
        source_url="https://example.com",
        chunk_number=0,
        content="Excerpt",
    )
    retrieval = FakeRetrieval([source])
    provider = FakeProvider()
    app.dependency_overrides[get_retrieval] = lambda: retrieval
    app.dependency_overrides[get_provider] = lambda: provider
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/ask", json={"question": " What  is this? "})
            assert response.status_code == 200
            assert response.json()["answer"] == "Grounded answer [1]"
            assert response.json()["sources"][0]["title"] == "Title"
            assert retrieval.calls == [("What is this?", None, 10)]
            assert "Excerpt" in provider.prompts[0]
            retrieval.results = []
            response = client.post("/api/v1/ask", json={"question": "Unknown"})
            assert response.json() == {"answer": "No relevant knowledge was found.", "sources": []}
            assert len(provider.prompts) == 1
            assert client.post("/api/v1/ask", json={"question": " "}).status_code == 422
    finally:
        app.dependency_overrides.clear()

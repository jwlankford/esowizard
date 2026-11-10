import pytest
from fakes import FakeEmbedder, FakeLLM, InMemoryRepository
from fastapi.testclient import TestClient

from app.api.dependencies import get_ai_provider, get_embedding_provider, get_repository
from app.core.categories import ESOCategory
from app.core.config import Settings, get_settings
from app.main import app
from app.schemas.knowledge import ImportDocument
from app.services.knowledge.chunking import Chunker
from app.services.knowledge.ingestion import IngestionService


@pytest.fixture
def client():
    repo, embedder, llm = InMemoryRepository(), FakeEmbedder(), FakeLLM("Synthetic answer [1]")

    async def seed():
        await IngestionService(repo, embedder, Chunker(500, 50)).import_document(
            ImportDocument.model_validate(
                {
                    "title": "SYNTHETIC Fishing Note",
                    "category": "FISHING",
                    "source": {"name": "Synthetic Source", "url": "https://example.com"},
                    "canonical_url": "https://example.com/fishing",
                    "content": "zorblax quimble frobnicate wibble",
                }
            )
        )

    import asyncio

    asyncio.run(seed())
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_embedding_provider] = lambda: embedder
    app.dependency_overrides[get_ai_provider] = lambda: llm
    app.dependency_overrides[get_settings] = lambda: Settings(
        google_api_key="x", retrieval_min_score=0.5
    )
    with TestClient(app) as test_client:
        test_client.llm = llm
        yield test_client
    app.dependency_overrides.clear()


def test_health_and_categories(client):
    response = client.get("/api/v1/health")
    assert response.json() == {"status": "ok", "detail": None}
    assert response.headers["x-request-id"]
    categories = client.get("/api/v1/categories").json()
    assert len(categories) == len(ESOCategory)
    assert {"value": "PVP", "label": "PvP"} in categories


def test_request_id_is_echoed_when_safe(client):
    assert (
        client.get("/api/v1/health", headers={"X-Request-ID": "abc-123"}).headers["x-request-id"]
        == "abc-123"
    )
    assert (
        client.get("/api/v1/health", headers={"X-Request-ID": "bad id!"}).headers["x-request-id"]
        != "bad id!"
    )


def test_health_ai_checks_configuration_only(client):
    assert client.get("/api/v1/health/ai").status_code == 200
    app.dependency_overrides[get_settings] = lambda: Settings(google_api_key="")
    assert client.get("/api/v1/health/ai").status_code == 503


def test_health_database(client):
    class Repo:
        def __init__(self, result):
            self.result = result

        async def check_connection(self):
            if isinstance(self.result, Exception):
                raise self.result
            return self.result

    app.dependency_overrides[get_repository] = lambda: Repo(True)
    assert client.get("/api/v1/health/database").status_code == 200
    app.dependency_overrides[get_repository] = lambda: Repo(False)
    assert client.get("/api/v1/health/database").status_code == 503
    app.dependency_overrides[get_repository] = lambda: Repo(RuntimeError("password=hunter2"))
    response = client.get("/api/v1/health/database")
    assert response.status_code == 503 and "hunter2" not in response.text


def test_search_returns_typed_results_without_generation(client):
    response = client.post(
        "/api/v1/search", json={"query": "  zorblax   quimble ", "category": "FISHING", "limit": 3}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "zorblax quimble"
    result = body["results"][0]
    assert result["title"] == "SYNTHETIC Fishing Note"
    assert result["source_name"] == "Synthetic Source"
    assert result["source_url"] == "https://example.com/fishing"
    assert result["category"] == "FISHING"
    assert 0 < result["score"] <= 1
    assert client.llm.calls == []


@pytest.mark.parametrize(
    "payload",
    [{"query": "  "}, {"query": "a", "limit": 51}, {"query": "a", "category": "Fishing"}, {}],
)
def test_search_validation(client, payload):
    assert client.post("/api/v1/search", json=payload).status_code == 422


def test_ask_answered_with_sources(client):
    response = client.post("/api/v1/ask", json={"question": " zorblax  quimble frobnicate? "})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["question"] == "zorblax quimble frobnicate?"
    assert body["answer"] == "Synthetic answer [1]"
    assert body["sources"] == [
        {
            "title": "SYNTHETIC Fishing Note",
            "url": "https://example.com/fishing",
            "source_name": "Synthetic Source",
        }
    ]
    assert body["related_queries"] == []


def test_ask_insufficient_knowledge(client):
    response = client.post("/api/v1/ask", json={"question": "qqqq yyyy vvvv"})
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "insufficient_knowledge"
    assert body["sources"] == []
    assert client.llm.calls == []


def test_ask_validation(client):
    assert client.post("/api/v1/ask", json={"question": "  "}).status_code == 422
    assert client.post("/api/v1/ask", json={"question": "x" * 2001}).status_code == 422
    assert client.post("/api/v1/ask", json={"question": "a", "category": "bad"}).status_code == 422


def test_missing_api_key_is_a_503_without_secrets():
    app.dependency_overrides[get_settings] = lambda: Settings(google_api_key="")
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/ask", json={"question": "hello"})
            assert response.status_code == 503
            assert "GOOGLE_API_KEY" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()

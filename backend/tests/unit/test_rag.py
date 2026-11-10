import pytest
from fakes import FakeEmbedder, FakeLLM, InMemoryRepository

from app.core.categories import ESOCategory
from app.schemas.api import AskStatus
from app.schemas.knowledge import ImportDocument, RetrievedChunk
from app.services.ai.provider import AIProvider, ProviderError
from app.services.knowledge.chunking import Chunker
from app.services.knowledge.context import (
    INSUFFICIENT_ANSWER,
    INSUFFICIENT_MARKER,
    SYSTEM_INSTRUCTION,
    build_context,
    detect_category,
)
from app.services.knowledge.ingestion import IngestionService
from app.services.knowledge.retrieval import KnowledgeRetrievalService
from app.services.rag import RAGService


def chunk(number, document_id=1, title="Doc", url="https://example.com/doc", score=0.9):
    return RetrievedChunk(
        chunk_id=number,
        document_id=document_id,
        chunk_index=number,
        title=title,
        category=ESOCategory.ITEM,
        content=f"Synthetic excerpt {number}",
        score=score,
        source_name="Synthetic Source",
        source_url=url,
    )


@pytest.fixture
async def knowledge():
    repo, embedder = InMemoryRepository(), FakeEmbedder()
    service = IngestionService(repo, embedder, Chunker(500, 50))
    for title, category, content in [
        ("SYNTHETIC Fishing Note", "FISHING", "zorblax quimble frobnicate wibble"),
        ("SYNTHETIC Crafting Note", "CRAFTING", "plonk grumble sprocket thwang"),
    ]:
        await service.import_document(
            ImportDocument.model_validate(
                {
                    "title": title,
                    "category": category,
                    "source": {"name": "Synthetic Source"},
                    "canonical_url": f"https://example.com/{category.lower()}",
                    "content": content,
                }
            )
        )
    return repo, embedder


async def test_retrieval_ranks_filters_and_returns_typed_results(knowledge):
    repo, embedder = knowledge
    retrieval = KnowledgeRetrievalService(repo, embedder)
    results = await retrieval.retrieve("zorblax quimble", None, 5)
    assert results[0].title == "SYNTHETIC Fishing Note"
    assert results[0].score > results[1].score
    assert results[0].source_url == "https://example.com/fishing"
    assert embedder.query_calls == ["zorblax quimble"]
    filtered = await retrieval.retrieve("zorblax quimble", ESOCategory.CRAFTING, 5)
    assert [r.title for r in filtered] == ["SYNTHETIC Crafting Note"]
    assert len(await retrieval.retrieve("zorblax", None, 1)) == 1


def make_rag(repo, embedder, llm, min_score=0.5):
    return RAGService(KnowledgeRetrievalService(repo, embedder), llm, 5, min_score)


async def test_grounded_answer_with_backend_resolved_sources(knowledge):
    repo, embedder = knowledge
    llm = FakeLLM("The synthetic fact. [1]")
    response = await make_rag(repo, embedder, llm).ask("zorblax quimble frobnicate wibble")
    assert response.status is AskStatus.ANSWERED
    assert response.answer == "The synthetic fact. [1]"
    assert [s.title for s in response.sources] == ["SYNTHETIC Fishing Note"]
    assert response.sources[0].url == "https://example.com/fishing"
    prompt, system = llm.calls[0]
    assert "zorblax" in prompt
    assert "plonk" not in prompt  # below-threshold chunk is not sent to the model
    assert system == SYSTEM_INSTRUCTION


async def test_insufficient_retrieval_never_calls_the_model(knowledge):
    repo, embedder = knowledge
    llm = FakeLLM()
    response = await make_rag(repo, embedder, llm).ask("qqqq yyyy vvvv")
    assert response.status is AskStatus.INSUFFICIENT_KNOWLEDGE
    assert response.answer == INSUFFICIENT_ANSWER
    assert response.sources == []
    assert llm.calls == []


async def test_empty_knowledge_base_is_insufficient():
    llm = FakeLLM()
    response = await make_rag(InMemoryRepository(), FakeEmbedder(), llm).ask("anything")
    assert response.status is AskStatus.INSUFFICIENT_KNOWLEDGE
    assert llm.calls == []


async def test_model_declining_maps_to_insufficient_without_sources(knowledge):
    repo, embedder = knowledge
    llm = FakeLLM(INSUFFICIENT_MARKER)
    response = await make_rag(repo, embedder, llm).ask("zorblax quimble")
    assert response.status is AskStatus.INSUFFICIENT_KNOWLEDGE
    assert response.answer == INSUFFICIENT_ANSWER
    assert response.sources == []


async def test_provider_failures_become_error_status(knowledge):
    repo, embedder = knowledge

    class FailingLLM(AIProvider):
        async def generate(self, prompt, system_instruction=None):
            raise ProviderError("down")

    response = await make_rag(repo, embedder, FailingLLM()).ask("zorblax quimble")
    assert response.status is AskStatus.ERROR
    assert response.sources == []


def test_context_prompt_and_citation_mapping():
    context = build_context(
        [chunk(1, 1, "A", "https://a"), chunk(2, 1, "A"), chunk(3, 2, "B", None)]
    )
    prompt = context.prompt("Q?")
    assert "Question: Q?" in prompt and "[3] (document: B" in prompt
    assert context.cited_numbers("x [2] and [1, 3] [9] [2]") == [2, 1, 3]
    sources = context.sources_for("Answer [1][2]")
    assert [(s.document_id, s.title) for s in sources] == [(1, "A")]  # deduplicated
    assert [s.document_id for s in context.sources_for("a [3] b [1]")] == [2, 1]


def test_sources_ignore_model_invented_urls_and_fall_back_to_context():
    context = build_context([chunk(1, 1, "A", "https://real.example/a")])
    sources = context.sources_for("See https://evil.example/fake for details")
    assert [s.url for s in sources] == ["https://real.example/a"]
    assert [s.url for s in context.sources_for("Out of range [7]")] == ["https://real.example/a"]


def test_system_instruction_requires_grounding():
    assert "ONLY" in SYSTEM_INSTRUCTION
    assert INSUFFICIENT_MARKER in SYSTEM_INSTRUCTION
    assert "Never write URLs" in SYSTEM_INSTRUCTION


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Where do I get Perfect Roe?", ESOCategory.FISHING),
        ("What addons show dungeon bosses?", ESOCategory.ADDON),
        ("How do I get to Cyrodiil?", ESOCategory.CYRODIIL),
        ("something unrelated", None),
    ],
)
def test_category_detection(question, expected):
    assert detect_category(question) is expected

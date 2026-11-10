from app.schemas.api import AskRequest, AskResponse
from app.services.ai.prompt import grounded_prompt
from app.services.ai.provider import AIProvider
from app.services.search.retrieval import RetrievalService


class AskService:
    def __init__(self, retrieval: RetrievalService, provider: AIProvider):
        self.retrieval = retrieval
        self.provider = provider

    def ask(self, request: AskRequest) -> AskResponse:
        question = " ".join(request.question.split())
        sources = self.retrieval.search(question, request.category, 10)
        if not sources:
            return AskResponse(answer="No relevant knowledge was found.", sources=[])
        answer = self.provider.generate(grounded_prompt(question, sources))
        return AskResponse(answer=answer, sources=sources)

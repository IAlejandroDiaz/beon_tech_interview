"""RAG question-answering service (FastAPI, async).

Exposes POST /ask: receives a question, retrieves the most relevant snippets
from the knowledge base via a local vector DB, and asks a local LLM (vLLM) to
answer using ONLY those snippets. Returns a structured JSON response.

Pipeline (bonus RAG, full):
    question
      -> embed question                     (vector_store)
      -> retrieve top-k relevant snippets    (vector_store / ChromaDB)
      -> build grounded, anti-hallucination prompt  (prompt)
      -> LLM chat completion                 (llm / vLLM, OpenAI-compatible)
      -> { question, answer, sources, model }

The core task ("send the KB as context") is just this pipeline with k = full
corpus; RAG generalizes it by sending only what's relevant.

Run:  uv run uvicorn src.rag.main:app --port 8001 --reload
      (port 8001 to avoid clashing with vLLM on 8000)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator

from .llm import LLMClient
from .prompt import build_messages
from .vector_store import VectorStore

# Built once at startup (the embedding model + index load is not free) and
# reused across requests. Populated in the lifespan handler below.
_state: dict = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Load the embedding model + build the vector index once, before serving.
    _state["store"] = VectorStore()
    _state["llm"] = LLMClient()
    yield
    _state.clear()


app = FastAPI(title="beon-rag-service", version="0.1.0", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(..., description="The user's question.")
    # How many snippets to retrieve. Defaults to 2; capped by the store to the
    # corpus size. Exposed so the retrieval breadth is tunable per request.
    top_k: int = Field(default=2, ge=1, le=10)

    @field_validator("question")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if v.strip() == "":
            raise ValueError("`question` must be a non-empty string.")
        return v


class Source(BaseModel):
    text: str
    score: float


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[Source]
    model: str
    timestamp: str


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "rag", "timestamp": _now()}


@app.post("/ask", response_model=AskResponse)
async def ask(body: AskRequest) -> AskResponse:
    store: VectorStore = _state["store"]
    llm: LLMClient = _state["llm"]

    # 1. Retrieve only the snippets relevant to this question (the RAG step).
    retrieved = store.retrieve(body.question, k=body.top_k)
    context = [item["text"] for item in retrieved]

    # 2. Build a grounded prompt and 3. ask the LLM.
    messages = build_messages(body.question, context)
    answer = await llm.complete(messages)

    # 4. Return a structured response that exposes the retrieved sources, so a
    #    reviewer can see exactly what grounded the answer.
    return AskResponse(
        question=body.question,
        answer=answer,
        sources=[Source(**item) for item in retrieved],
        model=llm.model,
        timestamp=_now(),
    )

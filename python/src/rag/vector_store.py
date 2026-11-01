"""Vector store for the RAG retrieval step.

Wraps ChromaDB (in-memory) + a local sentence-transformers embedding model.
Both run locally with no API key — the embedding model is downloaded once and
cached by Hugging Face.

Responsibilities:
  - Embed each knowledge-base snippet and index it in Chroma on startup.
  - Given a question, embed it and return the top-k most similar snippets.

Why in-memory: the corpus is three snippets, so persistence buys us nothing and
an ephemeral client keeps the demo reproducible (fresh index every boot). Swap
`EphemeralClient` for `PersistentClient(path=...)` to persist.

Why MiniLM (`all-MiniLM-L6-v2`): small (~80MB), fast on CPU, and a strong
baseline for short-text semantic similarity — the right tradeoff for a live demo.
"""

from __future__ import annotations

import chromadb
from sentence_transformers import SentenceTransformer

from .knowledge_base import KNOWLEDGE_BASE

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "beon_knowledge_base"


class VectorStore:
    """Encapsulates embedding + retrieval so the API layer stays thin."""

    def __init__(self, snippets: list[str] | None = None) -> None:
        self._snippets = snippets if snippets is not None else KNOWLEDGE_BASE
        # Load the embedding model once; reused for both indexing and queries so
        # question and document vectors live in the same space.
        self._model = SentenceTransformer(EMBEDDING_MODEL)
        # Cosine space matches normalized sentence-transformer embeddings.
        self._client = chromadb.EphemeralClient()
        self._collection = self._client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._index()

    def _embed(self, texts: list[str]) -> list[list[float]]:
        # `normalize_embeddings=True` makes cosine distance well-behaved.
        return self._model.encode(
            texts, normalize_embeddings=True
        ).tolist()

    def _index(self) -> None:
        """Embed and store every knowledge-base snippet. Runs once at startup."""
        embeddings = self._embed(self._snippets)
        self._collection.add(
            ids=[f"snippet-{i}" for i in range(len(self._snippets))],
            documents=self._snippets,
            embeddings=embeddings,
        )

    def retrieve(self, question: str, k: int = 2) -> list[dict]:
        """Return the top-k snippets most relevant to `question`.

        Each result carries its text and a similarity score (1 - cosine
        distance) so the caller can expose *why* a snippet was chosen.
        """
        k = min(k, len(self._snippets))
        query_embedding = self._embed([question])
        result = self._collection.query(
            query_embeddings=query_embedding,
            n_results=k,
        )
        documents = result["documents"][0]
        distances = result["distances"][0]
        return [
            {"text": doc, "score": round(1.0 - dist, 4)}
            for doc, dist in zip(documents, distances)
        ]

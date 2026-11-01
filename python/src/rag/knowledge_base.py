"""The knowledge base: the single source of truth for the LLM's answers.

Kept as a plain list of strings so it's trivial to read, extend, or swap for a
real document loader later. Each entry is one retrievable snippet — the unit we
embed and retrieve in the RAG pipeline (see `vector_store.py`).
"""

KNOWLEDGE_BASE: list[str] = [
    "BEON.tech mission is to place the brightest tech talent in the most "
    "disruptive and innovative U.S. companies.",
    "BEON.tech offer IT staff augmentation services for every modern tech "
    "need, from backend and frontend to AI, machine learning, DevOps and QA.",
    "At BEON.tech, building software means far more than just filling roles — "
    "it's about creating strong relationships, empowering careers and helping "
    "people grow.",
]

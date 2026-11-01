"""Prompt engineering — the anti-hallucination layer.

The exercise is explicit that the model must stay grounded in the provided
context and not invent facts. We enforce that in two places:

  1. A strict system prompt that defines the model's role and hard rules.
  2. A user prompt that fences the retrieved context and the question so the
     model can clearly tell instruction from data.

Keeping prompt construction in one module makes the strategy easy to read,
test, and iterate on in isolation from transport/LLM concerns.
"""

from __future__ import annotations

SYSTEM_PROMPT = (
    "You are BEON.tech's assistant. Answer the user's question using ONLY the "
    "context provided below. Follow these rules strictly:\n"
    "1. Base every statement on the context. Do not use outside knowledge.\n"
    "2. If the context does not contain the answer, reply exactly: "
    '"I don\'t have enough information to answer that."\n'
    "3. Be concise — one to three sentences. No preamble, no repetition of the "
    "question.\n"
    "4. Do not invent facts, figures, names, or URLs that are not in the context."
)


def build_messages(question: str, context_snippets: list[str]) -> list[dict]:
    """Assemble the chat messages sent to the LLM.

    Context snippets are numbered and clearly delimited so the model treats
    them as reference data rather than instructions to follow.
    """
    context_block = "\n".join(
        f"[{i + 1}] {snippet}" for i, snippet in enumerate(context_snippets)
    )
    user_prompt = (
        f"Context:\n{context_block}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the context above."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

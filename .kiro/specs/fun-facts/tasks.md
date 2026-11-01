# Implementation Plan — Fun Facts

## Overview

This plan implements the `GET /fun-fact` endpoint on the existing RAG service.
Work proceeds bottom-up: first the small `VectorStore` and prompt additions,
then the response model and handler that compose them, then tests and
integration verification. Each task builds only on earlier ones and leaves the
existing `/ask` behavior intact.

## Task Dependency Graph

Tasks 1-4 are independent foundations; task 5 composes them; 6 and 7 verify; 8
is the final end-to-end check.

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1", "2", "3", "4"] },
    { "wave": 2, "tasks": ["5"] },
    { "wave": 3, "tasks": ["6", "7"] },
    { "wave": 4, "tasks": ["8"] }
  ]
}
```

## Tasks

- [ ] 1. Extend VectorStore with random sampling and a size accessor
  - Add `sample(self, k: int = 1) -> list[dict]` to `python/src/rag/vector_store.py` using `random.sample` over the in-memory snippets, capped at the corpus size, returning the `retrieve` dict shape with `score` set to `None`.
  - Add a `size` property returning the number of indexed snippets for the empty-KB guard.
  - Import `random` at module top; keep the existing `retrieve` behavior untouched.
  - _Requirements: 2.2, 4.1, 5.2_

- [ ] 2. Add the fun-fact prompt builder
  - Add `build_fun_fact_messages(context_snippets: list[str]) -> list[dict]` to `python/src/rag/prompt.py` with a dedicated system prompt: exactly one fun fact, grounded only in context, at most two sentences, light tone, no verbatim restatement, invent nothing.
  - Reuse the numbered, fenced context-block style from `build_messages` so instruction and data stay separable.
  - _Requirements: 1.2, 1.3, 4.3_

- [ ] 3. Widen the shared Source model to allow unranked sources
  - Change `Source.score` in `python/src/rag/main.py` from `float` to `float | None` so random-mode sources can report `None`.
  - Confirm the `/ask` path still always populates a real score (behavior unchanged).
  - _Requirements: 3.1_

- [ ] 4. Add the FunFactResponse model
  - Define `FunFactResponse` in `python/src/rag/main.py` with fields `fact: str`, `sources: list[Source]`, `topic: str | None`, `model: str`, `timestamp: str`.
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 5. Implement the GET /fun-fact handler
  - Add `async def fun_fact(topic: str | None = None)` with `response_model=FunFactResponse`.
  - Normalize `topic`: strip and map empty/whitespace to `None`.
  - Guard empty KB via `store.size == 0` -> raise HTTP 503 with a descriptive JSON `error`.
  - Select context: topic present -> `store.retrieve(topic, k=2)`; absent -> `store.sample(k=1)`.
  - Build messages via `build_fun_fact_messages` and call `llm.complete`.
  - Guard empty/unusable LLM output -> raise HTTP 502 with a descriptive JSON `error`.
  - Assemble and return `FunFactResponse` with echoed `topic` (or `null`), `sources`, `llm.model`, and `_now()` timestamp.
  - _Requirements: 1.1, 1.4, 2.1, 2.3, 3.2, 4.1, 4.2, 5.1, 5.2, 5.3_

- [ ] 6. Write unit tests for the handler and VectorStore additions
  - Add tests in `python/src/rag/` (e.g. `test_fun_facts.py`) using pytest + httpx `ASGITransport`, with `LLMClient.complete` and the `VectorStore` mocked/faked so no servers or model loads are needed.
  - Cases: (a) no topic -> 200, `topic` null, `sample` used, non-empty `fact`, valid shape; (b) `?topic=AI` -> 200, `topic` echoed, `retrieve` used, scored sources; (c) whitespace topic -> random path, `topic` null; (d) empty LLM output -> 502; (e) empty KB -> 503.
  - Add a focused unit test for `VectorStore.sample` (returns `k` items, `score` is `None`, respects corpus cap) and `size`.
  - Run `uv run pytest` and confirm green.
  - _Requirements: 1.1, 1.4, 2.1, 2.2, 2.3, 3.1, 5.1, 5.2_

- [ ] 7. Add a Bruno integration request
  - Create `bruno/Fun Fact.bru` (next seq) mirroring the existing style: `GET {{ragUrl}}/fun-fact?topic=AI`, asserts 200, non-empty `fact`, `model` defined, and a populated `sources` array.
  - Verify against the live service: start the RAG server on 8001 (vLLM on 8000 must be up), run `npx @usebruno/cli run "Fun Fact.bru" --env Local`, confirm pass, then stop the server.
  - _Requirements: 1.1, 3.1_

- [ ] 8. End-to-end verification
  - Start the RAG server; manually hit `/fun-fact` (no topic) and `/fun-fact?topic=careers` with curl; confirm grounded, concise facts and correct response shape in both modes.
  - Run `uv run pytest` once more; clean up any temporary files and stop the server.
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 3.1_

## Notes

- No new dependencies: the feature reuses `chromadb`, `sentence-transformers`,
  and `openai` already in `pyproject.toml`.
- The only change touching `/ask` is widening `Source.score` to `float | None`
  (Task 3); `/ask` continues to emit real scores, so its behavior is unchanged.
- Tests must not require running servers or model downloads — mock `LLMClient`
  and the `VectorStore`, consistent with the existing two-layer testing model.
- Running `/fun-fact` live needs both the RAG server (8001) and vLLM (8000) up.

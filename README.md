# BEON.tech — AI Engineer Coding Exercise

A small polyglot backend built for a live-coding technical interview focused on
AI. It pairs a Node.js (TypeScript) stack and a Python (FastAPI) stack, and on
top of the Python side implements the exercise itself: a **Retrieval-Augmented
Generation (RAG)** question-answering service grounded in a BEON.tech knowledge
base and backed by a local LLM served via **vLLM**.

## The exercise

Build an HTTP service that receives a user's question and returns an
LLM-generated answer, using a provided knowledge base as context. The bonus is
to upgrade it to a full RAG system: embed each knowledge-base snippet, store the
embeddings in a local vector database, embed the incoming question, retrieve the
most relevant snippets, and pass only those to the LLM.

Both the core task and the bonus are implemented in the RAG service below.

## Repository layout

```
.
├── src/                      # Node.js (TypeScript) stack — Express + GraphQL
│   ├── express/server.ts     #   Express 5: GET /health, POST /echo
│   ├── express/server.test.ts
│   ├── graphql/server.ts     #   Apollo Server: health query, echo mutation
│   └── graphql/server.test.ts
├── python/                   # Python stack (uv-managed, Python 3.13)
│   └── src/
│       ├── rest/main.py      #   FastAPI: GET /health, POST /echo (the seed)
│       └── rag/              #   the AI exercise — full RAG service
│           ├── main.py       #     FastAPI: GET /health, POST /ask
│           ├── knowledge_base.py
│           ├── vector_store.py  # ChromaDB + sentence-transformers embeddings
│           ├── llm.py        #     OpenAI client pointed at local vLLM
│           └── prompt.py     #     grounded, anti-hallucination prompt
├── bruno/                    # Bruno HTTP collection (integration/smoke layer)
├── .kiro/
│   ├── steering/             # project context for the AI assistant
│   └── specs/fun-facts/      # example spec (requirements/design/tasks) — not implemented
├── package.json              # Node scripts + deps
└── .nvmrc                    # Node pinned to 26.13.0
```

## Ports at a glance

| Service              | Port | Notes                                  |
|----------------------|------|----------------------------------------|
| Express REST         | 3000 | `/health`, `/echo`                     |
| GraphQL (Apollo)     | 4000 | health query, echo mutation            |
| FastAPI REST (seed)  | 8000 | `/health`, `/echo`                     |
| vLLM (OpenAI API)    | 8000 | serves the chat model; see note below  |
| RAG service          | 8001 | `/health`, `/ask`                      |

> Note: the FastAPI seed and vLLM both default to 8000. During the AI exercise,
> vLLM owns 8000 (the model server) and the RAG service runs on 8001.

---

## RAG service (the AI exercise)

A FastAPI service that answers questions about BEON.tech using only a small
knowledge base, grounded through a full RAG pipeline.

### How it works

```
question
  -> embed the question                          (sentence-transformers MiniLM)
  -> retrieve top-k relevant snippets            (ChromaDB, cosine similarity)
  -> build a grounded, anti-hallucination prompt (prompt.py)
  -> LLM chat completion                         (vLLM, OpenAI-compatible API)
  -> { question, answer, sources, model, timestamp }
```

- **LLM**: a local model served by **vLLM** behind its OpenAI-compatible API
  (`/v1/chat/completions`). The service talks to it with the official `openai`
  client — no API key required (vLLM ignores it). Base URL and model are
  configurable via `LLM_BASE_URL` and `LLM_MODEL`.
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`, downloaded once and
  cached locally. Small, fast on CPU, no API key.
- **Vector store**: **ChromaDB** (in-memory, cosine space). The three
  knowledge-base snippets are embedded and indexed at startup; the question is
  embedded at request time and the top-k most similar snippets are retrieved.
- **Prompt engineering**: a strict system prompt instructs the model to answer
  only from the provided context, to reply with a fixed "I don't have enough
  information" line when the context doesn't cover the question, and to stay
  concise. Combined with a low temperature, this is the anti-hallucination guard.
- **Structured output**: the response exposes the retrieved `sources` and their
  similarity `score`, so the grounding behind each answer is observable.

### Design notes

- **Retrieval and generation are decoupled.** The embedding model is independent
  from the LLM; each layer (knowledge base, vector store, prompt, LLM client) is
  its own module, so swapping the model, the vector DB, or expanding the corpus
  is a one-file change.
- **The core task is RAG with `k = full corpus`.** The bonus generalizes it by
  sending only the relevant snippets instead of the whole knowledge base.

### Run it

Prerequisites: a vLLM server running on `http://127.0.0.1:8000/v1` serving a
chat model. Confirm with:

```bash
curl -s http://127.0.0.1:8000/v1/models
```

Then start the RAG service (from `python/`):

```bash
uv run uvicorn src.rag.main:app --port 8001 --reload
```

> First boot downloads the ~90MB MiniLM embedding model once, then caches it.

### Endpoints

`GET /health`

```json
{ "status": "ok", "service": "rag", "timestamp": "..." }
```

`POST /ask`

```bash
curl -s http://127.0.0.1:8001/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What services does BEON.tech offer?", "top_k": 2}'
```

```json
{
  "question": "What services does BEON.tech offer?",
  "answer": "BEON.tech offers IT staff augmentation services ...",
  "sources": [
    { "text": "BEON.tech offer IT staff augmentation services ...", "score": 0.7873 },
    { "text": "BEON.tech mission is to place the brightest tech talent ...", "score": 0.6158 }
  ],
  "model": "mlx-community/Qwen3-4B-Instruct-2507-4bit",
  "timestamp": "..."
}
```

Off-topic questions are refused rather than answered from outside knowledge:

```bash
curl -s http://127.0.0.1:8001/ask -H "Content-Type: application/json" \
  -d '{"question": "What is the capital of France?"}'
# -> answer: "I don't have enough information to answer that."
```

### Configuration

| Env var        | Default                                       | Purpose                     |
|----------------|-----------------------------------------------|-----------------------------|
| `LLM_BASE_URL` | `http://127.0.0.1:8000/v1`                    | vLLM OpenAI-compatible URL  |
| `LLM_MODEL`    | `mlx-community/Qwen3-4B-Instruct-2507-4bit`   | model id to request         |
| `LLM_API_KEY`  | `not-needed`                                  | vLLM ignores it             |

---

## Node.js stack (TypeScript)

Express REST and a GraphQL (Apollo) server, mirroring the same `health` + `echo`
contract. ESM, Node pinned to `26.13.0` via `.nvmrc`; run via `tsx`.

```bash
npm install

npm run dev:express     # Express watch mode (port 3000)
npm run dev:graphql     # GraphQL watch mode (port 4000)
npm run start:express   # Express, no watch
npm run start:graphql   # GraphQL, no watch

npm run typecheck       # tsc (no emit, typecheck only)
npm test                # node:test runner via tsx — no servers needed
```

Tests import the app/schema directly (server startup is guarded by
`import.meta.main`), so unit tests run in-process without opening a port.

---

## Python stack (FastAPI, uv)

Managed by [uv](https://docs.astral.sh/uv/); Python pinned to `3.13`.

```bash
cd python
uv sync                                       # install deps

uv run fastapi dev src/rest/main.py           # seed REST server, reload (8000)
uv run uvicorn src.rag.main:app --port 8001   # RAG service (8001)
uv run pytest                                 # async unit tests, no server needed
```

Everything is async; validation uses Pydantic models (invalid bodies yield
FastAPI's 422 automatically). Tests use `pytest-asyncio` + httpx `ASGITransport`
to hit the app in-process.

---

## Bruno collection (integration/smoke tests)

The `bruno/` directory holds a Bruno HTTP collection covering every service
(Express, GraphQL, FastAPI, and the RAG `/ask` endpoint). This is the
integration layer — servers must be **up** — complementing the in-process unit
tests.

```bash
cd bruno
npx @usebruno/cli run --env Local                  # run the whole collection
npx @usebruno/cli run "RAG Ask.bru" --env Local    # a single request
```

Environment variables (`bruno/environments/Local.bru`):

| Variable     | Value                    |
|--------------|--------------------------|
| `expressUrl` | `http://localhost:3000`  |
| `graphqlUrl` | `http://localhost:4000`  |
| `fastapiUrl` | `http://127.0.0.1:8000`  |
| `ragUrl`     | `http://127.0.0.1:8001`  |

---

## Specs

`.kiro/specs/fun-facts/` contains a worked example of spec-driven development
(requirements -> design -> tasks) for a hypothetical `GET /fun-fact` endpoint.
It is a planning artifact and is **not implemented** in the codebase.

## Knowledge base

The RAG service answers strictly from these three snippets:

1. BEON.tech's mission — placing the brightest tech talent in disruptive,
   innovative U.S. companies.
2. BEON.tech's IT staff augmentation services — backend, frontend, AI, ML,
   DevOps, QA.
3. BEON.tech's philosophy — relationships, careers, and helping people grow over
   just filling roles.

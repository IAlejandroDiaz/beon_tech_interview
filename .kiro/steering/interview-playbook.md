# Interview Playbook — Beon Tech Live Coding (AI focus)

This repo is the boilerplate for a **live-coding technical interview focused on AI**, with
some Node.js questions. This file is your (Kiro's) standing context so you can support me
fast during the session without re-discovering the project each time.

## What the interviewer asked for

From their email (Spanish, paraphrased):
- Live-coding interview focused on **AI**, plus some **Node** questions.
- I'll be asked to **create a new repository during the interview**.
- To save time, I should **prepare an empty Node repo with a simple POST endpoint**
  beforehand. The exercise will be **built on top of that base**.

Implication: the POST endpoint is the seed. The exercise is unknown but almost certainly
involves calling an AI/LLM API (chat/completion, streaming, tool-calling, RAG, or similar).

## What this repo already provides

TWO parallel stacks for the two sides of the interview:
- **Node (TypeScript)** at repo root — Express REST + GraphQL. Node pinned `26.13.0`.
- **Python** under `python/` — FastAPI async REST only (no GraphQL, kept simple). `uv`-managed,
  Python pinned `3.13`.

Both expose the same `/health` + `/echo` contract so the demo story is identical across
languages. Ports: Express `3000`, GraphQL `4000`, FastAPI `8000`.

### Node (TypeScript), ESM, Node pinned `26.13.0` via `.nvmrc`

```
src/express/server.ts         # Express 5 — GET /health, POST /echo  <- the required POST seed
src/express/server.test.ts    # unit tests (node:test + supertest)
src/graphql/server.ts         # Apollo Server standalone — health query + echo mutation
src/graphql/server.test.ts    # unit tests (node:test + graphql() on the schema)
bruno/                        # Bruno collection: 6 requests (Express/GraphQL/FastAPI × Health/Echo)
tsconfig.json                 # strict, NodeNext ESM, noEmit (we run via tsx)
tsconfig.debug.json           # emits dist/*.js + sourcemaps — used ONLY for debugging
.vscode/launch.json           # debug configs (compile-then-debug the compiled JS)
.vscode/tasks.json            # build:debug task the debug configs run first
.nvmrc                        # pins Node 26.13.0
```

Ports: Express `3000`, GraphQL `4000`.

Key scripts:
- `npm run dev:express` / `npm run dev:graphql` — watch mode (tsx)
- `npm run start:express` / `npm run start:graphql`
- `npm run typecheck` — `tsc` (noEmit; typecheck only, no build step — we run via tsx)
- `npm test` — `tsx --test src/**/*.test.ts` (unit tests; servers do NOT need to be running)

The `POST /echo` handler is intentionally minimal (validates a `message` string, echoes it
back). It is the hook to turn into a real AI endpoint live. The GraphQL `echo` mutation is
its mirror (write), alongside the `health` query (read).

### Python (FastAPI, async, uv), Python pinned `3.13` via `python/.python-version`

```
python/
├── pyproject.toml            # uv-managed: fastapi[standard]; dev: pytest, pytest-asyncio, httpx
├── .python-version           # 3.13
└── src/rest/
    ├── main.py               # FastAPI app: GET /health, POST /echo (async)
    └── test_main.py          # async tests: pytest-asyncio + httpx ASGITransport (in-process)
```

Key commands (run from `python/`):
- `uv run fastapi dev src/rest/main.py` — dev server with reload
- `uv run uvicorn src.rest.main:app --port 8000` — explicit uvicorn (port 8000)
- `uv run pytest` — async unit tests (no server needed; httpx hits the ASGI app in-process)
- `uv add <pkg>` / `uv add --dev <pkg>` — add deps (uv resolves + pins; never pip install)

Python conventions to keep:
- Everything async (`async def` handlers and tests) — it's the point of this side.
- Validation via Pydantic `BaseModel` + `field_validator`; missing/empty/wrong-type body →
  FastAPI's 422 automatically (note: 422, NOT 400 like Express — mention this contrast).
- Response shape matches the Node servers: `{status, service, timestamp}` and
  `{received, length, timestamp}`, ISO-8601 UTC timestamps.
- Tests import `from src.rest.main import app`; `pythonpath = ["."]` + `asyncio_mode = "auto"`
  are set in `pyproject.toml`. Keep handler logic importable (same testability principle as Node).
- uvicorn binds IPv4 `127.0.0.1`; the Bruno `fastapiUrl` uses `127.0.0.1` (not `localhost`) to
  dodge the IPv6 `::1` ECONNREFUSED gotcha.

Python debugging (`python/.vscode/launch.json`, debugpy):
- Configs: "Debug: FastAPI (8000)" (launches uvicorn as a module — use this for request
  breakpoints), "Debug: Current file", "Debug: Pytest".
- MUCH simpler than the Node side: the interpreter runs the actual `.py` — no transpile, no
  sourcemaps, no disk-verification. Breakpoints bind natively by line.
- The ONE requirement: the config pins the uv venv interpreter
  (`${workspaceFolder}/.venv/bin/python`) so FastAPI/uvicorn import. `debugpy` is a dev dep.
- Breakpoint on a statement inside a handler (e.g. the `return {` in `/echo`, not the `async
  def` line), run "Debug: FastAPI (8000)", hit the endpoint (curl / Bruno) → pauses. A
  startup breakpoint pauses before uvicorn listens (same ECONNREFUSED-until-continue behavior
  as the Node servers).

## How to support me during the interview

Priorities, in order:
1. **Speed and correctness.** Working code fast beats clever code. Keep diffs small and
   readable so I can narrate them to the interviewer.
2. **Narrate the "why."** When you write code, give me the one-line rationale I can say out
   loud (why this validation, why this error shape, why streaming here). I'm demonstrating
   expertise, not just producing output.
3. **Match existing style.** ESM imports, `type` imports for types, `process.env.X ?? default`,
   JSON responses with a `timestamp`, explicit status codes. Don't introduce new libraries
   unless I ask.
4. **Verify before declaring done.** Run `npm run typecheck`; run `npm test` if tests exist;
   for integration, start the server and hit it (curl or the Bruno CLI:
   `cd bruno && npx @usebruno/cli run --env Local`).
5. **Flag tradeoffs, don't hide them.** If there's a shortcut vs. a robust approach, tell me
   both in one sentence so I can make the call on camera.

Only add tests when I ask (I may ask during the session). When I do, follow the Testing
section below exactly — same patterns, no new frameworks.

## Testing patterns (follow these when I ask for unit tests)

Keep the established conventions — do NOT introduce Jest, Vitest, Mocha, or any new test
framework. The stack is deliberate and a talking point: Node's built-in runner, zero extra
runtime deps.

**Stack**
- Runner + assertions: `node:test` (`describe`/`it`) + `node:assert/strict`.
- Run via `tsx`: `npm test` → `tsx --test src/**/*.test.ts`.
- Express HTTP: `supertest` against the exported `app` (in-process; no real port).
- GraphQL: `graphql()` from `graphql` run against a schema built with
  `makeExecutableSchema` from `@graphql-tools/schema` — no server, no network.

**Hard rule: unit tests never require a running server.** They do NOT need
`npm run dev:*`. This is only possible because of the testability refactor below — preserve
it in any new code.

**Testability refactor (must be kept)**
- Each server file SEPARATES definition from startup:
  - Express: `export const app = express();` and the `app.listen(...)` call is wrapped in
    `if (import.meta.main) { ... }`.
  - GraphQL: `export const typeDefs` and `export const resolvers`; the
    `startStandaloneServer(...)` call is wrapped in `if (import.meta.main) { ... }`.
- `import.meta.main` is true only for the entry module, so importing a server file in a test
  does NOT boot a listener. (Verified available in Node 26.)
- When adding a new endpoint/resolver, keep its logic importable so it can be unit-tested
  the same way.

**File convention**
- Co-locate tests next to source: `src/<area>/server.test.ts` (matches `src/**/*.test.ts`).
- TS specifics already configured: `allowImportingTsExtensions` + `noEmit`, so imports use
  explicit `.ts` extensions (e.g. `import { app } from "./server.ts"`).

**What to assert**
- Express: status code, response body fields, and the validation paths (missing / empty /
  wrong-type input → 400 with an `error`).
- GraphQL: `result.errors` is `undefined` on success; on bad input assert the error exists
  and `errors[0].extensions.code` (e.g. `BAD_USER_INPUT`). Cover both the resolver guard
  (empty string) AND schema-level validation (missing non-null arg).
- Prefer small, named `it(...)` cases per behavior over one big test.

**Two-layer model to state out loud**
- Unit tests (`npm test`): servers down, logic in isolation, fast.
- Bruno collection (`cd bruno && npx @usebruno/cli run --env Local`): servers UP, real HTTP —
  integration/smoke layer. Keep both in sync when behavior changes.

## Debugging

`.vscode/launch.json` has ready debug configs (editor is VS Code-based, F5 works):
- "Debug: Express (3000)", "Debug: GraphQL (4000)", and a "Debug: Both servers" compound.
  (No test-debug config — debug tests ad hoc if needed; `npm test` covers the normal case.)
- Approach: COMPILE-THEN-DEBUG. The configs run a `build:debug` task first
  (`tsconfig.debug.json` → `dist/*.js` + `.js.map`), then launch the compiled `.js` with
  `outFiles: dist/**/*.js`. `runtimeVersion: "26.13.0"` pins nvm Node (shell default is 24).
- Why NOT debug the `.ts` directly: both tsx and Node's native type-stripping run content
  that differs from the raw `.ts` on disk, so js-debug's "disk verification" fails and EVERY
  breakpoint greys out / stays unbound. Also: the `tsx` CLI / `tsx watch` fork a child, so the
  debugger attaches to the parent, which exits ("Waiting for the debugger to disconnect...").
  Compiling to real `.js` that matches disk + sourcemaps makes breakpoints BIND. (Verified via
  CDP: `setBreakpointByUrl` on `dist/*.js` returns resolved locations; on the `.ts` it returns
  none.)
- MATCH THE RUNNING CONFIG TO THE FILE. A breakpoint only binds in the file whose server
  is actually running. Express session ↔ breakpoints in `src/express/server.ts`; GraphQL
  session ↔ `src/graphql/server.ts`. Setting a GraphQL breakpoint while the Express config
  runs leaves it grey (common source of confusion). Use "Debug: Both servers" to bind in
  either file at once.
- Set the breakpoint on an EXECUTABLE STATEMENT, NOT a comment, blank line, closing brace,
  or object-literal property line — those can NEVER bind and stay grey regardless of config.
  Good Express line: `const { message } = req.body ?? {}`. Good GraphQL line:
  `const message = args.message?.trim() ?? ""`. (The exact line numbers drift as the file
  grows — pick the first real statement in the handler/resolver, not a remembered number.)
- A solid red dot = bound; a hollow/grey dot = not bound (wrong file for the session, or a
  non-code line). Launch, hit the endpoint (curl / Bruno), execution pauses on the line
  (shown in your `.ts` via the sourcemap). Keep the session running while you make requests.
- Gotcha: a leftover debug/`tsx watch`/`node dist/...` server holding port 3000/4000 blocks a
  new launch and causes confusing behavior. Check `lsof -iTCP:3000 -iTCP:4000 -sTCP:LISTEN -P`
  and kill it.
- Gotcha: a breakpoint in STARTUP code (module top level, or inside `if (import.meta.main)` —
  `new ApolloServer`, `startStandaloneServer`, `app.listen`) pauses BEFORE the server listens,
  so requests get ECONNREFUSED. That's not a network bug — just press Continue, or put the
  breakpoint in a handler/resolver body (per-request) instead of the startup path.
- Dev/run/test still use tsx (`npm run dev:*`, `npm test`); ONLY debugging uses compiled
  `dist/`. `dist/` is gitignored and rebuilt by the preLaunchTask.
- Don't add `debugger;` statements to source; use editor breakpoints.

## Likely AI-exercise directions (be ready to pivot the POST endpoint)

When I learn the real task, expect to evolve `POST /echo` (or a new route) into one of:

- **Chat/completion proxy**: accept `{ prompt }`, call an LLM, return the completion.
  Read the key from `process.env` (e.g. `OPENAI_API_KEY`); never hardcode secrets.
- **Streaming**: stream tokens back via SSE (`text/event-stream`) or chunked responses.
- **Tool / function calling**: expose a tool schema, let the model call it, loop the result.
- **RAG**: embed a small corpus, retrieve top-k, stuff context into the prompt.
- **Structured output**: enforce a JSON schema / Zod validation on the model response.
- **Conversation state**: keep message history per session/conversation id.

Cross-cutting concerns to raise proactively when relevant: input validation, API-key
handling via env vars, timeouts and retries on the model call, error handling and useful
status codes, rate-limit awareness, and basic observability (logging latency).

## Node questions — quick-reference talking points

Be ready to explain concisely if asked: event loop and microtasks vs macrotasks,
`async`/`await` and promise error handling, streams and backpressure, CommonJS vs ESM,
`cluster`/`worker_threads` for CPU-bound work, middleware order in Express, and graceful
shutdown. Keep answers short and concrete; offer to show code rather than lecture.

## Environment / secrets

- No secrets are committed. If the exercise needs an API key, read it from `process.env`
  and add the var name to a `.env.example` (not `.env`, which is gitignored).
- If I need to add a dependency live (e.g. an AI SDK, `zod`), use a pinned version and
  tell me the one command to run.

## Fresh-repo note

The interviewer said to create a NEW repo during the interview. This repo is the base to
copy/push. If they want a clean start, we lift `src/express/server.ts` (health + POST) as
the seed and build from there.

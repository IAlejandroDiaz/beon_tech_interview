"""FastAPI REST server (async).

Python mirror of the Node/Express boilerplate: a health check (GET) and a
simple echo endpoint (POST) that acts as the seed for the live AI exercise.
Runs independently on its own port.

Run:  uv run fastapi dev src/rest/main.py        (reload, dev)
      uv run fastapi run src/rest/main.py        (production-style)
      uv run uvicorn src.rest.main:app --reload  (explicit uvicorn)
"""

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

app = FastAPI(title="beon-python-interview", version="0.1.0")


def _now() -> str:
    """ISO-8601 UTC timestamp, matching the Node servers' response shape."""
    return datetime.now(timezone.utc).isoformat()


# --- GET /health -----------------------------------------------------------
# Liveness/readiness probe. Async so it matches the rest of the app's style,
# even though it does no awaiting — FastAPI runs sync and async handlers fine,
# but keeping it async is the convention here.
@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "fastapi", "timestamp": _now()}


# --- POST /echo ------------------------------------------------------------
# The write seed for the interview exercise. Accepts a JSON body, validates it,
# echoes it back. Swap this for a real LLM call live: rename `message` to
# `prompt`, `await` the model client, return the completion.
#
# Validation is declarative via Pydantic: an invalid/empty body yields FastAPI's
# standard 422 response automatically. We add an explicit guard for empty /
# whitespace-only strings and return 400 to mirror the Express contract.
class EchoRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if v.strip() == "":
            raise ValueError("`message` must be a non-empty string.")
        return v


@app.post("/echo")
async def echo(body: EchoRequest) -> dict:
    return {
        "received": body.message,
        "length": len(body.message),
        "timestamp": _now(),
    }

"""Thin wrapper around the Anthropic SDK used by the three LLM steps.

- Model: claude-opus-5-5 (adaptive thinking is always on; depth via `effort`).
- Server-side refusal fallback enabled by default (beta `server-side-fallback-2026-07-01`,
  `fallbacks: "default"`), so a policy decline reruns on a fallback model inside the same call.
- The API key comes from the environment / .env (never committed).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import anthropic

MODEL = "claude-opus-5-5"
BETAS = ["server-side-fallback-2026-07-01"]
ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _load_dotenv()
        _client = anthropic.Anthropic()
    return _client


class LLMError(RuntimeError):
    pass


def create(*, system: str, messages: list, effort: str = "medium", max_tokens: int = 16000,
           tools: list | None = None, output_schema: dict | None = None):
    """One Messages call. Returns the response; raises LLMError on refusal / truncation."""
    kwargs = dict(model=MODEL, max_tokens=max_tokens, system=system, messages=messages,
                  betas=BETAS, fallbacks="default", output_config={"effort": effort})
    if tools:
        kwargs["tools"] = tools
    if output_schema:
        kwargs["output_config"]["format"] = {"type": "json_schema", "schema": output_schema}
    # Stream so long agent turns never hit the SDK's non-streaming timeout guard.
    with client().beta.messages.stream(**kwargs) as stream:
        resp = stream.get_final_message()
    if resp.stop_reason == "refusal":
        cat = resp.stop_details.category if resp.stop_details else None
        raise LLMError(f"model declined (category: {cat})")
    if resp.stop_reason == "max_tokens":
        raise LLMError("response hit max_tokens")
    return resp


def json_call(*, system: str, user: str, schema: dict, effort: str = "medium") -> dict:
    """Structured output: the response's text block is guaranteed to be JSON matching `schema`."""
    resp = create(system=system, messages=[{"role": "user", "content": user}], effort=effort,
                  output_schema=schema)
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)


def usage(resp) -> dict:
    u = resp.usage
    return {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens}

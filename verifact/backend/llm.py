"""LLM client for VeriFact — DashScope (Alibaba Cloud) Qwen.

Uses the OpenAI-compatible Responses API (`POST /responses`) at the
DashScope international endpoint. Thinking mode is disabled for agent
calls: structured JSON output is faster and cleaner without a trace.
Falls back to the standard compatible-mode chat endpoint automatically.
"""
import asyncio
import json
import os
import re

import httpx

# Primary: the Responses-API endpoint (verified format for this key)
RESPONSES_URL = os.environ.get(
    "LLM_RESPONSES_URL",
    "https://dashscope-intl.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1/responses",
)
# Fallback: standard OpenAI-compatible chat endpoint
CHAT_URL = os.environ.get(
    "LLM_CHAT_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
)
MODEL = os.environ.get("LLM_MODEL", "qwen3.7-max-2026-06-08")
API_KEY = os.environ.get(
    "DASHSCOPE_API_KEY",
    "sk-ws-H.LIEMPD.DpZK.MEUCIA7GLanKjqNWA0UKOWsBVdGLaMhqZYh3BHYqMNL9Z_oGAiEA2u1dfrMN6KjNoVmBrQWrYwbfdlgRtKnRIfpRSym-z5M",
)

_use_chat = False  # flips True if the Responses endpoint 404s once


def extract_json(text: str):
    """Pull the first JSON object/array out of a model response."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = text.find(opener), text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"No JSON found in model output: {text[:200]!r}")


def _text_from_responses(data: dict) -> str:
    """Extract answer text from a Responses-API payload (output items)."""
    parts = []
    for item in data.get("output", []) or []:
        if item.get("type") == "message":
            for c in item.get("content", []) or []:
                if c.get("type") in ("output_text", "text") and c.get("text"):
                    parts.append(c["text"])
    if not parts and isinstance(data.get("output_text"), str):
        parts.append(data["output_text"])
    return "".join(parts)


def _text_from_chat(data: dict) -> str:
    return data.get("choices", [{}])[0].get("message", {}).get("content", "")


async def _post(url: str, body: dict) -> httpx.Response:
    headers = {"Authorization": f"Bearer {API_KEY}", "content-type": "application/json"}
    async with httpx.AsyncClient(timeout=180) as client:
        return await client.post(url, json=body, headers=headers)


async def chat(
    messages: list[dict],
    temperature: float = 0.2,
    max_tokens: int = 8000,
    expect_json: bool = False,
    log=None,
) -> str:
    """One logical chat call, with retry/backoff and endpoint fallback."""
    global _use_chat
    last_err = None
    for attempt in range(8):
        try:
            if _use_chat:
                resp = await _post(CHAT_URL, {
                    "model": MODEL, "max_tokens": max_tokens,
                    "temperature": temperature, "messages": messages,
                    "enable_thinking": False,
                })
            else:
                resp = await _post(RESPONSES_URL, {
                    "model": MODEL, "max_tokens": max_tokens,
                    "temperature": temperature, "input": messages,
                    "enable_thinking": False,
                })

            if resp.status_code == 404 and not _use_chat:
                _use_chat = True  # Responses endpoint unavailable → chat fallback
                if log:
                    log("responses endpoint unavailable, using chat endpoint")
                continue
            if resp.status_code == 429:
                wait = _retry_after(resp.text, attempt)
                if log:
                    log(f"rate-limited, waiting {wait}s")
                await asyncio.sleep(wait)
                continue
            if resp.status_code >= 500:
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                await asyncio.sleep(2 + attempt)
                continue
            resp.raise_for_status()
            data = resp.json()
            text = _text_from_chat(data) if _use_chat else _text_from_responses(data)
            if not text:
                last_err = f"empty response: {json.dumps(data)[:200]}"
                continue
            if expect_json:
                try:
                    extract_json(text)
                except ValueError:
                    messages = messages + [
                        {"role": "assistant", "content": text},
                        {
                            "role": "user",
                            "content": "Your last answer was not valid JSON. "
                            "Return ONLY the JSON object, no prose, no code fences.",
                        },
                    ]
                    continue
            return text
        except httpx.HTTPError as e:
            last_err = str(e)
            await asyncio.sleep(2 + attempt)
    raise RuntimeError(f"LLM request failed after 8 attempts: {last_err}")


def _retry_after(body: str, attempt: int) -> float:
    m = re.search(r"after\s+(\d+)\s*second", body)
    return min(float(m.group(1)) + 1, 60) if m else 5 * (attempt + 1)


async def chat_json(
    system: str, user: str, temperature: float = 0.2, max_tokens: int = 8000, log=None
):
    """Chat expecting a JSON object back; returns the parsed object."""
    text = await chat(
        [
            {"role": "user", "content": f"{system}\n\n{user}\n\nReturn ONLY valid JSON."},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        expect_json=True,
        log=log,
    )
    return extract_json(text)

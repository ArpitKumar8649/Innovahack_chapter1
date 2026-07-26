"""Serper.dev client — Google SERP results as structured JSON.

Endpoints (all verified working 2026-07-25):
  POST /search   → organic[], peopleAlsoAsk[], knowledgeGraph, answerBox
  POST /scholar  → academic papers (authority signal)
  POST /news     → recency-sensitive results
"""
import os

import httpx

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
BASE = "https://google.serper.dev"
HEADERS = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}


async def _post(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(f"{BASE}{path}", json=payload, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


async def web_search(query: str, num: int = 10) -> dict:
    """Returns {organic, people_also_ask, answer_box, knowledge_graph}."""
    try:
        d = await _post("/search", {"q": query, "num": num})
    except Exception:
        return {"organic": [], "people_also_ask": [], "answer_box": None,
                "knowledge_graph": None}
    return {
        "organic": [
            {"title": r.get("title", ""), "url": r.get("link", ""),
             "snippet": r.get("snippet", "")}
            for r in d.get("organic", []) if r.get("link")
        ],
        "people_also_ask": [
            p.get("question", "") for p in d.get("peopleAlsoAsk", [])
            if p.get("question")
        ],
        "answer_box": d.get("answerBox"),
        "knowledge_graph": d.get("knowledgeGraph"),
    }


async def scholar_search(query: str) -> list[dict]:
    """Academic papers — peer-review authority signal."""
    try:
        d = await _post("/scholar", {"q": query})
    except Exception:
        return []
    return [
        {"title": r.get("title", ""), "url": r.get("link", ""),
         "snippet": r.get("publicationInfo", "") or r.get("snippet", ""),
         "scholar": True}
        for r in d.get("organic", []) if r.get("link")
    ][:5]


async def news_search(query: str) -> list[dict]:
    """Recent news — recency signal for fast-moving topics."""
    try:
        d = await _post("/news", {"q": query})
    except Exception:
        return []
    return [
        {"title": r.get("title", ""), "url": r.get("link", ""),
         "snippet": r.get("snippet", ""), "date": r.get("date", ""),
         "news": True}
        for r in d.get("news", []) if r.get("link")
    ][:5]

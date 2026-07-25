"""Thin async Tavily client (search only — snippets are enough for verification)."""
import os

import httpx

TAVILY_API_KEY = os.environ.get(
    "TAVILY_API_KEY", "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"
)
API = "https://api.tavily.com"


async def search(query: str, max_results: int = 5) -> list[dict]:
    """Returns [{title, url, content, score}]; empty list on failure."""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{API}/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                },
            )
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception:
        return []

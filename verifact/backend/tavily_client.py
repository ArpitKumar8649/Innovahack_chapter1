"""Thin async Tavily client — search (snippets) and extract (full content)."""
import os

import httpx

TAVILY_API_KEY = os.environ.get(
    "TAVILY_API_KEY", "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"
)
API = "https://api.tavily.com"
HEADERS = {"Authorization": f"Bearer {TAVILY_API_KEY}",
           "Content-Type": "application/json"}


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


async def extract(urls: list[str], depth: str = "basic") -> dict[str, str]:
    """Full-text extraction for up to 20 URLs. Returns {url: raw_content}."""
    out: dict[str, str] = {}
    for i in range(0, len(urls), 20):
        batch = urls[i : i + 20]
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{API}/extract",
                    json={"urls": batch, "extract_depth": depth},
                    headers=HEADERS,
                )
            resp.raise_for_status()
            for r in resp.json().get("results", []):
                content = r.get("raw_content") or ""
                if r.get("url") and content.strip():
                    out[r["url"]] = content
        except Exception:
            continue
    return out

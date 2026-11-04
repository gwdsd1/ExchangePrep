"""Bounded, request-local access to DeepSeek's official Search and Fetch APIs."""
import re
import time

import httpx


class DeepSeekWebError(RuntimeError):
    """Sanitized error: never expose the response body or authorization header."""
    def __init__(self, operation, status_code=None, reason="request failed"):
        self.status_code = status_code
        self.operation = operation
        self.fatal = status_code in {401, 402}
        super().__init__(f"DeepSeek {operation}: HTTP {status_code}" if status_code else
                         f"DeepSeek {operation}: {reason}")


def search_query(query):
    """Keep site/date/language operators when fitting the API's 128-char limit."""
    query = " ".join(query.split())
    if not query:
        raise ValueError("Search query cannot be empty")
    if len(query) <= 128:
        return query
    operators = re.findall(r"(?<!\S)(?:-?site|lang|after|before):\S+", query)
    rest = re.sub(r"(?<!\S)(?:-?site|lang|after|before):\S+", "", query)
    compact = " ".join(operators + rest.split())[:128].rstrip()
    if compact.count('"') % 2:
        compact = compact.replace('"', '')
    return compact


class DeepSeekWeb:
    def __init__(self, client, key, *, max_search=20, max_fetch=40):
        self.client = client
        self._key = key
        self.limits = {"search": max_search, "fetch": max_fetch}
        self.calls = {"search": 0, "fetch": 0}

    def _post(self, operation, payload):
        for attempt in range(2):
            if self.calls[operation] >= self.limits[operation]:
                raise DeepSeekWebError(operation, reason="request budget exhausted")
            self.calls[operation] += 1
            try:
                response = self.client.post(
                    f"https://api.deepseek.com/v1/tools/{operation}", json=payload,
                    headers={"Authorization": f"Bearer {self._key}",
                             "Content-Type": "application/json"},
                    timeout=30, follow_redirects=False)
            except httpx.TransportError:
                if attempt == 0:
                    time.sleep(.5)
                    continue
                raise DeepSeekWebError(operation, reason="connection or timeout error") from None
            if response.status_code != 200:
                if attempt == 0 and response.status_code in {408, 429, 500, 502, 503, 504}:
                    time.sleep(.5)
                    continue
                raise DeepSeekWebError(operation, response.status_code)
            if len(response.content) > 3_000_000:
                raise DeepSeekWebError(operation, reason="response exceeds 3 MB limit")
            try:
                data = response.json()
            except ValueError:
                raise DeepSeekWebError(operation, reason="invalid JSON response") from None
            if not isinstance(data, dict):
                raise DeepSeekWebError(operation, reason="invalid response shape")
            return data

    def search(self, query, *, original_question=""):
        query = search_query(query)
        payload = {"query": query, "count": 8, "need_content": False}
        if original_question.strip():
            payload["ori_question"] = original_question.strip()[:128]
        data = self._post("search", payload)
        if not isinstance(data.get("results"), list):
            raise DeepSeekWebError("search", reason="missing results array")
        hits, seen = [], set()
        for item in data["results"][:50]:
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            if not isinstance(url, str) or not url.startswith(("https://", "http://")) or url in seen:
                continue
            seen.add(url)
            # Snippets/summaries are discovery leads, never page evidence.
            hits.append({"url": url, "title": str(item.get("title") or url)[:240],
                "snippet": str(item.get("snippet") or "")[:650],
                "summary": str(item.get("summary") or "")[:1600],
                "query": query, "engine": "deepseek", "date": item.get("date"),
                "authority": item.get("authority"), "rerank_score": item.get("rerank_score")})
        return hits

    def fetch(self, url):
        data = self._post("fetch", {"url": url})
        if not isinstance(data.get("content"), str) or not data["content"].strip():
            raise DeepSeekWebError("fetch", reason="empty page content")
        return {"title": str(data.get("title") or url)[:240], "content": data["content"]}

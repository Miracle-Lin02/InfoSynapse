# utils/search_client.py
"""
SearchClient - wrapper for Web Search APIs
Supports:
 - SerpAPI (serpapi)  : https://serpapi.com/ (engine=google)
 - Bing Web Search (bing) : Microsoft Bing Web Search API
Usage:
  client = SearchClient(provider='serpapi', api_key=...)
  snippets = client.search_snippets("machine learning transformers", top_k=5)
Returns list of dicts: [{"title":..., "link":..., "snippet":...}, ...]
"""
import os
import logging
from typing import List, Dict, Optional
import requests

logger = logging.getLogger("search_client")

class SearchClient:
    def __init__(self, provider: Optional[str] = None, api_key: Optional[str] = None, timeout: int = 10):
        # provider: 'serpapi' or 'bing'
        self.provider = provider or os.getenv("SEARCH_API_PROVIDER", "") or ""
        self.api_key = api_key or os.getenv("SEARCH_API_KEY", "") or ""
        self.timeout = timeout
        if self.provider:
            self.provider = self.provider.lower()
        logger.info(f"SearchClient init provider={self.provider} key_set={bool(self.api_key)}")

    def _serpapi_search(self, q: str, top_k: int = 5) -> List[Dict]:
        # SerpAPI "google" engine search. Requires serpapi key.
        url = "https://serpapi.com/search.json"
        params = {"q": q, "engine": "google", "num": top_k, "hl": "en"}
        params["api_key"] = self.api_key
        try:
            r = requests.get(url, params=params, timeout=self.timeout)
            r.raise_for_status()
            jd = r.json()
            results = []
            # serpapi returns 'organic_results'
            for it in jd.get("organic_results", [])[:top_k]:
                results.append({
                    "title": it.get("title"),
                    "link": it.get("link") or it.get("formatted_link"),
                    "snippet": it.get("snippet") or it.get("snippet_highlighted") or ""
                })
            return results
        except Exception as e:
            logger.warning(f"SerpAPI search failed: {e}")
            return []

    def _bing_search(self, q: str, top_k: int = 5) -> List[Dict]:
        # Microsoft Bing Web Search API (v7)
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        params = {"q": q, "count": top_k}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            r.raise_for_status()
            jd = r.json()
            results = []
            web_pages = jd.get("webPages", {}).get("value", [])
            for it in web_pages[:top_k]:
                results.append({
                    "title": it.get("name"),
                    "link": it.get("url"),
                    "snippet": it.get("snippet") or ""
                })
            return results
        except Exception as e:
            logger.warning(f"Bing search failed: {e}")
            return []

    def search_snippets(self, query: str, top_k: int = 5) -> List[Dict]:
        """Return list of {'title','link','snippet'}"""
        if not self.provider or not self.api_key:
            logger.info("SearchClient: no provider or api_key set — returning []")
            return []
        if self.provider == "serpapi":
            return self._serpapi_search(query, top_k=top_k)
        if self.provider == "bing":
            return self._bing_search(query, top_k=top_k)
        logger.warning(f"Unknown search provider: {self.provider}")
        return []
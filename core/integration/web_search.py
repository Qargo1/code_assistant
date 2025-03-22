import requests
from googlesearch import search
from urllib.parse import urlparse
import json

class WebSearchManager:
    def __init__(self):
        self.search_cache = {}

    def google_search(self, query: str, num_results=3) -> list:
        if query in self.search_cache:
            return self.search_cache[query]
        
        results = []
        try:
            for url in search(query, num_results=num_results):
                if self._is_reliable_source(url):
                    content = self._extract_content(url)
                    results.append({"url": url, "content": content[:500]})
            
            self.search_cache[query] = results
            return results
        except Exception as e:
            return [{"error": str(e)}]

    def _is_reliable_source(self, url: str) -> bool:
        domain = urlparse(url).netloc
        return any(d in domain for d in ["stackoverflow", "github", "official-docs"])

    def _extract_content(self, url: str) -> str:
        try:
            response = requests.get(url, timeout=5)
            return response.text
        except:
            return ""
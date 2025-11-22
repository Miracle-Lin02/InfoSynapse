# -*- coding: utf-8 -*-
"""
GitHubCrawler
- 如果提供 GITHUB_TOKEN，则使用 GitHub Search API 搜索与兴趣相关的仓库（按 stars 排序）
- 否则降级为爬取 https://github.com/trending/<language> 页面（按语言或 topic）
- 提供 top_repos_for_topic(topic, top_n) 接口，返回 repo dicts with keys:
  name, full_name, html_url, description, stargazers_count, language, owner
注意：
- 若使用 GitHub API，请在环境变量或 st.secrets 中设置 GITHUB_TOKEN（不要写入代码）
- API 有速率限制：未认证约 60 req/hour，认证后为更高额度
"""
import os
import time
import logging
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("github_crawler")

class GitHubCrawler:
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.session = requests.Session()
        headers = {"User-Agent": "InfoSynapseGitHubCrawler/1.0"}
        if token:
            headers["Authorization"] = f"token {token}"
        self.session.headers.update(headers)
        self.api_search = "https://api.github.com/search/repositories"

    def _search_api(self, query: str, top_n: int = 8) -> List[Dict[str, Any]]:
        params = {"q": query, "sort": "stars", "order": "desc", "per_page": top_n}
        try:
            r = self.session.get(self.api_search, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            items = data.get("items", [])[:top_n]
            repos = []
            for it in items:
                repos.append({
                    "name": it.get("name"),
                    "full_name": it.get("full_name"),
                    "html_url": it.get("html_url"),
                    "description": it.get("description"),
                    "stargazers_count": it.get("stargazers_count"),
                    "language": it.get("language"),
                    "owner": it.get("owner", {}).get("login")
                })
            return repos
        except Exception as e:
            logger.warning(f"GitHub API search failed: {e}")
            return []

    def _scrape_trending(self, language_or_topic: str, top_n: int = 8) -> List[Dict[str, Any]]:
        url = f"https://github.com/trending/{language_or_topic}?since=daily"
        try:
            r = self.session.get(url, timeout=12)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            articles = soup.find_all('article', class_='Box-row')[:top_n]
            repos = []
            for a in articles:
                # repository full name in <h2><a href="/owner/repo"> owner / repo </a></h2>
                h2 = a.find('h2')
                if not h2:
                    continue
                a_tag = h2.find('a')
                if not a_tag:
                    continue
                href = a_tag.get('href', '').strip()
                full_name = href.strip('/')

                # name & owner
                parts = full_name.split('/')
                owner = parts[0] if parts else ""
                name = parts[1] if len(parts) > 1 else parts[0] if parts else ""

                desc_tag = a.find('p', class_='col-9')
                description = desc_tag.get_text(strip=True) if desc_tag else ""

                star_tag = a.find('a', href=lambda x: x and x.endswith('/stargazers'))
                stars = star_tag.get_text(strip=True) if star_tag else None
                try:
                    stars_int = int(stars.replace(',', '')) if stars else 0
                except:
                    stars_int = 0

                lang_tag = a.find('span', itemprop='programmingLanguage')
                language = lang_tag.get_text(strip=True) if lang_tag else None

                repos.append({
                    "name": name,
                    "full_name": full_name,
                    "html_url": f"https://github.com/{full_name}",
                    "description": description,
                    "stargazers_count": stars_int,
                    "language": language,
                    "owner": owner
                })
            return repos
        except Exception as e:
            logger.warning(f"Scraping GitHub trending failed: {e}")
            return []

    def top_repos_for_topic(self, topic: str, top_n: int = 8) -> List[Dict[str, Any]]:
        """Return top repos for a given topic/interest.
        Strategy:
          1) If token available, use search API with queries targeting name/description/readme/topics.
          2) Else attempt to treat topic as language and scrape trending.
        """
        topic_clean = topic.strip().lower()
        if not topic_clean:
            return []

        # If token exists, try GitHub Search API
        if self.token:
            # construct a search query: topic in name/description/readme; also search by language keyword if looks like language
            query = f"{topic_clean} in:name,description,readme"
            # also try language: if simple token like 'python' or 'java'
            # We'll run API search once with this query
            repos = self._search_api(query, top_n=top_n)
            if repos:
                return repos

        # Fallback: scrape trending assuming the topic maybe a language slug
        try:
            return self._scrape_trending(topic_clean, top_n=top_n)
        except Exception as e:
            logger.warning(f"top_repos_for_topic fallback failed: {e}")
            return []

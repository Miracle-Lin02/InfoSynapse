# utils/agent_recommender.py
"""
AgentRecommender - combine KB + GitHub + Web snippets and call AI agent (DeepSeek)
Outputs: list of recommendations with fields:
  id, name, source, score (optional), reason (str), plan (str), links (list)
Behavior:
 - If SEARCH client provided and returns snippets, include them in prompt.
 - Try to parse JSON output from agent; if non-JSON, return textual 'raw' output as one entry.
"""
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("agent_recommender")

def _shorten(text: str, n: int = 400) -> str:
    if not text:
        return ""
    return text if len(text) <= n else text[:n-1] + "…"

class AgentRecommender:
    def __init__(self, ai_agent, kb: Dict[str, Any], github_crawler=None, search_client=None, max_candidates:int = 20):
        self.ai_agent = ai_agent
        self.kb = kb
        self.github = github_crawler
        self.search = search_client
        self.max_candidates = max_candidates

    def _collect_kb_summary(self, interests: List[str], max_items: int = 10) -> List[Dict[str, Any]]:
        # Flatten some KB items likely relevant: courses, practice, jds, advisors
        candidates = []
        # practice
        for p in self.kb.get("practice", [])[:max_items]:
            candidates.append({"id": f"kb_practice:{p.get('name')}", "name": p.get("name"), "source": "KB", "desc": _shorten(p.get("desc","")), "link": p.get("link","")})
        # advisors (include research)
        for a in self.kb.get("advisors", [])[:max_items]:
            candidates.append({"id": f"kb_advisor:{a.get('name')}", "name": a.get("name"), "source": "KB", "desc": _shorten(a.get("research","")), "link": a.get("homepage","")})
        # jds
        for j in self.kb.get("jds", [])[:max_items]:
            candidates.append({"id": f"kb_jd:{j.get('company')}_{j.get('position')}", "name": f"{j.get('company')} - {j.get('position')}", "source": "KB", "desc": _shorten(j.get("jd","")), "link": j.get("link","")})
        return candidates

    def _collect_github_candidates(self, interests: List[str], per_topic:int = 10) -> List[Dict[str, Any]]:
        out = []
        if not self.github:
            return out
        seen = set()
        for t in interests:
            try:
                fetched = self.github.top_repos_for_topic(t, top_n=per_topic)
            except Exception as e:
                logger.warning(f"GitHub fetch for topic {t} failed: {e}")
                fetched = []
            for r in fetched:
                key = r.get("full_name") or r.get("name")
                if not key or key in seen:
                    continue
                seen.add(key)
                out.append({
                    "id": f"gh:{key}",
                    "name": key,
                    "source": "GitHub",
                    "desc": _shorten(r.get("description","")),
                    "stars": r.get("stargazers_count", r.get("stargazers", 0)),
                    "link": r.get("html_url")
                })
        return out

    def _collect_web_snippets(self, interests: List[str], top_k:int = 5) -> List[Dict[str, Any]]:
        out = []
        if not self.search:
            return out
        for t in interests:
            q = f"{t} latest trends 2025"
            try:
                snippets = self.search.search_snippets(q, top_k=top_k)
            except Exception as e:
                logger.warning(f"Search for '{q}' failed: {e}")
                snippets = []
            for s in snippets:
                out.append({"topic": t, "title": s.get("title"), "link": s.get("link"), "snippet": _shorten(s.get("snippet",""), 600)})
        return out

    def recommend_with_agent(self, interests: List[str], top_n:int = 6, include_web: bool = True) -> List[Dict[str, Any]]:
        """
        Main method. Returns list of recommendations.
        """
        if not interests:
            return []

        # collect candidates
        kb_cands = self._collect_kb_summary(interests, max_items=10)
        gh_cands = self._collect_github_candidates(interests, per_topic=8)
        web_snips = self._collect_web_snippets(interests, top_k=4) if include_web else []

        # build prompt (compact)
        prompt_lines = []
        prompt_lines.append("你是一个为杭电学生服务的智能推荐助理。")
        prompt_lines.append(f"用户兴趣关键词: {', '.join(interests)}")
        prompt_lines.append("下面是来自本地知识库的候选项（KB）：")
        for k in kb_cands[:10]:
            prompt_lines.append(f"- {k['name']} | {k.get('desc','')} | {k.get('link','')}")
        prompt_lines.append("下面是从 GitHub 收集到的候选仓（name | stars | 简要）：")
        for g in gh_cands[:20]:
            prompt_lines.append(f"- {g['name']} | stars: {g.get('stars',0)} | {g.get('desc','')} | {g.get('link','')}")
        if web_snips:
            prompt_lines.append("下面是检索到的网页/文章摘要（最新前沿信息）：")
            for w in web_snips[:20]:
                prompt_lines.append(f"- [{w.get('topic')}] {w.get('title')} | {w.get('snippet')} | {w.get('link')}")
        prompt_lines.append("")
        prompt_lines.append(
            "任务：请基于上述信息综合排序并返回 Top %d 推荐（可以是 KB 条目 或 GitHub 仓），"
            "对每项给出：id、name、source、score(0-100)、简短匹配理由（1-2 行）、以及一周可执行的学习/实践计划(3-5 步)，并返回 JSON 数组，"
            "JSON 每项格式示例： {\"id\":\"\",\"name\":\"\",\"source\":\"\",\"score\":90,\"reason\":\"\",\"plan\":\"\",\"links\":[...]} 。"
            % top_n
        )
        prompt_text = "\n".join(prompt_lines)

        # call agent
        try:
            resp_text = self.ai_agent.call(prompt_text, temperature=0.2, max_tokens=1000)
        except Exception as e:
            logger.warning(f"Agent call failed: {e}")
            resp_text = ""

        # try parse JSON from response
        try:
            data = json.loads(resp_text)
            if isinstance(data, list):
                # validate minimal keys
                out = []
                for it in data[:top_n]:
                    out.append({
                        "id": it.get("id") or it.get("name"),
                        "name": it.get("name"),
                        "source": it.get("source"),
                        "score": it.get("score"),
                        "reason": it.get("reason"),
                        "plan": it.get("plan"),
                        "links": it.get("links", [])
                    })
                return out
        except Exception:
            # not JSON - fallback to single textual entry
            pass

        # fallback: return the raw agent text as one item
        logger.info("Agent returned non-JSON; returning raw text fallback.")
        return [{"id":"agent_raw","name":"Agent 响应（原始）","source":"Agent","score":None,"reason":resp_text,"plan":"", "links":[]}]
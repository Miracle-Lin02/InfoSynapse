# -*- coding: utf-8 -*-
"""
推荐逻辑模块：
- AIAgent 包装
- KB + GitHub 综合推荐
- 随机 GitHub 项目推荐（调用 github_crawler + 缓存）
- 按兴趣+地区的职业推荐 & 学习路径（已放宽条件，单个兴趣也能返回职业）
- 智能体推荐项目（基于兴趣 & 技能 & 目标职业）
"""

import json
import math
import random
import logging
from typing import List, Dict, Any

import requests
import streamlit as st

logger = logging.getLogger("recommend")


class AIAgent:
    def __init__(
        self,
        api_key: str = "",
        api_url: str = "https://api.deepseek.com/chat/completions",
        timeout: int = 60,
    ):
        self.api_key = api_key
        self.api_url = api_url
        self.timeout = timeout

    def _local_template(self, prompt: str) -> str:
        if "推荐" in prompt and "项目" in prompt:
            return """```json
[
  {
    "name": "Vue 3",
    "url": "https://github.com/vuejs/core",
    "description": "易学易用的渐进式 JavaScript 框架",
    "learning_value": "学习现代前端架构与响应式原理",
    "difficulty": "medium",
    "estimated_time": "8",
    "tech_stack": ["TypeScript", "Vue"]
  },
  {
    "name": "FastAPI",
    "url": "https://github.com/tiangolo/fastapi",
    "description": "现代、高性能 Python Web 框架",
    "learning_value": "掌握异步编程与 API 设计",
    "difficulty": "medium",
    "estimated_time": "6",
    "tech_stack": ["Python", "ASGI"]
  }
]
```"""
        if "职业" in prompt or "career" in prompt:
            return "【本地回退】根据你的兴趣，推荐以下职业方向：\n- 全栈开发工程师\n- 数据分析师\n- AI工程师"
        if "学习路径" in prompt or "learning path" in prompt:
            return "【本地回退】建议：基础-进阶-项目三阶段，每阶段 1-2 个月，配合 2-3 个小项目。"
        return "【本地回退】请配置 DEEPSEEK_API_KEY 以使用真实 AI。"

    def call(self, prompt: str, temperature: float = 0.7, max_tokens: int = 800) -> str:
        if not self.api_key:
            return self._local_template(prompt)
        try:
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            r = requests.post(
                self.api_url, json=payload, headers=headers, timeout=self.timeout
            )
            r.raise_for_status()
            d = r.json()
            return (
                d.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                or d.get("choices", [{}])[0].get("text", "")
                or self._local_template(prompt)
            )
        except Exception as e:
            logger.warning(f"AIAgent.call failed: {e}")
            return self._local_template(prompt)


# Configuration constants
NATIONAL_STRATEGIC_BONUS = 2.0  # Bonus score for national strategic positions
LOCATION_GLOBAL = "全国"  # Global location marker

# Social value and patriotic keywords for filtering
SOCIAL_VALUE_KEYWORDS = [
    "挑战杯", "红色", "公益", "助老", "乡村", "振兴",
    "志愿", "扶贫", "社会服务", "开源", "国产"
]

PATRIOTIC_OPENSOURCE_KEYWORDS = [
    "openeuler", "openkylin", "opengauss", "mindspore", "paddlepaddle",
    "china", "chinese", "国产", "自主", "开源", "公益", "education",
    "healthcare", "environmental", "accessibility", "charity"
]

DEFAULT_WEIGHTS = {
    "INTEREST_NAME_WEIGHT": 30.0,
    "INTEREST_DESC_WEIGHT": 18.0,
    "TAG_MATCH_WEIGHT": 12.0,
    "KB_BASE_SCORE": 6.0,
    "SOURCE_GITHUB_BONUS": 5.0,
    "SOURCE_KB_BONUS": 2.0,
    "GITHUB_STAR_WEIGHT_FACTOR": 6.0,
    "GITHUB_STAR_MAX_BONUS": 40.0,
    "RANDOM_TIE_BREAKER": 1.5,
}

CONFIG = {
    "RECOMMEND_MAX_ITEMS": 12,
    "GITHUB_FETCH_PER_TOPIC": 30,
    "GITHUB_PICK_TOTAL": 8,
}
CONFIG.update(DEFAULT_WEIGHTS)


INTEREST_TOPIC_MAP: Dict[str, List[str]] = {
    "Python开发": ["python", "django", "fastapi", "flask"],
    "机器学习": ["machine-learning", "pytorch", "tensorflow", "scikit-learn"],
    "前端": ["javascript", "react", "vue", "frontend", "typescript"],
    "后端": ["backend", "spring-boot", "go", "nodejs", "microservices"],
    "算法": ["algorithm", "data-structures", "leetcode", "competitive-programming"],
    "嵌入式": ["embedded-systems", "stm32", "arduino", "rtos"],
    "区块链": ["blockchain", "solidity", "web3", "ethereum"],
    "计算机视觉": ["computer-vision", "opencv", "image-processing", "yolo"],
}


def _kb_items_as_candidates(kb: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = []
    for major, course_list in kb.get("courses", {}).items():
        for c in course_list:
            candidates.append(
                {
                    "id": f"course:{c.get('code','')}",
                    "name": c.get("name"),
                    "type": "course",
                    "desc": c.get("outline", ""),
                    "tags": [c.get("level", ""), major],
                    "source": "KB",
                    "url": c.get("link", ""),
                    "meta": c,
                }
            )
    for p in kb.get("practice", []):
        candidates.append(
            {
                "id": f"practice:{p.get('name')}",
                "name": p.get("name"),
                "type": "practice",
                "desc": p.get("desc", ""),
                "tags": [p.get("type", "")],
                "source": "KB",
                "url": p.get("link", ""),
                "meta": p,
            }
        )
    for j in kb.get("jds", []):
        candidates.append(
            {
                "id": f"jd:{j.get('company')}_{j.get('position')}",
                "name": f"{j.get('company')} - {j.get('position')}",
                "type": "job",
                "desc": j.get("jd", ""),
                "tags": j.get("skills", []),
                "source": "KB",
                "url": j.get("link", ""),
                "meta": j,
            }
        )
    for a in kb.get("advisors", []):
        tags = []
        if a.get("department"):
            tags.append(a.get("department"))
        if a.get("research"):
            tags += [x.strip() for x in a.get("research", "").split("/") if x.strip()]
        candidates.append(
            {
                "id": f"advisor:{a.get('name')}",
                "name": a.get("name"),
                "type": "advisor",
                "desc": a.get("research", ""),
                "tags": tags,
                "source": "KB",
                "url": a.get("homepage", ""),
                "meta": a,
            }
        )
    return candidates


def _github_repos_candidates_from_session(interests: List[str]) -> List[Dict[str, Any]]:
    out = []
    cached = st.session_state.get("github_repos", [])
    if cached:
        for r in cached:
            key = r.get("full_name") or f"{r.get('owner','')}/{r.get('name','')}"
            out.append(
                {
                    "id": f"github:{key}",
                    "name": key,
                    "type": "github",
                    "desc": r.get("description", ""),
                    "tags": [r.get("language", "")] + (
                        [r.get("matched_interest")] if r.get("matched_interest") else []
                    ),
                    "source": "GitHub",
                    "url": r.get("html_url"),
                    "stars": r.get("stargazers_count", r.get("stargazers", 0)),
                    "meta": r,
                }
            )
    return out


def _score_candidate_live(candidate: Dict[str, Any], interests: List[str]) -> float:
    weights = {
        k: float(st.session_state.get(k, CONFIG.get(k, 0.0)))
        for k in DEFAULT_WEIGHTS.keys()
    }
    score = 0.0
    name = (candidate.get("name") or "").lower()
    desc = (candidate.get("desc") or "").lower()
    tags = [str(t).lower() for t in candidate.get("tags", []) if t]
    for i in interests:
        ik = i.lower()
        if ik in name:
            score += weights["INTEREST_NAME_WEIGHT"]
        if ik in desc:
            score += weights["INTEREST_DESC_WEIGHT"]
        if any(ik in t for t in tags):
            score += weights["TAG_MATCH_WEIGHT"]
    if candidate.get("source") == "GitHub":
        stars = candidate.get("stars", 0) or 0
        star_bonus = math.log1p(stars) * weights["GITHUB_STAR_WEIGHT_FACTOR"]
        star_bonus = min(star_bonus, weights["GITHUB_STAR_MAX_BONUS"])
        score += star_bonus + weights["SOURCE_GITHUB_BONUS"]
    else:
        score += weights["KB_BASE_SCORE"] + weights["SOURCE_KB_BONUS"]
        meta = candidate.get("meta", {})
        heat = meta.get("热度") if isinstance(meta.get("热度"), (int, float)) else 0
        if heat:
            score += min(8.0, heat / 10.0)
    score += random.uniform(0, weights["RANDOM_TIE_BREAKER"])
    return score


def get_combined_recommendations(
    kb: Dict[str, Any], interests: List[str], max_items: int = 12
) -> List[Dict[str, Any]]:
    if not interests:
        return []
    kb_cands = _kb_items_as_candidates(kb)
    gh_cands = _github_repos_candidates_from_session(interests)
    all_cands = kb_cands + gh_cands
    scored = []
    for c in all_cands:
        s = _score_candidate_live(c, interests)
        cc = dict(c)
        cc["score"] = round(s, 2)
        reason_parts = []
        for i in interests:
            ik = i.lower()
            if ik in (c.get("name", "") or "").lower():
                reason_parts.append(f"名称匹配：{i}")
            if ik in (c.get("desc", "") or "").lower():
                reason_parts.append(f"描述匹配：{i}")
            if any(ik in str(t).lower() for t in c.get("tags", [])):
                reason_parts.append(f"标签匹配：{i}")
        cc["match_reason"] = "; ".join(reason_parts) or "关键词匹配较低"
        scored.append(cc)
    scored.sort(key=lambda x: x.get("score", 0), reverse=True)
    return scored[:max_items]


def weighted_sample_without_replacement(
    items: List[Dict[str, Any]], weights: List[float], k: int
) -> List[Dict[str, Any]]:
    if not items or k <= 0:
        return []
    if len(items) <= k:
        return items.copy()
    pool = items.copy()
    w = weights.copy()
    selected = []
    for _ in range(min(k, len(pool))):
        total = sum(w)
        if total <= 0:
            random.shuffle(pool)
            selected.extend(pool[: (k - len(selected))])
            break
        r = random.random() * total
        cum = 0.0
        idx = None
        for i, weight in enumerate(w):
            cum += weight
            if r <= cum:
                idx = i
                break
        if idx is None:
            idx = len(w) - 1
        selected.append(pool[idx])
        pool.pop(idx)
        w.pop(idx)
    return selected


def recommend_random_repos(
    interests: List[str],
    github_crawler=None,
    per_topic_fetch: int = None,
    total_pick: int = None,
) -> List[Dict[str, Any]]:
    per_topic_fetch = per_topic_fetch or CONFIG["GITHUB_FETCH_PER_TOPIC"]
    total_pick = total_pick or CONFIG["GITHUB_PICK_TOTAL"]
    if not interests:
        return []

    candidates = []
    seen = set()
    topics_used: List[str] = []

    if github_crawler:
        topic_list: List[str] = []
        for interest in interests:
            mapped = INTEREST_TOPIC_MAP.get(interest, [])
            if mapped:
                topic_list.extend(mapped)
            else:
                topic_list.append(interest)
        topic_list = list(dict.fromkeys([t for t in topic_list if t]))
        topics_used = topic_list.copy()

        for topic in topic_list:
            try:
                fetched = github_crawler.top_repos_for_topic(
                    topic, top_n=per_topic_fetch
                )
            except Exception as e:
                logger.warning(f"GitHub fetch error for topic={topic}: {e}")
                fetched = []
            for r in fetched:
                key = r.get("full_name") or f"{r.get('owner','')}/{r.get('name','')}"
                if not key or key in seen:
                    continue
                seen.add(key)
                item = {
                    "full_name": key,
                    "html_url": r.get("html_url") or f"https://github.com/{key}",
                    "description": r.get("description") or "",
                    "stargazers_count": int(
                        r.get("stargazers_count", r.get("stargazers", 0) or 0)
                    ),
                    "language": r.get("language") or "",
                    "matched_interest": topic,
                }
                candidates.append(item)

        if candidates:
            st.session_state["github_repos"] = candidates

    if not candidates and st.session_state.get("github_repos"):
        for r in st.session_state["github_repos"]:
            key = r.get("full_name") or r.get("name")
            if not key or key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "full_name": key,
                    "html_url": r.get("html_url") or f"https://github.com/{key}",
                    "description": r.get("description") or "",
                    "stargazers_count": int(
                        r.get("stargazers_count", r.get("stargazers", 0) or 0)
                    ),
                    "language": r.get("language") or "",
                    "matched_interest": r.get("matched_interest", ""),
                }
            )

    st.session_state["github_topics_used"] = topics_used
    st.session_state["github_fetch_count"] = len(candidates)

    if not candidates:
        return []

    weights = [
        math.log1p(c.get("stargazers_count", 0) or 0) + 0.1 for c in candidates
    ]
    k = min(total_pick, len(candidates))
    selected = weighted_sample_without_replacement(candidates, weights, k)
    random.shuffle(selected)
    return selected


# ===== 职业配置（用于职业推荐，放宽匹配条件） =====

CAREER_CONFIG: List[Dict[str, Any]] = [
    {
        "career": "后端工程师",
        "tags": ["Python开发", "后端", "Web开发"],
        "locations": [],  # 空列表表示地区不限
        "skills": ["Python/Java", "数据库", "Linux", "API 设计"],
        "salary": "12k-25k/月",
        "companies": "互联网大厂、中小型互联网公司",
        "national_strategic": False,
    },
    {
        "career": "数据分析师",
        "tags": ["数据分析", "Python开发", "机器学习"],
        "locations": ["北京", "上海", "深圳", "广州", "杭州"],
        "skills": ["SQL", "Python", "Excel", "可视化"],
        "salary": "12k-22k/月",
        "companies": "互联网、消费、金融、咨询",
        "national_strategic": False,
    },
    {
        "career": "机器学习工程师",
        "tags": ["机器学习", "深度学习", "算法", "Python开发"],
        "locations": ["北京", "上海", "深圳", "杭州", "广州"],
        "skills": ["Python", "PyTorch", "TensorFlow", "Linux"],
        "salary": "20k-35k/月",
        "companies": "互联网大厂、AI 公司、独角兽",
        "national_strategic": False,
    },
    {
        "career": "算法工程师",
        "tags": ["机器学习", "算法", "数据挖掘"],
        "locations": ["北京", "上海", "深圳", "杭州", "南京", "成都"],
        "skills": ["Python", "C++", "数据结构与算法", "线性代数"],
        "salary": "18k-30k/月",
        "companies": "互联网大厂、广告平台、金融科技",
        "national_strategic": False,
    },
    {
        "career": "前端工程师",
        "tags": ["前端", "Web开发"],
        "locations": [],
        "skills": ["JavaScript/TypeScript", "HTML/CSS", "前端框架"],
        "salary": "10k-22k/月",
        "companies": "大部分互联网公司",
        "national_strategic": False,
    },
    # 国家战略重点领域岗位
    {
        "career": "芯片设计工程师（国家战略）",
        "tags": ["嵌入式", "算法", "硬件"],
        "locations": ["北京", "上海", "深圳", "成都", "西安", "杭州"],
        "skills": ["数字电路", "Verilog/VHDL", "芯片架构", "EDA 工具"],
        "salary": "20k-40k/月",
        "companies": "华为海思、中芯国际、紫光展锐、龙芯中科",
        "national_strategic": True,
        "strategic_field": "芯片自主",
    },
    {
        "career": "网络安全工程师（国家战略）",
        "tags": ["网络安全", "后端", "算法"],
        "locations": ["北京", "上海", "深圳", "杭州", "成都"],
        "skills": ["渗透测试", "密码学", "安全协议", "Python/C++"],
        "salary": "18k-35k/月",
        "companies": "360、绿盟科技、启明星辰、奇安信",
        "national_strategic": True,
        "strategic_field": "网络安全",
    },
    {
        "career": "航天软件工程师（国家战略）",
        "tags": ["嵌入式", "算法", "后端"],
        "locations": ["北京", "西安", "上海", "成都"],
        "skills": ["C/C++", "实时操作系统", "卫星通信", "软件测试"],
        "salary": "15k-30k/月",
        "companies": "中国航天科技集团、中国航天科工集团、航天科技控股",
        "national_strategic": True,
        "strategic_field": "航天科技",
    },
    {
        "career": "智慧电网工程师（国家战略）",
        "tags": ["嵌入式", "后端", "物联网"],
        "locations": ["北京", "上海", "南京", "武汉", "成都"],
        "skills": ["电力系统", "物联网", "大数据分析", "Python"],
        "salary": "12k-25k/月",
        "companies": "国家电网、南方电网、许继电气、国电南瑞",
        "national_strategic": True,
        "strategic_field": "能源电力",
    },
    {
        "career": "乡村振兴信息化工程师（国家战略）",
        "tags": ["后端", "前端", "数据分析"],
        "locations": ["全国"],
        "skills": ["Web 开发", "数据库", "云计算", "物联网"],
        "salary": "10k-20k/月",
        "companies": "政府信息化部门、农业科技公司、电商平台",
        "national_strategic": True,
        "strategic_field": "乡村振兴",
    },
]


def _is_global_location(locations: List[str]) -> bool:
    """Helper function to check if location list is global (empty or contains '全国')."""
    return not locations or locations == [LOCATION_GLOBAL]


def recommend_careers_by_interests_and_location(
    interests: List[str], location: str = "", prioritize_national_strategic: bool = False
) -> List[Dict[str, Any]]:
    """
    根据兴趣标签和地区推荐职业方向（放宽条件版）.

    - interests: 侧边栏选择的兴趣标签列表（即使只有 1 个也会尽量给出推荐）
    - location: 工作地区，如 "全国" / "北京" / "上海" 等
    - prioritize_national_strategic: 是否优先推荐国家战略领域岗位

    返回 List[Dict]，每个元素结构类似：
    {
        "career": "算法工程师",
        "skills": [...],
        "salary": "...",
        "companies": "...",
        "score": 3.5,
        "match_reason": "与你的兴趣 [机器学习, 算法] 有 2 个直接匹配；该职业在你选择的地区（北京）招聘较多"
    }
    """
    interests = [i.strip() for i in (interests or []) if i.strip()]
    location = (location or "").strip() or LOCATION_GLOBAL

    results: List[Dict[str, Any]] = []

    for c in CAREER_CONFIG:
        tags = c.get("tags", []) or []
        locs = c.get("locations", []) or []
        is_national_strategic = c.get("national_strategic", False)

        # 地区过滤：location 为 "全国" 时不过滤；否则只有当职业明确限制且不包含该城市时才排除
        if location != LOCATION_GLOBAL:
            if locs and not _is_global_location(locs) and (location not in locs):
                continue

        # 兴趣匹配：按交集个数计分
        if interests:
            overlap = len(set(interests) & set(tags))
        else:
            overlap = 0

        base_score = overlap

        # 没有兴趣标签时，给一个基础分，让系统仍然可以推荐通用岗位
        if not interests:
            base_score = 1
        # 有兴趣但完全没交集，先给 0 分，后面看兜底逻辑
        elif overlap == 0:
            base_score = 0

        # 地区加成：如果职业本身有地点列表且包含当前地点，可以 +0.5
        loc_bonus = 0.0
        if location != LOCATION_GLOBAL and locs and not _is_global_location(locs) and (location in locs):
            loc_bonus = 0.5

        # 国家战略领域加成
        strategic_bonus = 0.0
        if prioritize_national_strategic and is_national_strategic:
            strategic_bonus = NATIONAL_STRATEGIC_BONUS

        score = base_score + loc_bonus + strategic_bonus

        # 有一点分数就先纳入候选
        if score > 0:
            match_reason_parts = []
            if overlap > 0:
                match_reason_parts.append(
                    f"与你的兴趣标签 {interests} 有 {overlap} 个直接匹配"
                )
            else:
                match_reason_parts.append("与常见开发/数据岗位相关，适合作为通用方向")

            if location != LOCATION_GLOBAL:
                if locs and not _is_global_location(locs) and location in locs:
                    match_reason_parts.append(f"该职业在你选择的地区（{location}）招聘较多")
                elif _is_global_location(locs):
                    match_reason_parts.append("该职业对地区要求不高，全国大部分城市都有机会")
            else:
                match_reason_parts.append("你选择了『全国』，该职业在多地都有需求")
            
            if is_national_strategic:
                strategic_field = c.get("strategic_field", "国家重点领域")
                match_reason_parts.append(f"🇨🇳 国家战略重点领域：{strategic_field}")

            results.append(
                {
                    "career": c.get("career"),
                    "skills": c.get("skills", []),
                    "salary": c.get("salary", ""),
                    "companies": c.get("companies", ""),
                    "score": score,
                    "match_reason": "；".join(match_reason_parts),
                    "national_strategic": is_national_strategic,
                    "strategic_field": c.get("strategic_field", ""),
                }
            )

    # 如果严格匹配为空，但用户有兴趣标签，则走兜底逻辑
    if not results and interests:
        backup: List[Dict[str, Any]] = []

        for c in CAREER_CONFIG:
            tags = c.get("tags", []) or []
            if "机器学习" in interests or "算法" in interests:
                if ("机器学习" in tags) or ("算法" in tags) or ("数据分析" in tags):
                    backup.append(c)
            else:
                # 其他兴趣时，给一两个通用开发岗位兜底
                if c.get("career") in ("后端工程师", "前端工程师"):
                    backup.append(c)

        # 如果 backup 还是空，就直接把所有职业当兜底候选
        if not backup:
            backup = CAREER_CONFIG

        for c in backup:
            results.append(
                {
                    "career": c.get("career"),
                    "skills": c.get("skills", []),
                    "salary": c.get("salary", ""),
                    "companies": c.get("companies", ""),
                    "score": 0.5,
                    "match_reason": "未找到与你兴趣高度匹配的职业，推荐一些相关或通用的软件/数据岗位作为兜底方向",
                }
            )

    # 去重：同名 career 只保留得分最高的一条
    if results:
        best_by_name: Dict[str, Dict[str, Any]] = {}
        for r in results:
            name = r.get("career")
            if name not in best_by_name or r.get("score", 0) > best_by_name[name].get(
                "score", 0
            ):
                best_by_name[name] = r
        results = list(best_by_name.values())

        # 最后按 score 降序排列，截断前 6 个，和你原来的行为一致
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        results = results[:6]

    return results


def generate_learning_path_for_career(
    career: str, interests: List[str], current_level: str = "初级", agent: AIAgent = None
) -> str:
    agent = agent or st.session_state.get("_global_ai_agent", AIAgent())
    prompt = f"""请为一个{current_level}水平的学生，针对职位'{career}'和兴趣'{', '.join(interests)}'，生成一份详细的3-6个月学习路径。

要求：
1. 分阶段（基础、进阶、项目实践）
2. 每阶段具体学习内容和时间安排
3. 推荐的学习资源和开源项目
4. 实际项目建议（2-3个具体小项目）
5. 预期达到的能力目标
6. 面试准备建议

请用Markdown格式组织答案，力求清晰易懂。"""
    return agent.call(prompt, temperature=0.3, max_tokens=2400)


def recommend_projects_by_agent(
    interests: List[str], skills: List[str], target_career: str
) -> List[Dict[str, Any]]:
    agent: AIAgent = st.session_state.get("_global_ai_agent", AIAgent())

    prompt = f"""基于以下信息，推荐5-8个适合学习和实践的开源项目：

兴趣标签：{', '.join(interests)}
已掌握技能：{', '.join(skills) if skills else '初级开发者'}
目标职业：{target_career or '暂未定'}

要求：
1. 每个项目包括：项目名称、GitHub链接、简短描述、学习价值、难度等级、预期学习时间
2. 项目应该能帮助获得目标职业相关的技能
3. 项目难度应该循序渐进
4. 优先推荐对初中级开发者友好的项目

请用以下格式输出（JSON格式）：
```json
[
  {{
    "name": "项目名称",
    "url": "GitHub链接",
    "description": "简短描述",
    "learning_value": "学习价值",
    "difficulty": "easy/medium/hard",
    "estimated_time": "预期学习时间（周）",
    "tech_stack": ["技术栈"]
  }}
]只输出JSON，不要其他文字。"""
    result_text = agent.call(prompt, temperature=0.3, max_tokens=3000)

    try:
        import re

        json_match = re.search(r"```json\n(.*?)\n```", result_text, re.DOTALL)
        json_str = json_match.group(1) if json_match else result_text.strip()
        projects = json.loads(json_str)
        if isinstance(projects, list):
            return projects
    except Exception as e:
        logger.warning(f"Failed to parse agent projects recommendation: {e}")

    return [
        {
            "name": "Vue 3",
            "url": "https://github.com/vuejs/core",
            "description": "学习现代前端框架",
            "learning_value": "前端工程实战",
            "difficulty": "medium",
            "estimated_time": "8",
            "tech_stack": ["JavaScript", "Vue"],
        },
        {
            "name": "FastAPI",
            "url": "https://github.com/tiangolo/fastapi",
            "description": "高性能 Python Web 框架",
            "learning_value": "后端开发实战",
            "difficulty": "medium",
            "estimated_time": "6",
            "tech_stack": ["Python", "FastAPI"],
        },
    ]

def explain_course_recommendation(course: Dict[str, Any], user_interests: List[str], score: float) -> str:
    """
    Generate an explanation for why a course is recommended.
    
    Args:
        course: Course dictionary
        user_interests: List of user's interests
        score: Recommendation score
        
    Returns:
        Human-readable explanation string
    """
    explanations = []
    
    course_name = course.get("name", "该课程")
    
    # Interest matching
    matched_interests = []
    for interest in user_interests:
        if interest.lower() in course_name.lower() or interest.lower() in course.get("outline", "").lower():
            matched_interests.append(interest)
    
    if matched_interests:
        explanations.append(f"与您的兴趣【{', '.join(matched_interests)}】高度匹配")
    
    # Level appropriateness
    level = course.get("level", "")
    if level:
        level_desc = {
            "本科": "适合本科阶段学习",
            "研究生": "研究生深度课程",
            "价值引领类": "思政价值引领课程"
        }.get(level, f"{level}课程")
        explanations.append(level_desc)
    
    # Ideological value
    if course.get("ideological"):
        explanations.append("💝 价值引领课程，培养技术伦理")
    
    # Score-based description
    if score > 80:
        explanations.append("🌟 强烈推荐")
    elif score > 50:
        explanations.append("👍 推荐学习")
    
    if not explanations:
        return "根据您的学习规划推荐"
    
    return "；".join(explanations)


def explain_advisor_recommendation(advisor: Dict[str, Any], user_interests: List[str]) -> str:
    """
    Generate an explanation for why an advisor is recommended.
    
    Args:
        advisor: Advisor dictionary
        user_interests: List of user's interests
        
    Returns:
        Human-readable explanation string
    """
    explanations = []
    
    # Research area matching
    research = advisor.get("research", "")
    matched_interests = []
    for interest in user_interests:
        if interest.lower() in research.lower():
            matched_interests.append(interest)
    
    if matched_interests:
        explanations.append(f"研究方向与【{', '.join(matched_interests)}】相关")
    
    # National projects
    if advisor.get("national_projects"):
        explanations.append("🇨🇳 参与国家重大项目")
    
    # Department
    dept = advisor.get("department", "")
    if dept:
        explanations.append(f"{dept}")
    
    if not explanations:
        return "优秀导师推荐"
    
    return "；".join(explanations)


def explain_practice_recommendation(practice: Dict[str, Any], user_interests: List[str], social_score: float = 0) -> str:
    """
    Generate an explanation for why a practice resource is recommended.
    
    Args:
        practice: Practice resource dictionary
        user_interests: List of user's interests
        social_score: Social value score
        
    Returns:
        Human-readable explanation string
    """
    explanations = []
    
    # Interest matching
    practice_name = practice.get("name", "")
    practice_desc = practice.get("description", "")
    matched_interests = []
    for interest in user_interests:
        if interest.lower() in practice_name.lower() or interest.lower() in practice_desc.lower():
            matched_interests.append(interest)
    
    if matched_interests:
        explanations.append(f"与【{', '.join(matched_interests)}】相关")
    
    # Social value
    if social_score > 0:
        explanations.append("💝 具有社会价值或服务国家战略")
    
    # Type
    ptype = practice.get("type", "")
    if ptype:
        explanations.append(f"{ptype}类资源")
    
    if not explanations:
        return "实践资源推荐"
    
    return "；".join(explanations)


def explain_career_recommendation(career: Dict[str, Any], user_interests: List[str], location: str, is_strategic: bool = False) -> str:
    """
    Generate an explanation for why a career is recommended.
    
    Args:
        career: Career dictionary
        user_interests: List of user's interests
        location: User's preferred location
        is_strategic: Whether it's a national strategic position
        
    Returns:
        Human-readable explanation string
    """
    explanations = []
    
    # Interest matching
    career_name = career.get("name", "")
    matched_interests = []
    for interest in user_interests:
        if interest.lower() in career_name.lower():
            matched_interests.append(interest)
    
    if matched_interests:
        explanations.append(f"匹配技能【{', '.join(matched_interests)}】")
    
    # Strategic position
    if is_strategic:
        explanations.append("��🇳 国家战略重点岗位")
    
    # Location
    career_location = career.get("location", "")
    if career_location and location and location != "全国":
        if location in career_location:
            explanations.append(f"📍 符合期望地区【{location}】")
    
    # Demand
    demand = career.get("demand", "")
    if demand == "高":
        explanations.append("🔥 市场需求旺盛")
    
    if not explanations:
        return "职业发展推荐"
    
    return "；".join(explanations)

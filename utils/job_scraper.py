# -*- coding: utf-8 -*-
"""
Job scraper - 使用 SerpAPI 爬取真实职位数据
"""
import os
import json
import uuid
import time
import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

import requests

logger = logging.getLogger("job_scraper")

DATA_DIR = "data"
ALERTS_PATH = os.path.join(DATA_DIR, "job_alerts.json")
SEEN_PATH = os.path.join(DATA_DIR, "job_alerts_seen.json")

os.makedirs(DATA_DIR, exist_ok=True)


def _load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _uuid_safe(text: str) -> str:
    """Deterministic id from text."""
    import hashlib
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]


# ==================== SerpAPI 爬取 ====================
def scrape_with_serpapi(company_name: str, position: str = "Python", api_key: str = "") -> List[Dict[str, Any]]:
    """
    使用 SerpAPI 爬取职位信息
    """
    jobs = []
    
    if not api_key:
        logger.warning("SerpAPI 密钥未配置")
        return jobs
    
    try:
        # 搜索 Google Jobs（通过 SerpAPI）
        search_query = f"{company_name} {position} 招聘 site:lagou.com OR site:zhipin.com OR site:nowcoder.com"
        
        url = "https://serpapi.com/search"
        params = {
            "q": search_query,
            "engine": "google",
            "api_key": api_key,
            "num": 10,
            "tbm": "lcm"  # Local/Careers
        }
        
        logger.info(f"使用 SerpAPI 搜索: {search_query}")
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        # 解析 jobs_results
        job_results = data.get("jobs_results", []) or data.get("local_results", []) or []
        
        if not job_results:
            logger.debug("SerpAPI 未返回职位数据")
            return jobs
        
        for item in job_results[:20]:
            try:
                title = item.get("title", "") or item.get("job_title", "") or "Unknown"
                company = item.get("company", "") or company_name
                location = item.get("location", "") or ""
                description = item.get("description", "") or item.get("snippet", "") or ""
                url = item.get("link", "") or item.get("url", "")
                salary = item.get("salary", "") or ""
                
                if title and title != "Unknown":
                    job = {
                        "id": _uuid_safe(f"{company}_{title}_{location}"),
                        "title": title,
                        "company": company,
                        "salary": salary,
                        "location": location,
                        "snippet": description[:400],
                        "url": url,
                        "source": "serpapi",
                        "classification": "campus" if any(kw in title.lower() for kw in ["校招", "应届", "实习", "培训"]) else "social"
                    }
                    jobs.append(job)
                    logger.debug(f"解析职位: {title} @ {company}")
            except Exception as e:
                logger.debug(f"解析职位失败: {e}")
                continue
        
        logger.info(f"SerpAPI 获取 {len(jobs)} 个职位")
    
    except Exception as e:
        logger.warning(f"SerpAPI 爬取失败: {e}")
    
    return jobs


# ==================== Mock 数据（演示用） ====================
MOCK_JOBS = [
    {
        "id": "mock_001",
        "title": "Python 开发工程师",
        "company": "字节跳动",
        "salary": "25k-45k",
        "location": "北京",
        "snippet": "负责后端系统开发，要求熟悉 Python、Django、FastAPI 等框架，有大规模系统开发经验优先。",
        "url": "https://www.lagou.com/jobs/1234567.html",
        "source": "mock",
        "classification": "social"
    },
    {
        "id": "mock_002",
        "title": "2025 校招 - Python 开发工程师",
        "company": "字节跳动",
        "salary": "15k-25k",
        "location": "北京",
        "snippet": "校招职位，面向2025届毕业生招聘 Python 开发工程师，提供完整培训。",
        "url": "https://www.zhipin.com/jobs/1234567.html",
        "source": "mock",
        "classification": "campus"
    },
    {
        "id": "mock_003",
        "title": "前端开发工程师",
        "company": "阿里巴巴",
        "salary": "30k-50k",
        "location": "杭州",
        "snippet": "负责淘宝/天猫前端开发，要求熟悉 React、Vue、TypeScript 等，有电商平台经验优先。",
        "url": "https://www.lagou.com/jobs/7654321.html",
        "source": "mock",
        "classification": "social"
    },
    {
        "id": "mock_004",
        "title": "2025 校招 - 前端工程师",
        "company": "阿里巴巴",
        "salary": "18k-28k",
        "location": "杭州",
        "snippet": "校招职位，面向2025届毕业生招聘前端工程师，不限工作经验。",
        "url": "https://www.nowcoder.com/jobs/7654321.html",
        "source": "mock",
        "classification": "campus"
    },
    {
        "id": "mock_005",
        "title": "算法工程师",
        "company": "腾讯",
        "salary": "28k-48k",
        "location": "深圳",
        "snippet": "负责推荐系统、搜索算法优化，要求算法基础扎实，有竞赛经验优先。",
        "url": "https://www.lagou.com/jobs/2468101.html",
        "source": "mock",
        "classification": "social"
    },
    {
        "id": "mock_006",
        "title": "2025 校招 - 算法工程师",
        "company": "网易",
        "salary": "16k-26k",
        "location": "杭州",
        "snippet": "校招职位，面向2025届毕业生招聘算法工程师，欢迎应届毕业生投递。",
        "url": "https://www.zhipin.com/jobs/2468101.html",
        "source": "mock",
        "classification": "campus"
    },
    {
        "id": "mock_007",
        "title": "后端开发工程师",
        "company": "快手",
        "salary": "25k-40k",
        "location": "北京",
        "snippet": "负责短视频平台后端开发，要求 Java/Go/Python 至少一种精通，有高并发经验优先。",
        "url": "https://www.lagou.com/jobs/3691215.html",
        "source": "mock",
        "classification": "social"
    },
    {
        "id": "mock_008",
        "title": "2025 校招 - 后端工程师",
        "company": "快手",
        "salary": "17k-27k",
        "location": "北京",
        "snippet": "校招职位，面向2025届毕业生招聘后端工程师，提供完整技术培训。",
        "url": "https://www.nowcoder.com/jobs/3691215.html",
        "source": "mock",
        "classification": "campus"
    },
]


def scrape_mock_jobs(company_name: str, position: str = "") -> List[Dict[str, Any]]:
    """
    返回 Mock 职位数据用于演示
    """
    filtered = []
    for job in MOCK_JOBS:
        if company_name.lower() in job["company"].lower():
            if position and position.lower() not in job["title"].lower():
                continue
            filtered.append(job)
    
    logger.info(f"Mock 获取 {len(filtered)} 个 {company_name} 的职位")
    return filtered


# ==================== 统一爬取接口 ====================
def scrape_company_jobs(company_name: str, company_domain: Optional[str] = None, search_client=None, max_links: int = 6) -> List[Dict[str, Any]]:
    """
    主爬取函数：优先使用 SerpAPI，回退到 Mock 数据
    """
    all_jobs = []
    
    # 尝试 1: 使用 SerpAPI（若已配置 SEARCH_API_KEY）
    if search_client and hasattr(search_client, 'api_key'):
        try:
            jobs = scrape_with_serpapi(company_name, position=company_name, api_key=search_client.api_key)
            if jobs:
                all_jobs.extend(jobs)
                logger.info(f"SerpAPI 成功爬取 {len(jobs)} 个职位")
                return all_jobs
        except Exception as e:
            logger.warning(f"SerpAPI 爬取失败，尝试 Mock 数据: {e}")
    
    # 回退: 使用 Mock 数据
    logger.info("使用 Mock 职位数据进行演示")
    all_jobs = scrape_mock_jobs(company_name)
    
    return all_jobs


# ==================== 分类 ====================
CAMPUS_KEYWORDS = [
    "intern", "internship", "graduate", "campus", "校园", "校招", "实习", "应届",
    "campus program", "graduate program", "graduate trainee", "校招实习", "校园招聘",
    "fresh graduate", "新毕业生", "大学生", "student", "培训生"
]

def classify_job(job: Dict[str, Any]) -> str:
    """分类为校招或社招"""
    txt = (
        (job.get("title") or "") + " " +
        (job.get("snippet") or "") + " " +
        (job.get("location") or "")
    ).lower()
    
    for kw in CAMPUS_KEYWORDS:
        if kw.lower() in txt:
            return "campus"
    return "social"


# ==================== Alerts 持久化 ====================
def load_alerts() -> List[Dict[str, Any]]:
    return _load_json(ALERTS_PATH, [])


def save_alerts(alerts: List[Dict[str, Any]]):
    _save_json(ALERTS_PATH, alerts)


def load_seen() -> Dict[str, Any]:
    return _load_json(SEEN_PATH, {"seen": {}})


def save_seen(seen: Dict[str, Any]):
    _save_json(SEEN_PATH, seen)


def create_alert(user: str, company: str = "", company_domain: str = "", keywords: Optional[List[str]] = None, match_type: str = "both", channels: Dict[str, Any] = None) -> Dict[str, Any]:
    """创建职位提醒"""
    alerts = load_alerts()
    alert = {
        "id": str(uuid.uuid4()),
        "user": user,
        "company": company,
        "company_domain": company_domain,
        "keywords": keywords or [],
        "match_type": match_type,
        "channels": channels or {},
        "created_at": datetime.utcnow().isoformat(timespec="seconds")
    }
    alerts.insert(0, alert)
    save_alerts(alerts)
    return alert


def delete_alert(alert_id: str) -> bool:
    alerts = load_alerts()
    new = [a for a in alerts if a.get("id") != alert_id]
    if len(new) == len(alerts):
        return False
    save_alerts(new)
    return True


# ==================== 扫描与通知 ====================
def _job_matches_alert(job: Dict[str, Any], alert: Dict[str, Any]) -> bool:
    """检查职位是否匹配提醒条件"""
    # 公司匹配
    if alert.get("company"):
        company_match = (
            alert["company"].lower() in (job.get("company", "") or "").lower() or
            alert["company"].lower() in (job.get("title", "") or "").lower()
        )
        if not company_match:
            return False
    
    # 分类匹配
    jt = job.get("classification", classify_job(job))
    if alert.get("match_type") and alert.get("match_type") != "both":
        if alert["match_type"] != jt:
            return False
    
    # 关键词匹配
    kws = alert.get("keywords") or []
    if kws:
        text = (
            (job.get("title", "") or "") + " " +
            (job.get("snippet", "") or "") + " " +
            (job.get("location", "") or "")
        ).lower()
        if not any(kw.lower() in text for kw in kws):
            return False
    
    return True


def scan_alerts_and_notify(search_client=None, notify_fn: Optional[Callable[[Dict[str, Any], Dict[str, Any]], None]] = None):
    """扫描所有提醒，爬取职位并通知"""
    alerts = load_alerts()
    seen_store = load_seen()
    seen = seen_store.get("seen", {})
    new_seen = False

    for alert in alerts:
        company = alert.get("company", "")
        if not company:
            continue
        
        try:
            jobs = scrape_company_jobs(company, search_client=search_client, max_links=6)
        except Exception as e:
            logger.warning(f"爬取职位失败: {e}")
            jobs = []
        
        for job in jobs:
            jid = job.get("id") or uuid.uuid4().hex
            if jid in seen:
                continue
            
            if _job_matches_alert(job, alert):
                seen[jid] = {
                    "job": job,
                    "alert_id": alert.get("id"),
                    "time": datetime.utcnow().isoformat(timespec="seconds")
                }
                new_seen = True
                
                if notify_fn:
                    try:
                        notify_fn(job, alert)
                    except Exception as e:
                        logger.warning(f"通知失败: {e}")

    if new_seen:
        save_seen({"seen": seen})
    
    return True
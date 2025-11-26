# -*- coding: utf-8 -*-
"""
User profile management utilities.
Contains functions for loading, saving, and managing user profiles.
Supports PostgreSQL database storage or JSON file storage (based on DB_TYPE config).
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any

from shared.config import USER_PROFILE_PATH


def _get_db_store():
    """获取数据库存储实例"""
    try:
        from utils.database import get_data_store, is_using_database
        if is_using_database():
            return get_data_store()
    except ImportError:
        pass
    return None


def load_user_profiles() -> Dict[str, Dict[str, Any]]:
    """Load all user profiles from database or JSON file."""
    # 优先从数据库加载
    db_store = _get_db_store()
    if db_store:
        try:
            return db_store.get_all_user_profiles()
        except Exception as e:
            print(f"[profiles] 从数据库加载档案失败，回退到 JSON: {e}")
    
    # 从 JSON 文件加载
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(USER_PROFILE_PATH):
        return {}
    try:
        with open(USER_PROFILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_user_profiles(profiles: Dict[str, Dict[str, Any]]):
    """Save all user profiles to JSON file with atomic write."""
    os.makedirs("data", exist_ok=True)
    tmp = USER_PROFILE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)
    os.replace(tmp, USER_PROFILE_PATH)


def _normalize_repo_item(repo: Any) -> Dict[str, Any]:
    """Normalize a repository item to a consistent dictionary format."""
    if not repo:
        return {}
    if isinstance(repo, str):
        full_name = repo
        html_url = f"https://github.com/{full_name}" if full_name else ""
        return {
            "full_name": full_name,
            "html_url": html_url,
            "description": "",
            "language": "",
            "stargazers_count": 0,
        }
    if isinstance(repo, dict):
        full_name = repo.get("full_name") or repo.get("name") or ""
        html_url = repo.get("html_url") or (
            f"https://github.com/{full_name}" if full_name else ""
        )
        return {
            "full_name": full_name,
            "html_url": html_url,
            "description": repo.get("description") or "",
            "language": repo.get("language") or "",
            "stargazers_count": int(repo.get("stargazers_count", 0) or 0),
        }
    full_name = str(repo)
    html_url = f"https://github.com/{full_name}" if full_name else ""
    return {
        "full_name": full_name,
        "html_url": html_url,
        "description": "",
        "language": "",
        "stargazers_count": 0,
    }


def _normalize_learning_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a learning plan item to a consistent dictionary format."""
    if not item:
        return {}
    return {
        "id": item.get("id") or item.get("name"),
        "name": item.get("name", ""),
        "source": item.get("source", ""),
        "type": item.get("type", ""),
        "status": item.get("status", "todo") or "todo",
    }


def get_user_profile(username: str) -> Dict[str, Any]:
    """Get a user's profile with default values."""
    base = {
        "interests": [],
        "skills": [],
        "major": "",
        "stage": "",
        "target_career": "",
        "target_direction": "",
        "bio": "",
        "updated_at": "",
        "starred_repos": [],
        "finished_repos": [],
        "learning_plan": [],
    }
    
    # 优先从数据库获取
    db_store = _get_db_store()
    if db_store:
        try:
            db_profile = db_store.get_user_profile(username)
            if db_profile:
                prof = db_profile
                for k, v in base.items():
                    if k not in prof:
                        prof[k] = v
                prof["starred_repos"] = [
                    _normalize_repo_item(r) for r in prof.get("starred_repos", []) if r
                ]
                prof["finished_repos"] = [
                    _normalize_repo_item(r) for r in prof.get("finished_repos", []) if r
                ]
                prof["learning_plan"] = [
                    _normalize_learning_item(x) for x in prof.get("learning_plan", []) if x
                ]
                return prof
        except Exception as e:
            print(f"[profiles] 从数据库获取档案失败，回退到 JSON: {e}")
    
    # 从 JSON 获取
    profiles = load_user_profiles()
    prof = profiles.get(username, {})
    for k, v in base.items():
        if k not in prof:
            prof[k] = v
    prof["starred_repos"] = [
        _normalize_repo_item(r) for r in prof.get("starred_repos", []) if r
    ]
    prof["finished_repos"] = [
        _normalize_repo_item(r) for r in prof.get("finished_repos", []) if r
    ]
    prof["learning_plan"] = [
        _normalize_learning_item(x) for x in prof.get("learning_plan", []) if x
    ]
    return prof


def save_user_profile(username: str, profile: Dict[str, Any]):
    """Save a user's profile to the profiles file."""
    profiles = load_user_profiles()
    defaults = {
        "interests": [],
        "skills": [],
        "major": "",
        "stage": "",
        "target_career": "",
        "target_direction": "",
        "bio": "",
        "starred_repos": [],
        "finished_repos": [],
        "learning_plan": [],
    }
    for k, v in defaults.items():
        profile.setdefault(k, v)
    profile["starred_repos"] = [
        _normalize_repo_item(r) for r in profile.get("starred_repos", []) if r
    ]
    profile["finished_repos"] = [
        _normalize_repo_item(r) for r in profile.get("finished_repos", []) if r
    ]
    profile["learning_plan"] = [
        _normalize_learning_item(x) for x in profile.get("learning_plan", []) if x
    ]
    profile["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    # 优先保存到数据库
    db_store = _get_db_store()
    if db_store:
        try:
            if db_store.save_user_profile(username, profile):
                print(f"[profiles] 用户档案已保存到数据库: {username}")
                return
        except Exception as e:
            print(f"[profiles] 保存档案到数据库失败，回退到 JSON: {e}")
    
    # 回退到 JSON 文件
    profiles[username] = profile
    save_user_profiles(profiles)


def _sync_profile_to_session(username: str, session_state: Any):
    """Sync user profile data to Streamlit session state."""
    prof = get_user_profile(username)
    session_state["user_interests"] = prof.get("interests", [])
    session_state["starred_repos"] = prof.get("starred_repos", [])
    session_state["finished_repos"] = prof.get("finished_repos", [])
    session_state["my_learning_plan"] = prof.get("learning_plan", [])


def _update_profile_field(username: str, **fields):
    """Update specific fields in a user's profile."""
    profiles = load_user_profiles()
    prof = profiles.get(username, get_user_profile(username))
    for k, v in fields.items():
        prof[k] = v
    save_user_profile(username, prof)

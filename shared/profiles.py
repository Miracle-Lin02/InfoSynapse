# -*- coding: utf-8 -*-
"""
User profile management utilities.
Contains functions for loading, saving, and managing user profiles.
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any

from shared.config import USER_PROFILE_PATH


def load_user_profiles() -> Dict[str, Dict[str, Any]]:
    """Load all user profiles from JSON file."""
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
    profiles = load_user_profiles()
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

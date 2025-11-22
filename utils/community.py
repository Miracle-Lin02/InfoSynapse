# -*- coding: utf-8 -*-
"""
utils/community.py

A tiny forum storage using JSON file at data/community.json.
Thread structure:
{
  "id": "<uuid>",
  "title": "...",
  "created_by": "username/display_name",
  "created_at": "ISO",
  "posts": [
      {"id":"<uuid>", "author": "username", "author_name": "...", "content": "...", "time":"ISO"}
  ]
}

Provides create_thread, add_post, list_threads, get_thread, delete_post/thread (admin).
"""
import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

COMMUNITY_PATH = "data/community.json"

def _ensure():
    if not os.path.exists("data"):
        os.makedirs("data", exist_ok=True)
    if not os.path.exists(COMMUNITY_PATH):
        with open(COMMUNITY_PATH, "w", encoding="utf-8") as f:
            json.dump({"threads": []}, f, ensure_ascii=False, indent=2)

def _load() -> Dict[str, Any]:
    _ensure()
    with open(COMMUNITY_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {"threads": []}

def _save(data: Dict[str, Any]):
    _ensure()
    tmp = COMMUNITY_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, COMMUNITY_PATH)

def list_threads() -> List[Dict[str, Any]]:
    data = _load()
    return data.get("threads", []) or []

def get_thread(thread_id: str) -> Optional[Dict[str, Any]]:
    for t in list_threads():
        if t.get("id") == thread_id:
            return t
    return None

def create_thread(title: str, created_by: str, created_by_name: str, initial_post: str, category: str = "其他") -> Dict[str, Any]:
    data = _load()
    t = {
        "id": str(uuid.uuid4()),
        "title": title,
        "created_by": created_by,
        "created_by_name": created_by_name,
        "created_at": datetime.utcnow().isoformat(timespec="seconds"),
        "category": category,
        "posts": []
    }
    if initial_post:
        t["posts"].append({
            "id": str(uuid.uuid4()),
            "author": created_by,
            "author_name": created_by_name,
            "content": initial_post,
            "time": datetime.utcnow().isoformat(timespec="seconds")
        })
    data.setdefault("threads", []).insert(0, t)
    _save(data)
    return t

def add_post(thread_id: str, author: str, author_name: str, content: str) -> Optional[Dict[str, Any]]:
    data = _load()
    for t in data.get("threads", []):
        if t.get("id") == thread_id:
            post = {
                "id": str(uuid.uuid4()),
                "author": author,
                "author_name": author_name,
                "content": content,
                "time": datetime.utcnow().isoformat(timespec="seconds")
            }
            t.setdefault("posts", []).append(post)
            _save(data)
            return post
    return None

def delete_post(thread_id: str, post_id: str) -> bool:
    data = _load()
    for t in data.get("threads", []):
        if t.get("id") == thread_id:
            posts = t.get("posts", [])
            for i, p in enumerate(posts):
                if p.get("id") == post_id:
                    posts.pop(i)
                    _save(data)
                    return True
    return False

def delete_thread(thread_id: str) -> bool:
    data = _load()
    threads = data.get("threads", [])
    for i, t in enumerate(threads):
        if t.get("id") == thread_id:
            threads.pop(i)
            _save(data)
            return True
    return False

def toggle_like_thread(thread_id: str, username: str) -> bool:
    """Toggle like on a thread. Returns True if liked, False if unliked."""
    data = _load()
    for t in data.get("threads", []):
        if t.get("id") == thread_id:
            likes = t.setdefault("likes", [])
            if username in likes:
                likes.remove(username)
                _save(data)
                return False
            else:
                likes.append(username)
                _save(data)
                return True
    return False

def toggle_like_post(thread_id: str, post_id: str, username: str) -> bool:
    """Toggle like on a post. Returns True if liked, False if unliked."""
    data = _load()
    for t in data.get("threads", []):
        if t.get("id") == thread_id:
            for p in t.get("posts", []):
                if p.get("id") == post_id:
                    likes = p.setdefault("likes", [])
                    if username in likes:
                        likes.remove(username)
                        _save(data)
                        return False
                    else:
                        likes.append(username)
                        _save(data)
                        return True
    return False

def get_like_count(item: Dict[str, Any]) -> int:
    """Get the number of likes for a thread or post."""
    return len(item.get("likes", []))

def is_liked_by(item: Dict[str, Any], username: str) -> bool:
    """Check if an item is liked by a specific user."""
    return username in item.get("likes", [])
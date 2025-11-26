# -*- coding: utf-8 -*-
"""
User activity tracking: browsing history and bookmarks.
Supports PostgreSQL database or JSON file storage.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional


USER_ACTIVITY_DIR = "data/user_activity"


def _get_db_store():
    """获取数据库存储实例"""
    try:
        from utils.database import get_data_store, is_using_database
        if is_using_database():
            return get_data_store()
    except ImportError:
        pass
    return None


def _ensure_activity_dir():
    """Ensure the user activity directory exists."""
    os.makedirs(USER_ACTIVITY_DIR, exist_ok=True)


def _get_user_activity_path(username: str) -> str:
    """Get the path to a user's activity file."""
    _ensure_activity_dir()
    return os.path.join(USER_ACTIVITY_DIR, f"{username}_activity.json")


def _load_user_activity(username: str) -> Dict[str, Any]:
    """Load user activity data."""
    path = _get_user_activity_path(username)
    if not os.path.exists(path):
        return {
            "history": [],
            "bookmarks": []
        }
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "history": [],
            "bookmarks": []
        }


def _save_user_activity(username: str, activity: Dict[str, Any]):
    """Save user activity data."""
    path = _get_user_activity_path(username)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(activity, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def add_to_history(username: str, item_type: str, item_id: str, item_name: str, max_history: int = 50):
    """
    Add an item to user's browsing history.
    
    Args:
        username: Username
        item_type: Type of item ('course', 'advisor', 'practice', 'career', 'github')
        item_id: Unique identifier for the item
        item_name: Display name of the item
        max_history: Maximum number of history items to keep
    """
    # 优先保存到数据库
    db_store = _get_db_store()
    if db_store:
        try:
            db_store.add_user_activity(username, 'history', item_type, item_id, item_name)
            return
        except Exception as e:
            print(f"[user_activity] 保存浏览历史到数据库失败: {e}")
    
    # 回退到 JSON
    activity = _load_user_activity(username)
    
    # Remove if already exists (to update timestamp)
    activity["history"] = [
        h for h in activity["history"]
        if not (h.get("type") == item_type and h.get("id") == item_id)
    ]
    
    # Add to front
    activity["history"].insert(0, {
        "type": item_type,
        "id": item_id,
        "name": item_name,
        "timestamp": datetime.now().isoformat()
    })
    
    # Trim to max_history
    activity["history"] = activity["history"][:max_history]
    
    _save_user_activity(username, activity)


def get_history(username: str, limit: Optional[int] = 20) -> List[Dict[str, Any]]:
    """
    Get user's browsing history.
    
    Args:
        username: Username
        limit: Maximum number of items to return
        
    Returns:
        List of history items
    """
    # 优先从数据库获取
    db_store = _get_db_store()
    if db_store:
        try:
            activity = db_store.get_user_activity(username)
            history = activity.get('history', [])
            if limit:
                history = history[:limit]
            return history
        except Exception as e:
            print(f"[user_activity] 从数据库获取浏览历史失败: {e}")
    
    # 回退到 JSON
    activity = _load_user_activity(username)
    history = activity.get("history", [])
    if limit:
        history = history[:limit]
    return history


def add_bookmark(username: str, item_type: str, item_id: str, item_name: str) -> bool:
    """
    Add an item to user's bookmarks.
    
    Args:
        username: Username
        item_type: Type of item
        item_id: Unique identifier
        item_name: Display name
        
    Returns:
        True if added, False if already exists
    """
    # 优先保存到数据库
    db_store = _get_db_store()
    if db_store:
        try:
            # Check if already bookmarked
            activity = db_store.get_user_activity(username)
            for bookmark in activity.get('bookmarks', []):
                if bookmark.get("type") == item_type and bookmark.get("id") == item_id:
                    return False
            
            db_store.add_user_activity(username, 'bookmark', item_type, item_id, item_name)
            return True
        except Exception as e:
            print(f"[user_activity] 保存收藏到数据库失败: {e}")
    
    # 回退到 JSON
    activity = _load_user_activity(username)
    
    # Check if already bookmarked
    for bookmark in activity.get("bookmarks", []):
        if bookmark.get("type") == item_type and bookmark.get("id") == item_id:
            return False
    
    # Add bookmark
    activity.setdefault("bookmarks", []).append({
        "type": item_type,
        "id": item_id,
        "name": item_name,
        "timestamp": datetime.now().isoformat()
    })
    
    _save_user_activity(username, activity)
    return True


def remove_bookmark(username: str, item_type: str, item_id: str) -> bool:
    """
    Remove an item from user's bookmarks.
    
    Returns:
        True if removed, False if not found
    """
    # 优先从数据库删除
    db_store = _get_db_store()
    if db_store:
        try:
            return db_store.remove_user_activity(username, 'bookmark', item_type, item_id)
        except Exception as e:
            print(f"[user_activity] 从数据库删除收藏失败: {e}")
    
    # 回退到 JSON
    activity = _load_user_activity(username)
    
    bookmarks = activity.get("bookmarks", [])
    new_bookmarks = [
        b for b in bookmarks
        if not (b.get("type") == item_type and b.get("id") == item_id)
    ]
    
    if len(new_bookmarks) == len(bookmarks):
        return False  # Not found
    
    activity["bookmarks"] = new_bookmarks
    _save_user_activity(username, activity)
    return True


def get_bookmarks(username: str) -> List[Dict[str, Any]]:
    """Get user's bookmarks."""
    # 优先从数据库获取
    db_store = _get_db_store()
    if db_store:
        try:
            activity = db_store.get_user_activity(username)
            return activity.get('bookmarks', [])
        except Exception as e:
            print(f"[user_activity] 从数据库获取收藏失败: {e}")
    
    # 回退到 JSON
    activity = _load_user_activity(username)
    return activity.get("bookmarks", [])


def is_bookmarked(username: str, item_type: str, item_id: str) -> bool:
    """Check if an item is bookmarked."""
    bookmarks = get_bookmarks(username)
    for bookmark in bookmarks:
        if bookmark.get("type") == item_type and bookmark.get("id") == item_id:
            return True
    return False

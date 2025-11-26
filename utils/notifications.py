# -*- coding: utf-8 -*-
"""
utils/notifications.py

Notification system for InfoSynapse platform.
Supports: new reply notifications, admin announcements, mentions.
Storage: PostgreSQL database or per-user JSON files in data/notifications/
"""
import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any

NOTIFICATIONS_DIR = "data/notifications"


def _get_db_store():
    """获取数据库存储实例"""
    try:
        from utils.database import get_data_store, is_using_database
        if is_using_database():
            return get_data_store()
    except ImportError:
        pass
    return None


def _ensure_dir():
    """Ensure notifications directory exists."""
    if not os.path.exists(NOTIFICATIONS_DIR):
        os.makedirs(NOTIFICATIONS_DIR, exist_ok=True)

def _get_user_file(username: str) -> str:
    """Get path to user's notification file."""
    _ensure_dir()
    return os.path.join(NOTIFICATIONS_DIR, f"{username}_notifications.json")

def _load_notifications(username: str) -> List[Dict[str, Any]]:
    """Load notifications for a user."""
    filepath = _get_user_file(username)
    if not os.path.exists(filepath):
        return []
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("notifications", [])
    except Exception:
        return []

def _save_notifications(username: str, notifications: List[Dict[str, Any]]):
    """Save notifications for a user."""
    filepath = _get_user_file(username)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({"notifications": notifications}, f, ensure_ascii=False, indent=2)

def add_notification(username: str, notification_type: str, title: str, 
                     message: str, link: str = "", metadata: Dict = None):
    """
    Add a notification for a user.
    
    Args:
        username: Target user
        notification_type: Type of notification (reply, mention, announcement, etc.)
        title: Notification title
        message: Notification message
        link: Optional link to related content
        metadata: Optional additional data
    """
    notification = {
        "id": str(uuid.uuid4()),
        "type": notification_type,
        "title": title,
        "message": message,
        "link": link,
        "metadata": metadata or {},
        "created_at": datetime.now().isoformat(),
        "read": False
    }
    
    # 优先保存到数据库
    db_store = _get_db_store()
    if db_store:
        try:
            if db_store.add_notification(username, notification):
                return notification
        except Exception as e:
            print(f"[notifications] 保存通知到数据库失败: {e}")
    
    # 回退到 JSON
    notifications = _load_notifications(username)
    notifications.insert(0, notification)  # Most recent first
    
    # Keep only last 100 notifications
    if len(notifications) > 100:
        notifications = notifications[:100]
    
    _save_notifications(username, notifications)
    return notification

def get_notifications(username: str, unread_only: bool = False, limit: int = None) -> List[Dict[str, Any]]:
    """
    Get notifications for a user.
    
    Args:
        username: Target user
        unread_only: Only return unread notifications
        limit: Maximum number of notifications to return
    
    Returns:
        List of notification dictionaries
    """
    # 优先从数据库获取
    db_store = _get_db_store()
    if db_store:
        try:
            return db_store.get_notifications(username, unread_only, limit)
        except Exception as e:
            print(f"[notifications] 从数据库获取通知失败: {e}")
    
    # 回退到 JSON
    notifications = _load_notifications(username)
    
    if unread_only:
        notifications = [n for n in notifications if not n.get("read", False)]
    
    if limit:
        notifications = notifications[:limit]
    
    return notifications

def get_unread_count(username: str) -> int:
    """Get count of unread notifications for a user."""
    # 优先从数据库获取
    db_store = _get_db_store()
    if db_store:
        try:
            notifications = db_store.get_notifications(username, unread_only=True)
            return len(notifications)
        except Exception as e:
            print(f"[notifications] 获取未读数量失败: {e}")
    
    # 回退到 JSON
    notifications = _load_notifications(username)
    return sum(1 for n in notifications if not n.get("read", False))

def mark_as_read(username: str, notification_id: str = None):
    """
    Mark notification(s) as read.
    
    Args:
        username: Target user
        notification_id: Specific notification ID, or None for all
    """
    # 优先使用数据库
    db_store = _get_db_store()
    if db_store:
        try:
            if notification_id:
                db_store.mark_notification_read(notification_id=notification_id)
            else:
                db_store.mark_notification_read(username=username)
            return
        except Exception as e:
            print(f"[notifications] 标记已读失败: {e}")
    
    # 回退到 JSON
    notifications = _load_notifications(username)
    
    if notification_id:
        for notif in notifications:
            if notif["id"] == notification_id:
                notif["read"] = True
                break
    else:
        # Mark all as read
        for notif in notifications:
            notif["read"] = True
    
    _save_notifications(username, notifications)

def clear_notifications(username: str):
    """Clear all notifications for a user."""
    # 优先使用数据库
    db_store = _get_db_store()
    if db_store:
        try:
            db_store.clear_notifications(username)
            return
        except Exception as e:
            print(f"[notifications] 清空通知失败: {e}")
    
    # 回退到 JSON
    _save_notifications(username, [])

def send_announcement(title: str, message: str, all_users: List[str]):
    """
    Send announcement to all users.
    
    Args:
        title: Announcement title
        message: Announcement message
        all_users: List of all usernames
    """
    for username in all_users:
        add_notification(
            username=username,
            notification_type="announcement",
            title=title,
            message=message,
            link=""
        )

def notify_new_reply(thread_id: str, thread_title: str, author: str, 
                     content_preview: str, participants: List[str]):
    """
    Notify thread participants about a new reply.
    
    Args:
        thread_id: Thread ID
        thread_title: Thread title
        author: Reply author username
        content_preview: Preview of reply content
        participants: List of usernames to notify (excludes author)
    """
    for username in participants:
        if username != author:  # Don't notify the author of their own reply
            add_notification(
                username=username,
                notification_type="reply",
                title=f"新回复: {thread_title}",
                message=f"{author} 回复了您参与的话题: {content_preview[:50]}...",
                link=f"thread_{thread_id}",
                metadata={"thread_id": thread_id, "author": author}
            )

def notify_mention(mentioned_user: str, author: str, context: str, link: str = ""):
    """
    Notify a user they were mentioned.
    
    Args:
        mentioned_user: Username that was mentioned
        author: User who mentioned them
        context: Context of the mention
        link: Link to the content
    """
    add_notification(
        username=mentioned_user,
        notification_type="mention",
        title="有人提到了你",
        message=f"{author} 在讨论中提到了你: {context[:50]}...",
        link=link,
        metadata={"author": author}
    )

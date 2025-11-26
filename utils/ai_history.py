# -*- coding: utf-8 -*-
"""
AI conversation history management.
Saves and retrieves user's AI conversation history across different tabs and sessions.
"""

import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

AI_HISTORY_DIR = "data/ai_history"


def _ensure_dir():
    """Ensure AI history directory exists."""
    os.makedirs(AI_HISTORY_DIR, exist_ok=True)


def _get_user_history_path(username: str) -> str:
    """Get path to user's AI history file."""
    _ensure_dir()
    return os.path.join(AI_HISTORY_DIR, f"{username}_ai_history.json")


def _load_user_history(username: str) -> Dict[str, Any]:
    """Load user's AI conversation history."""
    path = _get_user_history_path(username)
    if not os.path.exists(path):
        return {
            "conversations": [],
            "career_chats": [],
            "tab_helpers": {}
        }
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "conversations": [],
            "career_chats": [],
            "tab_helpers": {}
        }


def _save_user_history(username: str, history: Dict[str, Any]):
    """Save user's AI conversation history."""
    path = _get_user_history_path(username)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def save_conversation(username: str, conversation_type: str, 
                      title: str, messages: List[Dict[str, str]], 
                      context: Optional[Dict[str, Any]] = None,
                      max_history: int = 50) -> str:
    """
    Save a conversation to user's history.
    
    Args:
        username: Username
        conversation_type: Type of conversation ('career_chat', 'tab_helper', 'general')
        title: Conversation title
        messages: List of message dicts with 'role' and 'content' keys
        context: Optional context data (interests, stage, etc.)
        max_history: Maximum number of conversations to keep
    
    Returns:
        Conversation ID
    """
    history = _load_user_history(username)
    
    conv_id = str(uuid.uuid4())[:8]
    conversation = {
        "id": conv_id,
        "type": conversation_type,
        "title": title,
        "messages": messages,
        "context": context or {},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    history["conversations"].insert(0, conversation)
    
    # Trim to max_history
    if len(history["conversations"]) > max_history:
        history["conversations"] = history["conversations"][:max_history]
    
    _save_user_history(username, history)
    return conv_id


def get_conversations(username: str, conversation_type: Optional[str] = None, 
                      limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get user's conversation history.
    
    Args:
        username: Username
        conversation_type: Filter by type (None for all)
        limit: Maximum number of conversations to return
    
    Returns:
        List of conversation dicts
    """
    history = _load_user_history(username)
    conversations = history.get("conversations", [])
    
    if conversation_type:
        conversations = [c for c in conversations if c.get("type") == conversation_type]
    
    return conversations[:limit]


def get_conversation_by_id(username: str, conv_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific conversation by ID."""
    history = _load_user_history(username)
    for conv in history.get("conversations", []):
        if conv.get("id") == conv_id:
            return conv
    return None


def update_conversation(username: str, conv_id: str, 
                        messages: List[Dict[str, str]], 
                        title: Optional[str] = None):
    """
    Update an existing conversation with new messages.
    
    Args:
        username: Username
        conv_id: Conversation ID
        messages: Updated messages list
        title: Optional new title
    """
    history = _load_user_history(username)
    
    for conv in history.get("conversations", []):
        if conv.get("id") == conv_id:
            conv["messages"] = messages
            conv["updated_at"] = datetime.now().isoformat()
            if title:
                conv["title"] = title
            break
    
    _save_user_history(username, history)


def delete_conversation(username: str, conv_id: str) -> bool:
    """
    Delete a conversation from history.
    
    Returns:
        True if deleted, False if not found
    """
    history = _load_user_history(username)
    
    original_len = len(history.get("conversations", []))
    history["conversations"] = [
        c for c in history.get("conversations", [])
        if c.get("id") != conv_id
    ]
    
    if len(history["conversations"]) < original_len:
        _save_user_history(username, history)
        return True
    return False


def clear_all_history(username: str):
    """Clear all conversation history for a user."""
    history = {
        "conversations": [],
        "career_chats": [],
        "tab_helpers": {}
    }
    _save_user_history(username, history)


def save_tab_helper_response(username: str, tab_key: str, 
                              question: str, answer: str):
    """
    Save a tab helper response.
    
    Args:
        username: Username
        tab_key: Tab identifier
        question: User's question
        answer: AI's answer
    """
    history = _load_user_history(username)
    
    if "tab_helpers" not in history:
        history["tab_helpers"] = {}
    
    if tab_key not in history["tab_helpers"]:
        history["tab_helpers"][tab_key] = []
    
    history["tab_helpers"][tab_key].insert(0, {
        "question": question,
        "answer": answer,
        "timestamp": datetime.now().isoformat()
    })
    
    # Keep only last 10 per tab
    history["tab_helpers"][tab_key] = history["tab_helpers"][tab_key][:10]
    
    # Also save as a conversation for unified display
    conv_id = str(uuid.uuid4())[:8]
    tab_names = {
        "profile": "个人主页",
        "courses": "课程",
        "advisors": "导师",
        "practice": "校内实践",
        "career_tab": "求职",
        "github": "GitHub项目",
        "community": "社区",
        "mixed": "综合推荐",
        "admin": "管理"
    }
    tab_display_name = tab_names.get(tab_key, tab_key)
    
    conversation = {
        "id": conv_id,
        "type": "tab_helper",
        "title": f"{tab_display_name}助手咨询",
        "messages": [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ],
        "context": {"tab": tab_key},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    if "conversations" not in history:
        history["conversations"] = []
    
    history["conversations"].insert(0, conversation)
    
    # Keep only last 50 conversations
    if len(history["conversations"]) > 50:
        history["conversations"] = history["conversations"][:50]
    
    _save_user_history(username, history)


def get_tab_helper_history(username: str, tab_key: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Get tab helper response history for a specific tab."""
    history = _load_user_history(username)
    tab_history = history.get("tab_helpers", {}).get(tab_key, [])
    return tab_history[:limit]


def get_recent_conversation_history(username: str, limit: int = 5) -> str:
    """
    Get recent conversation history as a formatted string for AI context.
    This helps AI remember what was discussed before.
    
    Args:
        username: Username
        limit: Maximum number of recent conversations to include
    
    Returns:
        Formatted string of recent conversations
    """
    history = _load_user_history(username)
    conversations = history.get("conversations", [])[:limit]
    
    if not conversations:
        return ""
    
    lines = ["【以下是用户最近的对话记录，请参考以保持对话连贯性】"]
    
    for conv in conversations:
        title = conv.get("title", "未命名对话")
        created = conv.get("created_at", "")[:10]  # Just date
        messages = conv.get("messages", [])
        
        if messages:
            lines.append(f"\n--- {title} ({created}) ---")
            for msg in messages[-4:]:  # Only last 4 messages per conversation
                role = "用户" if msg.get("role") == "user" else "AI助手"
                content = msg.get("content", "")[:200]  # Truncate long messages
                if len(msg.get("content", "")) > 200:
                    content += "..."
                lines.append(f"{role}: {content}")
    
    lines.append("\n【以上是历史对话，请基于此继续为用户提供帮助】\n")
    return "\n".join(lines)


def get_conversation_stats(username: str) -> Dict[str, int]:
    """
    Get statistics about user's conversation history.
    
    Returns:
        Dict with counts by type and total
    """
    history = _load_user_history(username)
    conversations = history.get("conversations", [])
    
    stats = {
        "total": len(conversations),
        "career_chat": 0,
        "tab_helper": 0,
        "general": 0
    }
    
    for conv in conversations:
        conv_type = conv.get("type", "general")
        if conv_type in stats:
            stats[conv_type] += 1
        else:
            stats["general"] += 1
    
    return stats

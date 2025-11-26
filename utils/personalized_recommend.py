# -*- coding: utf-8 -*-
"""
Personalized recommendation module.
Optimizes AI recommendations based on user browsing history, feedback, and preferences.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter

from utils.user_activity import get_history, get_bookmarks


FEEDBACK_DIR = "data/user_feedback"


def _ensure_dir():
    """Ensure feedback directory exists."""
    os.makedirs(FEEDBACK_DIR, exist_ok=True)


def _get_user_feedback_path(username: str) -> str:
    """Get path to user's feedback file."""
    _ensure_dir()
    return os.path.join(FEEDBACK_DIR, f"{username}_feedback.json")


def _load_user_feedback(username: str) -> Dict[str, Any]:
    """Load user feedback data."""
    path = _get_user_feedback_path(username)
    if not os.path.exists(path):
        return {
            "career_likes": [],
            "career_dislikes": [],
            "course_ratings": {},
            "advisor_ratings": {},
            "practice_ratings": {},
            "skill_preferences": {},
            "last_updated": None
        }
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "career_likes": [],
            "career_dislikes": [],
            "course_ratings": {},
            "advisor_ratings": {},
            "practice_ratings": {},
            "skill_preferences": {},
            "last_updated": None
        }


def _save_user_feedback(username: str, feedback: Dict[str, Any]):
    """Save user feedback data."""
    path = _get_user_feedback_path(username)
    feedback["last_updated"] = datetime.now().isoformat()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(feedback, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def add_career_feedback(username: str, career_name: str, is_like: bool):
    """
    Record user feedback on a career recommendation.
    
    Args:
        username: Username
        career_name: Name of the career
        is_like: True for like, False for dislike
    """
    feedback = _load_user_feedback(username)
    
    if is_like:
        if career_name not in feedback["career_likes"]:
            feedback["career_likes"].append(career_name)
        # Remove from dislikes if previously disliked
        if career_name in feedback["career_dislikes"]:
            feedback["career_dislikes"].remove(career_name)
    else:
        if career_name not in feedback["career_dislikes"]:
            feedback["career_dislikes"].append(career_name)
        # Remove from likes if previously liked
        if career_name in feedback["career_likes"]:
            feedback["career_likes"].remove(career_name)
    
    _save_user_feedback(username, feedback)


def add_item_rating(username: str, item_type: str, item_id: str, rating: int):
    """
    Add rating for a course/advisor/practice item.
    
    Args:
        username: Username
        item_type: 'course', 'advisor', or 'practice'
        item_id: Item identifier
        rating: Rating value (1-5)
    """
    feedback = _load_user_feedback(username)
    
    key = f"{item_type}_ratings"
    if key not in feedback:
        feedback[key] = {}
    
    feedback[key][item_id] = {
        "rating": rating,
        "timestamp": datetime.now().isoformat()
    }
    
    _save_user_feedback(username, feedback)


def add_skill_preference(username: str, skill: str, weight: float = 1.0):
    """
    Record user's preference for a skill.
    
    Args:
        username: Username
        skill: Skill name
        weight: Preference weight (higher = more preferred)
    """
    feedback = _load_user_feedback(username)
    
    current = feedback.get("skill_preferences", {}).get(skill, 0)
    feedback["skill_preferences"][skill] = current + weight
    
    _save_user_feedback(username, feedback)


def analyze_user_preferences(username: str, 
                              profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analyze user's preferences based on bookmarks/favorites and feedback.
    
    Args:
        username: Username
        profile: Optional user profile data
    
    Returns:
        Dict with preference analysis including:
        - preferred_categories: Categories based on bookmarks
        - preferred_skills: Skills user is interested in
        - career_tendencies: Career directions user tends towards
        - activity_level: Based on bookmarks and feedback
    """
    bookmarks = get_bookmarks(username)
    feedback = _load_user_feedback(username)
    
    # Analyze bookmarks to determine preferred categories
    type_counts = Counter()
    for item in bookmarks:
        type_counts[item.get("type", "unknown")] += 1
    
    # Most bookmarked categories
    preferred_categories = [cat for cat, _ in type_counts.most_common(5)]
    
    # Analyze skills from bookmarked items and liked careers
    skill_mentions = Counter()
    
    # Extract skills from bookmarked items
    for bookmark in bookmarks:
        item_name = bookmark.get("name", "").lower()
        # Infer skills from bookmark names
        if "python" in item_name:
            skill_mentions["Python"] += 2
        if "java" in item_name and "javascript" not in item_name:
            skill_mentions["Java"] += 2
        if "javascript" in item_name or "js" in item_name:
            skill_mentions["JavaScript"] += 2
        if "react" in item_name:
            skill_mentions["React"] += 2
        if "vue" in item_name:
            skill_mentions["Vue"] += 2
        if "机器学习" in item_name or "ml" in item_name:
            skill_mentions["机器学习"] += 2
        if "深度学习" in item_name or "deep" in item_name:
            skill_mentions["深度学习"] += 2
        if "算法" in item_name:
            skill_mentions["算法"] += 2
        if "数据库" in item_name or "sql" in item_name:
            skill_mentions["数据库"] += 2
    
    # Extract skills from liked careers
    liked_careers = feedback.get("career_likes", [])
    for career in liked_careers:
        # Common skills associated with careers
        career_lower = career.lower()
        if "后端" in career_lower or "backend" in career_lower:
            for skill in ["Python", "Java", "Go", "数据库", "微服务"]:
                skill_mentions[skill] += 2
        if "前端" in career_lower or "frontend" in career_lower:
            for skill in ["JavaScript", "React", "Vue", "HTML/CSS", "TypeScript"]:
                skill_mentions[skill] += 2
        if "算法" in career_lower or "ai" in career_lower or "机器学习" in career_lower:
            for skill in ["Python", "机器学习", "深度学习", "TensorFlow", "PyTorch"]:
                skill_mentions[skill] += 2
        if "嵌入式" in career_lower:
            for skill in ["C/C++", "嵌入式", "单片机", "RTOS"]:
                skill_mentions[skill] += 2
    
    # Add explicit skill preferences from feedback
    for skill, weight in feedback.get("skill_preferences", {}).items():
        skill_mentions[skill] += int(weight)
    
    # Add skills from user profile
    if profile:
        for skill in profile.get("skills", []):
            skill_mentions[skill] += 1
        for interest in profile.get("interests", []):
            skill_mentions[interest] += 1
    
    preferred_skills = [skill for skill, _ in skill_mentions.most_common(10)]
    
    # Career tendencies
    career_tendencies = {
        "liked": liked_careers[:5],
        "disliked": feedback.get("career_dislikes", [])[:5],
        "national_strategic": False  # Will be set based on liked careers
    }
    
    # Check if user tends towards national strategic positions
    national_keywords = ["国企", "央企", "航天", "芯片", "能源", "乡村", "基层"]
    for career in liked_careers:
        if any(kw in career for kw in national_keywords):
            career_tendencies["national_strategic"] = True
            break
    
    # Activity level based on bookmarks and feedback
    total_activity = len(bookmarks) + len(liked_careers) + len(feedback.get("career_dislikes", []))
    if total_activity > 10:
        activity_level = "high"
    elif total_activity > 3:
        activity_level = "medium"
    else:
        activity_level = "low"
    
    return {
        "preferred_categories": preferred_categories,
        "preferred_skills": preferred_skills,
        "career_tendencies": career_tendencies,
        "activity_level": activity_level,
        "bookmark_count": len(bookmarks)
    }


def _is_recent(timestamp_str: Optional[str], days: int = 7) -> bool:
    """Check if a timestamp is within the specified number of days."""
    if not timestamp_str:
        return False
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        cutoff = datetime.now() - timedelta(days=days)
        # Handle timezone-aware vs naive datetime comparison
        if timestamp.tzinfo is not None:
            cutoff = cutoff.replace(tzinfo=timestamp.tzinfo)
        return timestamp > cutoff
    except Exception:
        return False


def get_personalized_boost_keywords(username: str) -> List[str]:
    """
    Get keywords that should be boosted in recommendations for this user.
    
    Returns:
        List of keywords/skills to prioritize
    """
    prefs = analyze_user_preferences(username)
    
    keywords = []
    
    # Add preferred skills
    keywords.extend(prefs.get("preferred_skills", []))
    
    # Add keywords from liked careers
    for career in prefs.get("career_tendencies", {}).get("liked", []):
        # Extract potential keywords from career name
        if "后端" in career or "服务" in career:
            keywords.extend(["后端", "服务端", "API"])
        if "前端" in career or "界面" in career:
            keywords.extend(["前端", "UI", "用户界面"])
        if "算法" in career or "AI" in career:
            keywords.extend(["算法", "AI", "模型"])
    
    return list(set(keywords))  # Remove duplicates


def get_recommendation_weights(username: str, 
                                base_weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    """
    Get personalized recommendation weights based on user activity.
    
    Args:
        username: Username
        base_weights: Optional base weights to modify
    
    Returns:
        Dict with modified weights
    """
    if base_weights is None:
        base_weights = {
            "INTEREST_NAME_WEIGHT": 30.0,
            "INTEREST_DESC_WEIGHT": 20.0,
            "KB_BASE_SCORE": 10.0
        }
    
    prefs = analyze_user_preferences(username)
    weights = base_weights.copy()
    
    # Adjust based on activity level
    activity_level = prefs.get("activity_level", "medium")
    if activity_level == "high":
        # More active users get more diverse recommendations
        weights["INTEREST_DESC_WEIGHT"] = weights.get("INTEREST_DESC_WEIGHT", 20.0) * 1.2
    elif activity_level == "low":
        # Less active users get safer, more conservative recommendations
        weights["KB_BASE_SCORE"] = weights.get("KB_BASE_SCORE", 10.0) * 1.3
    
    # Adjust based on preferred categories
    categories = prefs.get("preferred_categories", [])
    if "career" in categories or "github" in categories:
        # User interested in career/projects
        weights["INTEREST_NAME_WEIGHT"] = weights.get("INTEREST_NAME_WEIGHT", 30.0) * 1.1
    
    return weights


def get_anti_recommendations(username: str) -> List[str]:
    """
    Get items/keywords that should be deprioritized based on negative feedback.
    
    Returns:
        List of keywords to avoid in recommendations
    """
    feedback = _load_user_feedback(username)
    
    anti_keywords = []
    
    # Add disliked career keywords
    for career in feedback.get("career_dislikes", []):
        anti_keywords.append(career)
    
    # Add low-rated items
    for item_type in ["course", "advisor", "practice"]:
        ratings = feedback.get(f"{item_type}_ratings", {})
        for item_id, rating_data in ratings.items():
            if rating_data.get("rating", 3) <= 2:
                anti_keywords.append(item_id)
    
    return anti_keywords


def generate_personalized_prompt_context(username: str) -> str:
    """
    Generate context string for AI prompts based on user's preferences.
    
    Returns:
        String to append to AI prompts for personalization
    """
    prefs = analyze_user_preferences(username)
    
    context_parts = []
    
    # Add preferred skills
    if prefs.get("preferred_skills"):
        skills = ", ".join(prefs["preferred_skills"][:5])
        context_parts.append(f"该用户对以下技能感兴趣：{skills}")
    
    # Add career tendencies
    liked = prefs.get("career_tendencies", {}).get("liked", [])
    if liked:
        careers = ", ".join(liked[:3])
        context_parts.append(f"该用户喜欢的职业方向：{careers}")
    
    # Add national strategic preference
    if prefs.get("career_tendencies", {}).get("national_strategic"):
        context_parts.append("该用户倾向于国家战略领域/国企央企方向")
    
    # Add disliked directions
    disliked = prefs.get("career_tendencies", {}).get("disliked", [])
    if disliked:
        avoid = ", ".join(disliked[:3])
        context_parts.append(f"请避免推荐以下方向：{avoid}")
    
    if context_parts:
        return "【个性化上下文】\n" + "\n".join(context_parts) + "\n"
    return ""

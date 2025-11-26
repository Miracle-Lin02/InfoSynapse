# -*- coding: utf-8 -*-
"""
Smart reminder system based on academic progress.
Automatically reminds users about relevant courses, practice opportunities, and deadlines.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from utils.notifications import add_notification

REMINDERS_DIR = "data/reminders"
REMINDER_CONFIG_FILE = "data/reminder_config.json"


# Stage-based course recommendations
STAGE_COURSES = {
    "大一": {
        "recommended": ["程序设计基础", "高等数学", "线性代数", "计算机导论", "C语言"],
        "practices": ["新生编程竞赛", "学科兴趣小组", "ACM入门训练"],
        "tips": [
            "打好编程基础，多敲代码多练习",
            "可以开始了解各类竞赛，找到自己感兴趣的方向",
            "大一是培养学习习惯的关键时期"
        ]
    },
    "大二": {
        "recommended": ["数据结构", "算法分析", "数据库原理", "计算机网络", "操作系统"],
        "practices": ["ACM竞赛", "数学建模", "项目实训", "实验室科研", "开源项目"],
        "tips": [
            "可以开始考虑加入实验室或项目组",
            "大二是参加竞赛的黄金时期",
            "尝试做一些完整的小项目积累经验"
        ]
    },
    "大三": {
        "recommended": ["软件工程", "编译原理", "机器学习", "云计算", "专业选修"],
        "practices": ["企业实习", "毕业设计选题", "考研/求职准备", "高级竞赛"],
        "tips": [
            "开始规划求职或考研方向",
            "积极寻找实习机会，积累工作经验",
            "整理项目和竞赛经历，准备简历"
        ]
    },
    "大四": {
        "recommended": ["毕业设计", "专业前沿课程", "职业发展课"],
        "practices": ["秋招/春招", "毕业论文", "答辩准备"],
        "tips": [
            "全力准备求职或升学",
            "保持学习，持续提升技能",
            "做好毕业设计，为大学生活画上圆满句号"
        ]
    }
}

# Skill-based recommendations
SKILL_COURSES = {
    "Python开发": ["Python进阶", "Django/Flask", "数据分析", "自动化脚本"],
    "机器学习": ["机器学习基础", "深度学习", "PyTorch/TensorFlow", "计算机视觉", "NLP"],
    "前端": ["JavaScript高级", "React/Vue", "TypeScript", "前端工程化"],
    "后端": ["微服务架构", "数据库优化", "高并发编程", "系统设计"],
    "算法": ["数据结构与算法", "LeetCode刷题", "算法竞赛进阶"],
    "嵌入式": ["嵌入式系统", "单片机开发", "RTOS", "物联网"],
    "区块链": ["区块链原理", "智能合约", "分布式系统"],
    "计算机视觉": ["数字图像处理", "OpenCV", "目标检测", "图像分割"]
}


def _ensure_dir():
    """Ensure reminders directory exists."""
    os.makedirs(REMINDERS_DIR, exist_ok=True)


def _get_user_reminder_path(username: str) -> str:
    """Get path to user's reminder file."""
    _ensure_dir()
    return os.path.join(REMINDERS_DIR, f"{username}_reminders.json")


def _load_user_reminders(username: str) -> Dict[str, Any]:
    """Load user's reminder settings and history."""
    path = _get_user_reminder_path(username)
    if not os.path.exists(path):
        return {
            "settings": {
                "enabled": True,
                "frequency": "weekly",
                "course_reminders": True,
                "practice_reminders": True,
                "career_reminders": True
            },
            "sent_reminders": [],
            "dismissed_reminders": [],
            "last_check": None
        }
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "settings": {
                "enabled": True,
                "frequency": "weekly",
                "course_reminders": True,
                "practice_reminders": True,
                "career_reminders": True
            },
            "sent_reminders": [],
            "dismissed_reminders": [],
            "last_check": None
        }


def _save_user_reminders(username: str, data: Dict[str, Any]):
    """Save user's reminder settings and history."""
    path = _get_user_reminder_path(username)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_reminder_settings(username: str) -> Dict[str, Any]:
    """Get user's reminder settings."""
    data = _load_user_reminders(username)
    return data.get("settings", {})


def update_reminder_settings(username: str, settings: Dict[str, Any]):
    """Update user's reminder settings."""
    data = _load_user_reminders(username)
    data["settings"].update(settings)
    _save_user_reminders(username, data)


def dismiss_reminder(username: str, reminder_id: str):
    """Mark a reminder as dismissed so it won't appear again."""
    data = _load_user_reminders(username)
    if reminder_id not in data["dismissed_reminders"]:
        data["dismissed_reminders"].append(reminder_id)
    _save_user_reminders(username, data)


def generate_stage_reminders(stage: str, interests: List[str], 
                              skills: List[str]) -> List[Dict[str, Any]]:
    """
    Generate reminders based on user's academic stage and interests.
    
    Args:
        stage: Current academic stage (大一, 大二, 大三, 大四)
        interests: User's interest tags
        skills: User's known skills
    
    Returns:
        List of reminder dicts
    """
    reminders = []
    stage_data = STAGE_COURSES.get(stage, {})
    
    # Course recommendations based on stage
    recommended_courses = stage_data.get("recommended", [])
    if recommended_courses:
        reminders.append({
            "id": f"stage_courses_{stage}",
            "type": "course",
            "priority": "high",
            "title": f"📚 {stage}推荐课程",
            "message": f"根据你当前是{stage}学生，建议关注以下课程：{', '.join(recommended_courses[:4])}",
            "items": recommended_courses
        })
    
    # Practice opportunities based on stage
    recommended_practices = stage_data.get("practices", [])
    if recommended_practices:
        reminders.append({
            "id": f"stage_practices_{stage}",
            "type": "practice",
            "priority": "medium",
            "title": f"🏫 {stage}实践机会",
            "message": f"适合{stage}参与的实践活动：{', '.join(recommended_practices[:3])}",
            "items": recommended_practices
        })
    
    # Tips for current stage
    tips = stage_data.get("tips", [])
    if tips:
        reminders.append({
            "id": f"stage_tips_{stage}",
            "type": "tip",
            "priority": "low",
            "title": f"💡 {stage}学习建议",
            "message": tips[0] if tips else "",
            "items": tips
        })
    
    # Interest-based recommendations
    for interest in interests:
        if interest in SKILL_COURSES:
            courses = SKILL_COURSES[interest]
            reminders.append({
                "id": f"interest_courses_{interest}",
                "type": "course",
                "priority": "medium",
                "title": f"🎯 {interest}技能提升",
                "message": f"你对{interest}感兴趣，推荐学习：{', '.join(courses[:3])}",
                "items": courses
            })
    
    return reminders


def generate_career_reminders(stage: str, target_career: str) -> List[Dict[str, Any]]:
    """
    Generate career-related reminders.
    
    Args:
        stage: Current academic stage
        target_career: User's target career
    
    Returns:
        List of reminder dicts
    """
    reminders = []
    
    # Stage-specific career reminders
    if stage == "大三":
        reminders.append({
            "id": "career_internship_d3",
            "type": "career",
            "priority": "high",
            "title": "🔔 实习季提醒",
            "message": "大三是找实习的关键时期！建议开始准备简历，关注各大公司的实习招聘信息。",
            "action": "查看校招职位"
        })
        reminders.append({
            "id": "career_direction_d3",
            "type": "career",
            "priority": "high",
            "title": "📋 职业规划提醒",
            "message": "是时候明确求职或考研方向了。建议使用AI职业推荐功能，获取个性化建议。",
            "action": "生成职业推荐"
        })
    
    elif stage == "大四":
        reminders.append({
            "id": "career_recruitment_d4",
            "type": "career",
            "priority": "high",
            "title": "🎯 秋招/春招提醒",
            "message": "大四是求职关键期！确保简历已更新，持续关注目标企业的校招信息。",
            "action": "查看校招职位"
        })
    
    # Target career specific reminders
    if target_career:
        reminders.append({
            "id": f"career_target_{target_career}",
            "type": "career",
            "priority": "medium",
            "title": f"💼 {target_career}职业准备",
            "message": f"你的目标职业是{target_career}，建议查看该方向的技能要求和学习路径。",
            "action": "查看学习路径"
        })
    
    return reminders


def generate_progress_reminders(username: str, profile: Dict[str, Any], 
                                 learning_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate reminders based on learning progress.
    
    Args:
        username: Username
        profile: User profile data
        learning_plan: User's learning plan items
    
    Returns:
        List of reminder dicts
    """
    reminders = []
    
    # Learning plan progress reminder
    if learning_plan:
        total = len(learning_plan)
        done = sum(1 for item in learning_plan if item.get("status") == "done")
        doing = sum(1 for item in learning_plan if item.get("status") == "doing")
        todo = total - done - doing
        
        if doing > 0:
            doing_items = [item["name"] for item in learning_plan if item.get("status") == "doing"]
            reminders.append({
                "id": "progress_doing",
                "type": "progress",
                "priority": "medium",
                "title": "📖 学习进度提醒",
                "message": f"你有 {doing} 个正在进行的学习任务：{', '.join(doing_items[:3])}。继续加油！",
                "stats": {"total": total, "done": done, "doing": doing, "todo": todo}
            })
        
        if todo > 5 and doing == 0:
            reminders.append({
                "id": "progress_start",
                "type": "progress",
                "priority": "medium",
                "title": "⏰ 开始学习提醒",
                "message": f"你有 {todo} 个待开始的学习任务。选择一个开始吧！",
                "stats": {"total": total, "done": done, "doing": doing, "todo": todo}
            })
        
        if done > 0 and done == total:
            reminders.append({
                "id": "progress_complete",
                "type": "progress",
                "priority": "low",
                "title": "🎉 恭喜完成学习计划！",
                "message": f"太棒了！你已完成全部 {total} 个学习任务。考虑添加新的学习目标吧！",
                "stats": {"total": total, "done": done, "doing": doing, "todo": todo}
            })
    else:
        reminders.append({
            "id": "progress_empty",
            "type": "progress",
            "priority": "low",
            "title": "📝 创建学习计划",
            "message": "你还没有学习计划。去「综合推荐」添加感兴趣的课程和项目吧！",
            "action": "添加学习计划"
        })
    
    return reminders


def check_and_send_reminders(username: str, profile: Dict[str, Any], 
                              learning_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Check if reminders should be sent and return applicable reminders.
    Also sends reminders as notifications if enabled.
    
    Args:
        username: Username
        profile: User profile data
        learning_plan: User's learning plan items
    
    Returns:
        List of applicable reminder dicts
    """
    data = _load_user_reminders(username)
    settings = data.get("settings", {})
    
    if not settings.get("enabled", True):
        return []
    
    # Get user's stage and interests from profile
    stage = profile.get("stage", "")
    interests = profile.get("interests", [])
    skills = profile.get("skills", [])
    target_career = profile.get("target_career", "")
    
    all_reminders = []
    
    # Generate reminders based on stage
    if stage and settings.get("course_reminders", True):
        stage_reminders = generate_stage_reminders(stage, interests, skills)
        all_reminders.extend(stage_reminders)
    
    # Generate career reminders
    if settings.get("career_reminders", True):
        career_reminders = generate_career_reminders(stage, target_career)
        all_reminders.extend(career_reminders)
    
    # Generate progress reminders
    progress_reminders = generate_progress_reminders(username, profile, learning_plan)
    all_reminders.extend(progress_reminders)
    
    # Filter out dismissed reminders
    dismissed = set(data.get("dismissed_reminders", []))
    filtered_reminders = [r for r in all_reminders if r.get("id") not in dismissed]
    
    # Check frequency and send notifications
    last_check = data.get("last_check")
    should_notify = False
    
    if not last_check:
        should_notify = True
    else:
        try:
            last_check_dt = datetime.fromisoformat(last_check)
            frequency = settings.get("frequency", "weekly")
            
            if frequency == "daily":
                should_notify = datetime.now() - last_check_dt > timedelta(days=1)
            elif frequency == "weekly":
                should_notify = datetime.now() - last_check_dt > timedelta(weeks=1)
            else:
                should_notify = datetime.now() - last_check_dt > timedelta(weeks=2)
        except Exception:
            should_notify = True
    
    # Send high-priority reminders as notifications
    if should_notify:
        for reminder in filtered_reminders:
            if reminder.get("priority") == "high":
                # Check if this reminder was sent recently
                sent_ids = [s.get("id") for s in data.get("sent_reminders", [])]
                if reminder["id"] not in sent_ids:
                    add_notification(
                        username=username,
                        notification_type="reminder",
                        title=reminder["title"],
                        message=reminder["message"]
                    )
                    data["sent_reminders"].append({
                        "id": reminder["id"],
                        "sent_at": datetime.now().isoformat()
                    })
        
        data["last_check"] = datetime.now().isoformat()
        _save_user_reminders(username, data)
    
    return filtered_reminders


def get_quick_tips(stage: str) -> List[str]:
    """
    Get quick tips for a given academic stage.
    
    Args:
        stage: Academic stage
    
    Returns:
        List of tip strings
    """
    stage_data = STAGE_COURSES.get(stage, {})
    return stage_data.get("tips", [])

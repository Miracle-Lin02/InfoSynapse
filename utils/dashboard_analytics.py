# -*- coding: utf-8 -*-
"""
Dashboard analytics utilities for admin dashboard.
Provides user statistics, content metrics, and activity analytics.
"""
import os
import json
import csv
import io
from datetime import datetime, timedelta
from typing import Dict, Any, List, Union
from collections import Counter

def get_user_statistics() -> Dict[str, Any]:
    """Get overall user statistics."""
    from utils.auth import list_users
    
    users = list_users()
    total_users = len(users)
    admin_users = sum(1 for u in users if u.get("role") == "admin")
    regular_users = total_users - admin_users
    
    return {
        "total_users": total_users,
        "admin_users": admin_users,
        "regular_users": regular_users
    }

def get_community_statistics() -> Dict[str, Any]:
    """Get community content statistics."""
    from utils.community import list_threads
    
    threads = list_threads()
    total_threads = len(threads)
    total_posts = sum(len(t.get("posts", [])) for t in threads)
    
    # Count by category
    categories = Counter(t.get("category", "其他") for t in threads)
    
    # Count likes
    total_likes = 0
    for t in threads:
        total_likes += t.get("likes", 0)
        for p in t.get("posts", []):
            total_likes += p.get("likes", 0)
    
    return {
        "total_threads": total_threads,
        "total_posts": total_posts,
        "total_likes": total_likes,
        "categories": dict(categories)
    }

def get_knowledge_base_statistics(kb: Dict[str, Any]) -> Dict[str, Any]:
    """Get knowledge base content statistics."""
    stats = {}
    
    # Count courses
    courses_count = 0
    if "courses" in kb:
        for major, courses_data in kb["courses"].items():
            if isinstance(courses_data, list):
                courses_count += len(courses_data)
            elif isinstance(courses_data, dict):
                courses_count += len(courses_data)
    
    # Count advisors
    advisors_count = 0
    if "advisors" in kb:
        for dept, advisors_data in kb["advisors"].items():
            if isinstance(advisors_data, list):
                advisors_count += len(advisors_data)
            elif isinstance(advisors_data, dict):
                advisors_count += len(advisors_data)
    
    # Count practices
    practices_count = 0
    if "practice_resources" in kb:
        if isinstance(kb["practice_resources"], list):
            practices_count = len(kb["practice_resources"])
        elif isinstance(kb["practice_resources"], dict):
            practices_count = sum(len(v) if isinstance(v, list) else 1 
                                 for v in kb["practice_resources"].values())
    
    # Count alumni cases
    alumni_count = 0
    if "alumni_cases" in kb:
        if isinstance(kb["alumni_cases"], list):
            alumni_count = len(kb["alumni_cases"])
    
    stats["courses_count"] = courses_count
    stats["advisors_count"] = advisors_count
    stats["practices_count"] = practices_count
    stats["alumni_cases_count"] = alumni_count
    stats["total_items"] = courses_count + advisors_count + practices_count + alumni_count
    
    return stats

def get_activity_statistics() -> Dict[str, Any]:
    """Get user activity statistics from activity tracking."""
    activity_dir = "data/user_activity"
    if not os.path.exists(activity_dir):
        return {"total_bookmarks": 0, "active_users": 0}
    
    total_bookmarks = 0
    active_users = 0
    
    for filename in os.listdir(activity_dir):
        if filename.endswith("_activity.json"):
            filepath = os.path.join(activity_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    bookmarks = data.get("bookmarks", [])
                    if bookmarks:
                        total_bookmarks += len(bookmarks)
                        active_users += 1
            except:
                continue
    
    return {
        "total_bookmarks": total_bookmarks,
        "active_users": active_users
    }

def get_recent_activity(days: int = 7) -> Dict[str, Any]:
    """Get recent activity metrics."""
    from utils.community import list_threads
    
    cutoff = datetime.now() - timedelta(days=days)
    threads = list_threads()
    
    recent_threads = 0
    recent_posts = 0
    
    for t in threads:
        try:
            created_at = datetime.fromisoformat(t.get("created_at", ""))
            if created_at >= cutoff:
                recent_threads += 1
        except:
            pass
        
        for p in t.get("posts", []):
            try:
                post_time = datetime.fromisoformat(p.get("time", ""))
                if post_time >= cutoff:
                    recent_posts += 1
            except:
                pass
    
    return {
        "recent_threads": recent_threads,
        "recent_posts": recent_posts,
        "days": days
    }

# Import/Export functionality

def import_user_data(data: Dict[str, Any], mode: str = "merge") -> Dict[str, Any]:
    """
    Import user data.
    
    Args:
        data: User data dictionary (must have 'users' key)
        mode: 'merge' to add new users, 'overwrite' to replace all
        
    Returns:
        Result dictionary with success/failure details
    """
    from utils.auth import list_users
    import hashlib
    
    if "users" not in data:
        return {"success": False, "error": "Invalid data format: missing 'users' key"}
    
    users_file = "data/users.json"
    
    # Backup existing data
    backup_file = f"data/users_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    if os.path.exists(users_file):
        with open(users_file, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
    
    existing_users = list_users()
    new_users_data = data["users"]
    
    if mode == "overwrite":
        # Replace all users
        result_users = new_users_data
        message = f"Replaced all users. Total: {len(result_users)}"
    else:  # merge
        # Merge: add new users, keep existing
        existing_usernames = {u["username"] for u in existing_users}
        added_count = 0
        
        for user in new_users_data:
            if user["username"] not in existing_usernames:
                existing_users.append(user)
                added_count += 1
        
        result_users = existing_users
        message = f"Added {added_count} new users. Total: {len(result_users)}"
    
    # Save
    with open(users_file, "w", encoding="utf-8") as f:
        json.dump({"users": result_users}, f, ensure_ascii=False, indent=2)
    
    return {
        "success": True,
        "message": message,
        "backup_file": backup_file,
        "total_users": len(result_users)
    }

def import_community_data(data: Dict[str, Any], mode: str = "merge") -> Dict[str, Any]:
    """
    Import community discussion data.
    
    Args:
        data: Community data dictionary (must have 'threads' key)
        mode: 'merge' to add new threads, 'overwrite' to replace all
        
    Returns:
        Result dictionary with success/failure details
    """
    from utils.community import list_threads, save_threads
    
    if "threads" not in data:
        return {"success": False, "error": "Invalid data format: missing 'threads' key"}
    
    # Backup
    threads_file = "data/community_threads.json"
    backup_file = f"data/community_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    if os.path.exists(threads_file):
        with open(threads_file, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
    
    existing_threads = list_threads()
    new_threads_data = data["threads"]
    
    if mode == "overwrite":
        result_threads = new_threads_data
        message = f"Replaced all threads. Total: {len(result_threads)}"
    else:  # merge
        existing_ids = {t["id"] for t in existing_threads}
        added_count = 0
        
        for thread in new_threads_data:
            if thread["id"] not in existing_ids:
                existing_threads.append(thread)
                added_count += 1
        
        result_threads = existing_threads
        message = f"Added {added_count} new threads. Total: {len(result_threads)}"
    
    # Save
    save_threads(result_threads)
    
    return {
        "success": True,
        "message": message,
        "backup_file": backup_file,
        "total_threads": len(result_threads)
    }

def import_knowledge_base(data: Dict[str, Any], mode: str = "merge") -> Dict[str, Any]:
    """
    Import knowledge base data.
    
    Args:
        data: Knowledge base dictionary
        mode: 'merge' to combine, 'overwrite' to replace all
        
    Returns:
        Result dictionary with success/failure details
    """
    kb_file = "data/hdu_knowledge_base.json"
    
    # Backup
    backup_file = f"data/kb_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    if os.path.exists(kb_file):
        with open(kb_file, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
    
    if mode == "overwrite":
        result_kb = data
        message = "Replaced entire knowledge base"
    else:  # merge
        # Load existing
        if os.path.exists(kb_file):
            with open(kb_file, "r", encoding="utf-8") as f:
                existing_kb = json.load(f)
        else:
            existing_kb = {}
        
        # Merge each section
        for key in ["courses", "advisors", "practice_resources", "alumni_cases"]:
            if key in data:
                if key not in existing_kb:
                    existing_kb[key] = data[key]
                else:
                    # Merge logic depends on structure
                    if isinstance(data[key], dict) and isinstance(existing_kb[key], dict):
                        existing_kb[key].update(data[key])
                    elif isinstance(data[key], list):
                        # For lists, append new items
                        existing_kb[key] = existing_kb.get(key, []) + data[key]
        
        result_kb = existing_kb
        message = "Merged knowledge base data"
    
    # Save
    with open(kb_file, "w", encoding="utf-8") as f:
        json.dump(result_kb, f, ensure_ascii=False, indent=2)
    
    stats = get_knowledge_base_statistics(result_kb)
    
    return {
        "success": True,
        "message": message,
        "backup_file": backup_file,
        "statistics": stats
    }

# CSV/Excel Import Utilities

def csv_to_json(csv_content: str, data_type: str = "users") -> Dict[str, Any]:
    """
    Convert CSV content to JSON format for import.
    
    Args:
        csv_content: CSV file content as string
        data_type: Type of data ('users', 'community', 'knowledge')
        
    Returns:
        Dictionary in JSON format ready for import
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(reader)
    
    if data_type == "users":
        # Expected columns: username, password, role, registration_date
        users = []
        for row in rows:
            user = {
                "username": row.get("username", ""),
                "password": row.get("password", ""),  # Should be pre-hashed
                "role": row.get("role", "user"),
                "registration_date": row.get("registration_date", datetime.now().isoformat())
            }
            if user["username"] and user["password"]:
                users.append(user)
        return {"users": users}
    
    elif data_type == "community":
        # Expected columns: thread_id, title, author, content, category, created_at
        threads = []
        thread_dict = {}
        
        for row in rows:
            thread_id = row.get("thread_id", "")
            if not thread_id:
                continue
                
            if thread_id not in thread_dict:
                thread_dict[thread_id] = {
                    "id": thread_id,
                    "title": row.get("title", ""),
                    "author": row.get("author", ""),
                    "content": row.get("content", ""),
                    "category": row.get("category", "其他"),
                    "created_at": row.get("created_at", datetime.now().isoformat()),
                    "posts": [],
                    "likes": []
                }
        
        threads = list(thread_dict.values())
        return {"threads": threads}
    
    elif data_type == "courses":
        # Expected columns: major, name, level, type, prerequisites, link, description
        courses_by_major = {}
        for row in rows:
            major = row.get("major", "未分类")
            if major not in courses_by_major:
                courses_by_major[major] = []
            
            course = {
                "name": row.get("name", ""),
                "level": row.get("level", "本科"),
                "type": row.get("type", "必修"),
                "prerequisites": row.get("prerequisites", "").split(";") if row.get("prerequisites") else [],
                "link": row.get("link", ""),
                "description": row.get("description", "")
            }
            if course["name"]:
                courses_by_major[major].append(course)
        
        return {"courses": courses_by_major}
    
    return {}

def excel_to_json(file_content: bytes, data_type: str = "users", sheet_name: int = 0) -> Dict[str, Any]:
    """
    Convert Excel content to JSON format for import.
    
    Args:
        file_content: Excel file content as bytes
        data_type: Type of data ('users', 'community', 'knowledge')
        sheet_name: Sheet index or name to read (default: 0)
        
    Returns:
        Dictionary in JSON format ready for import
    """
    try:
        import pandas as pd
    except ImportError:
        return {"error": "pandas library not installed. Please install: pip install pandas openpyxl"}
    
    try:
        # Read Excel file
        df = pd.read_excel(io.BytesIO(file_content), sheet_name=sheet_name)
        
        # Convert to CSV string
        csv_content = df.to_csv(index=False)
        
        # Use CSV converter
        return csv_to_json(csv_content, data_type)
    
    except Exception as e:
        return {"error": f"Failed to parse Excel file: {str(e)}"}

def import_from_file(file_content: Union[str, bytes], filename: str, data_type: str = "users", mode: str = "merge") -> Dict[str, Any]:
    """
    Universal import function that handles JSON, CSV, and Excel files.
    
    Args:
        file_content: File content (string for text files, bytes for binary)
        filename: Name of the file (used to detect format)
        data_type: Type of data ('users', 'community', 'courses')
        mode: Import mode ('merge' or 'overwrite')
        
    Returns:
        Import result dictionary
    """
    # Detect file format
    file_ext = filename.lower().split('.')[-1]
    
    try:
        if file_ext == "json":
            # Parse JSON
            if isinstance(file_content, bytes):
                file_content = file_content.decode('utf-8')
            data = json.loads(file_content)
        
        elif file_ext == "csv":
            # Convert CSV to JSON
            if isinstance(file_content, bytes):
                file_content = file_content.decode('utf-8')
            data = csv_to_json(file_content, data_type)
        
        elif file_ext in ["xlsx", "xls"]:
            # Convert Excel to JSON
            if isinstance(file_content, str):
                file_content = file_content.encode('utf-8')
            data = excel_to_json(file_content, data_type)
            
            if "error" in data:
                return {"success": False, "error": data["error"]}
        
        else:
            return {"success": False, "error": f"Unsupported file format: {file_ext}. Supported: JSON, CSV, XLSX, XLS"}
        
        # Validate data format
        if not data or "error" in data:
            return {"success": False, "error": data.get("error", "Invalid data format")}
        
        # Route to appropriate import function
        if data_type == "users":
            return import_user_data(data, mode)
        elif data_type == "community":
            return import_community_data(data, mode)
        elif data_type in ["courses", "knowledge"]:
            return import_knowledge_base(data, mode)
        else:
            return {"success": False, "error": f"Unknown data type: {data_type}"}
    
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON format: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Import failed: {str(e)}"}

def get_import_template_csv(data_type: str = "users") -> str:
    """
    Generate a CSV template for data import.
    
    Args:
        data_type: Type of template ('users', 'community', 'courses', 'advisors', 'practices', 'alumni_cases')
        
    Returns:
        CSV template as string
    """
    if data_type == "users":
        return "username,password,role,registration_date\nexample_user,hashed_password,user,2024-01-01T00:00:00\nadmin_user,hashed_password,admin,2024-01-01T00:00:00"
    
    elif data_type == "community":
        return "thread_id,title,author,content,category,created_at\nthread_001,示例话题,username,这是话题内容,技术讨论,2024-01-01T00:00:00"
    
    elif data_type == "courses":
        return "major,name,level,type,prerequisites,link,description\n计算机,数据结构,本科,必修,程序设计基础,http://example.com,数据结构基础课程\n计算机,算法设计,本科,必修,数据结构,http://example.com,算法设计与分析"
    
    elif data_type == "advisors":
        return "name,title,research_areas,projects,email,office\n张教授,教授,人工智能;机器学习,国家自然科学基金,zhang@hdu.edu.cn,信息楼301\n李教授,副教授,数据库;大数据,省级科研项目,li@hdu.edu.cn,信息楼302"
    
    elif data_type == "practices":
        return "name,type,description,requirements,benefits,link\nACM竞赛,竞赛,程序设计竞赛,编程基础,提升算法能力,http://example.com/acm\n人工智能实验室,实验室,AI前沿技术研究,机器学习基础,科研经验,http://example.com/ailab"
    
    elif data_type == "alumni_cases":
        return "title,focus_area,alumni_name,graduation_year,case_content\nAI创业成功案例,人工智能,李明,2018,从杭电走向创业成功的故事。毕业后创建AI公司...\n大数据工程师发展,大数据,王芳,2019,从学生到高级工程师的成长历程。现任职于知名互联网公司..."
    
    return "# Unsupported template type"

def get_import_template_json(data_type: str = "courses") -> str:
    """
    Generate a JSON template for data import.
    
    Args:
        data_type: Type of template ('courses', 'advisors', 'practices', 'alumni_cases')
        
    Returns:
        JSON template as formatted string
    """
    templates = {
        "courses": {
            "courses": {
                "计算机": [
                    {
                        "name": "数据结构",
                        "level": "本科",
                        "type": "必修",
                        "prerequisites": "程序设计基础",
                        "link": "http://example.com",
                        "description": "数据结构基础课程"
                    },
                    {
                        "name": "算法设计",
                        "level": "本科",
                        "type": "必修",
                        "prerequisites": "数据结构",
                        "link": "http://example.com",
                        "description": "算法设计与分析"
                    }
                ]
            }
        },
        "advisors": {
            "advisors": {
                "信息工程学院": [
                    {
                        "name": "张教授",
                        "title": "教授",
                        "research_areas": ["人工智能", "机器学习"],
                        "projects": "国家自然科学基金",
                        "email": "zhang@hdu.edu.cn",
                        "office": "信息楼301"
                    },
                    {
                        "name": "李教授",
                        "title": "副教授",
                        "research_areas": ["数据库", "大数据"],
                        "projects": "省级科研项目",
                        "email": "li@hdu.edu.cn",
                        "office": "信息楼302"
                    }
                ]
            }
        },
        "practices": {
            "practice_resources": [
                {
                    "name": "ACM竞赛",
                    "type": "竞赛",
                    "description": "程序设计竞赛",
                    "requirements": "编程基础",
                    "benefits": "提升算法能力",
                    "link": "http://example.com/acm"
                },
                {
                    "name": "人工智能实验室",
                    "type": "实验室",
                    "description": "AI前沿技术研究",
                    "requirements": "机器学习基础",
                    "benefits": "科研经验",
                    "link": "http://example.com/ailab"
                }
            ]
        },
        "alumni_cases": {
            "alumni_cases": [
                {
                    "title": "AI创业成功案例",
                    "focus_area": "人工智能",
                    "alumni_name": "李明",
                    "graduation_year": "2018",
                    "case_content": "从杭电走向创业成功的故事。毕业后创建AI公司，现已成为行业领军企业。"
                },
                {
                    "title": "大数据工程师发展",
                    "focus_area": "大数据",
                    "alumni_name": "王芳",
                    "graduation_year": "2019",
                    "case_content": "从学生到高级工程师的成长历程。现任职于知名互联网公司，负责核心数据平台建设。"
                }
            ]
        }
    }
    
    template = templates.get(data_type, {})
    return json.dumps(template, ensure_ascii=False, indent=2)

def get_import_template_excel(data_type: str = "courses") -> bytes:
    """
    Generate an Excel template for data import.
    
    Args:
        data_type: Type of template ('courses', 'advisors', 'practices', 'alumni_cases')
        
    Returns:
        Excel file as bytes
    """
    try:
        import pandas as pd
    except ImportError:
        # Fallback: return CSV as bytes if pandas not available
        csv_content = get_import_template_csv(data_type)
        return csv_content.encode('utf-8-sig')
    
    try:
        # Create DataFrame based on data type
        if data_type == "courses":
            data = {
                "major": ["计算机", "计算机"],
                "name": ["数据结构", "算法设计"],
                "level": ["本科", "本科"],
                "type": ["必修", "必修"],
                "prerequisites": ["程序设计基础", "数据结构"],
                "link": ["http://example.com", "http://example.com"],
                "description": ["数据结构基础课程", "算法设计与分析"]
            }
        elif data_type == "advisors":
            data = {
                "name": ["张教授", "李教授"],
                "title": ["教授", "副教授"],
                "research_areas": ["人工智能;机器学习", "数据库;大数据"],
                "projects": ["国家自然科学基金", "省级科研项目"],
                "email": ["zhang@hdu.edu.cn", "li@hdu.edu.cn"],
                "office": ["信息楼301", "信息楼302"]
            }
        elif data_type == "practices":
            data = {
                "name": ["ACM竞赛", "人工智能实验室"],
                "type": ["竞赛", "实验室"],
                "description": ["程序设计竞赛", "AI前沿技术研究"],
                "requirements": ["编程基础", "机器学习基础"],
                "benefits": ["提升算法能力", "科研经验"],
                "link": ["http://example.com/acm", "http://example.com/ailab"]
            }
        elif data_type == "alumni_cases":
            data = {
                "title": ["AI创业成功案例", "大数据工程师发展"],
                "focus_area": ["人工智能", "大数据"],
                "alumni_name": ["李明", "王芳"],
                "graduation_year": ["2018", "2019"],
                "case_content": [
                    "从杭电走向创业成功的故事。毕业后创建AI公司，现已成为行业领军企业。",
                    "从学生到高级工程师的成长历程。现任职于知名互联网公司，负责核心数据平台建设。"
                ]
            }
        else:
            data = {"error": ["Unsupported template type"]}
        
        df = pd.DataFrame(data)
        
        # Write to Excel in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Template')
        
        return output.getvalue()
    
    except Exception as e:
        # Fallback to CSV
        csv_content = get_import_template_csv(data_type)
        return csv_content.encode('utf-8-sig')

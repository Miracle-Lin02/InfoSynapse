# -*- coding: utf-8 -*-
"""
Global search functionality for courses, advisors, and practice resources.
"""

from typing import List, Dict, Any, Tuple


def search_all(query: str, kb: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Search across courses, advisors, and practice resources.
    
    Args:
        query: Search query string
        kb: Knowledge base dictionary
        
    Returns:
        Dictionary with keys 'courses', 'advisors', 'practices' containing matching results
    """
    if not query or not query.strip():
        return {"courses": [], "advisors": [], "practices": []}
    
    query_lower = query.lower().strip()
    
    results = {
        "courses": [],
        "advisors": [],
        "practices": []
    }
    
    # Search courses
    for major_name, courses_list in kb.get("courses", {}).items():
        # Handle both list and dict structures
        if isinstance(courses_list, list):
            for course in courses_list:
                if _matches_query(course, query_lower, ["name", "outline"]):
                    course_copy = course.copy()
                    course_copy["major"] = major_name
                    results["courses"].append(course_copy)
        elif isinstance(courses_list, dict):
            for course_code, course in courses_list.items():
                if _matches_query(course, query_lower, ["name", "outline"]):
                    course_copy = course.copy()
                    course_copy["major"] = major_name
                    course_copy["code"] = course_code
                    results["courses"].append(course_copy)
    
    # Search advisors
    for advisor in kb.get("advisors", []):
        if _matches_query(advisor, query_lower, ["name", "department", "research"]):
            results["advisors"].append(advisor.copy())
    
    # Search practice resources
    for practice in kb.get("practice", []):
        if _matches_query(practice, query_lower, ["name", "type", "description"]):
            results["practices"].append(practice.copy())
    
    return results


def _matches_query(item: Dict[str, Any], query: str, fields: List[str]) -> bool:
    """
    Check if any of the specified fields in item match the query.
    
    Args:
        item: Dictionary to search in
        query: Lowercase query string
        fields: List of field names to search
        
    Returns:
        True if query matches any field, False otherwise
    """
    for field in fields:
        value = item.get(field, "")
        if value and query in str(value).lower():
            return True
    return False


def search_courses(query: str, kb: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Search only in courses."""
    return search_all(query, kb)["courses"]


def search_advisors(query: str, kb: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Search only in advisors."""
    return search_all(query, kb)["advisors"]


def search_practices(query: str, kb: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Search only in practice resources."""
    return search_all(query, kb)["practices"]

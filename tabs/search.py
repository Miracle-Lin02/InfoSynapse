# -*- coding: utf-8 -*-
"""
Global Search Tab: Search across courses, advisors, and practice resources.
"""

import streamlit as st
from typing import Dict, Any

from utils.global_search import search_all
from utils.user_activity import add_to_history, add_bookmark, remove_bookmark, is_bookmarked


def render_search_tab(kb: Dict[str, Any]):
    """Render the global search tab."""
    st.header("🔍 全局搜索")
    st.markdown("搜索课程、导师和校内实践资源")
    
    # Search input
    search_query = st.text_input(
        "搜索关键词",
        placeholder="输入课程名称、导师姓名、实践项目等...",
        help="支持搜索课程、导师、校内实践资源"
    )
    
    if not search_query or not search_query.strip():
        st.info("💡 输入关键词开始搜索")
        return
    
    # Perform search
    results = search_all(search_query, kb)
    
    total_results = len(results["courses"]) + len(results["advisors"]) + len(results["practices"])
    
    if total_results == 0:
        st.warning(f"未找到与 \"{search_query}\" 相关的结果")
        return
    
    st.success(f"找到 {total_results} 条结果")
    
    # Get current user
    user_info = st.session_state.get("user") or {}
    username = user_info.get("username", "") if user_info else ""
    
    # Display results in tabs
    result_tabs = st.tabs([
        f"📚 课程 ({len(results['courses'])})",
        f"👩‍🏫 导师 ({len(results['advisors'])})",
        f"🏫 实践 ({len(results['practices'])})"
    ])
    
    # Courses tab
    with result_tabs[0]:
        if not results["courses"]:
            st.info("未找到相关课程")
        else:
            for course in results["courses"]:
                with st.expander(f"📖 {course.get('name', '未命名课程')} - {course.get('major', '')}"):
                    st.markdown(f"**课程代码**: {course.get('code', 'N/A')}")
                    st.markdown(f"**层次**: {course.get('level', 'N/A')}")
                    prereq = course.get('prereq', '')
                    if prereq:
                        st.markdown(f"**先修课程**: {prereq}")
                    link = course.get('link', '')
                    if link:
                        st.markdown(f"**课程链接**: [{link}]({link})")
                    st.markdown("**课程简介**:")
                    st.write(course.get('outline', '暂无简介'))
                    
                    # Bookmark button
                    if username:
                        course_id = f"{course.get('major', '')}_{course.get('code', '')}"
                        bookmarked = is_bookmarked(username, "course", course_id)
                        
                        col1, col2 = st.columns([1, 5])
                        with col1:
                            if bookmarked:
                                if st.button("⭐ 已收藏", key=f"unbm_course_{course_id}"):
                                    remove_bookmark(username, "course", course_id)
                                    st.rerun()
                            else:
                                if st.button("☆ 收藏", key=f"bm_course_{course_id}"):
                                    add_bookmark(username, "course", course_id, course.get('name', ''))
                                    add_to_history(username, "course", course_id, course.get('name', ''))
                                    st.rerun()
    
    # Advisors tab
    with result_tabs[1]:
        if not results["advisors"]:
            st.info("未找到相关导师")
        else:
            for advisor in results["advisors"]:
                with st.expander(f"👨‍🏫 {advisor.get('name', '未命名导师')}"):
                    st.markdown(f"**院系**: {advisor.get('department', 'N/A')}")
                    st.markdown(f"**研究方向**: {advisor.get('research', '暂无信息')}")
                    homepage = advisor.get('homepage', '')
                    if homepage:
                        st.markdown(f"**主页**: [{homepage}]({homepage})")
                    
                    if advisor.get('national_projects'):
                        st.info("🇨🇳 参与国家重大项目")
                        st.markdown(f"**项目信息**: {advisor.get('national_projects_info', '')}")
                    
                    # Bookmark button
                    if username:
                        advisor_id = advisor.get('name', '')
                        bookmarked = is_bookmarked(username, "advisor", advisor_id)
                        
                        col1, col2 = st.columns([1, 5])
                        with col1:
                            if bookmarked:
                                if st.button("⭐ 已收藏", key=f"unbm_advisor_{advisor_id}"):
                                    remove_bookmark(username, "advisor", advisor_id)
                                    st.rerun()
                            else:
                                if st.button("☆ 收藏", key=f"bm_advisor_{advisor_id}"):
                                    add_bookmark(username, "advisor", advisor_id, advisor.get('name', ''))
                                    add_to_history(username, "advisor", advisor_id, advisor.get('name', ''))
                                    st.rerun()
    
    # Practice resources tab
    with result_tabs[2]:
        if not results["practices"]:
            st.info("未找到相关实践资源")
        else:
            for practice in results["practices"]:
                with st.expander(f"🏫 {practice.get('name', '未命名资源')}"):
                    st.markdown(f"**类型**: {practice.get('type', 'N/A')}")
                    st.markdown(f"**简介**: {practice.get('description', '暂无简介')}")
                    link = practice.get('link', '')
                    if link:
                        st.markdown(f"**链接**: [{link}]({link})")
                    
                    # Bookmark button
                    if username:
                        practice_id = practice.get('name', '')
                        bookmarked = is_bookmarked(username, "practice", practice_id)
                        
                        col1, col2 = st.columns([1, 5])
                        with col1:
                            if bookmarked:
                                if st.button("⭐ 已收藏", key=f"unbm_practice_{practice_id}"):
                                    remove_bookmark(username, "practice", practice_id)
                                    st.rerun()
                            else:
                                if st.button("☆ 收藏", key=f"bm_practice_{practice_id}"):
                                    add_bookmark(username, "practice", practice_id, practice.get('name', ''))
                                    add_to_history(username, "practice", practice_id, practice.get('name', ''))
                                    st.rerun()

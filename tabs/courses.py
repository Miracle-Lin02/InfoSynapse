# -*- coding: utf-8 -*-
"""
Tab 1: Courses view and review submission.
"""

from typing import Dict, Any
import streamlit as st

from utils.knowledge_loader import (
    load_knowledge_base,
    get_courses,
    submit_course_review_pending,
)
from utils.notify import notify_admins_new_pending
from shared.ai_helpers import format_review, render_tab_ai_helper


def render_courses_tab(KB_PATH: str, KB: Dict[str, Any], ai_agent):
    """Render the courses tab."""
    st.header("🏫 课程与学习路径")
    
    # Ideological & Political Education: Course value guidance
    with st.expander("🎓 价值引领课程推荐", expanded=False):
        st.markdown("""
        **技术向善与学术诚信**
        
        对于技术类专业学生，建议关注以下价值引领类课程：
        
        - 🤖 **人工智能伦理与社会责任**：探讨AI技术的伦理边界
        - 🛡️ **网络安全法律法规**：培养网络空间安全意识
        - 🔬 **科学家精神与创新文化**：学习科研报国情怀
        
        这些课程标记为"价值引领类"，帮助你在技术学习中树立正确价值观。
        """)
    
    st.markdown("---")
    
    majors = list(KB.get("courses", {}).keys()) or ["计算机"]
    
    # Filter section
    st.markdown("#### 🔍 课程筛选")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        major = st.selectbox("选择专业", majors, index=0)
    
    with col2:
        course_types = ["全部类型", "必修", "选修", "价值引领类"]
        selected_type = st.selectbox("课程类型", course_types)
    
    with col3:
        course_levels = ["全部级别", "本科", "研究生"]
        selected_level = st.selectbox("课程级别", course_levels)
    
    # Keyword search
    search_keyword = st.text_input("🔎 搜索关键词（课程名称或代码）", placeholder="输入课程名称或代码进行搜索...")
    
    st.markdown("---")
    
    courses = get_courses(KB, major)
    
    # Apply filters
    if courses:
        # Filter by type
        if selected_type != "全部类型":
            if selected_type == "价值引领类":
                courses = [c for c in courses if c.get("ideological", False) or c.get("level") == "价值引领类"]
            else:
                courses = [c for c in courses if c.get("type", "") == selected_type]
        
        # Filter by level
        if selected_level != "全部级别":
            courses = [c for c in courses if c.get("level", "") == selected_level or c.get("degree", "") == selected_level]
        
        # Filter by keyword
        if search_keyword.strip():
            keyword_lower = search_keyword.strip().lower()
            courses = [c for c in courses 
                      if keyword_lower in c.get("name", "").lower() 
                      or keyword_lower in c.get("code", "").lower()]
    
    context_lines = []
    if not courses:
        st.info("未找到符合条件的课程")
    else:
        st.success(f"找到 {len(courses)} 门课程")
        for c in courses:
            code = c.get("code", "")
            name = c.get("name", "")
            context_lines.append(f"{code} {name}")
            
            # Track browsing history when course is displayed
            username = st.session_state.get("username")
            if username:
                add_to_history(username, "course", code, name)
            
            # Add badge for ideological courses
            is_ideological = c.get("ideological", False) or c.get("level") == "价值引领类"
            ideological_badge = " 🎓" if is_ideological else ""
            
            st.markdown(f"### {code} {name}{ideological_badge}")
            
            # Highlight ideological courses
            if is_ideological:
                st.info("🎯 **价值引领类课程** - 该课程注重价值观培养和技术伦理教育")
            
            st.write(c.get("outline", ""))
            st.caption(f"先修：{c.get('prereq','')}  | 链接：{c.get('link','')}")
            reviews = c.get("reviews", []) or []
            if reviews:
                st.markdown("**学生评价（已发布）**")
                for r in reviews[:5]:
                    st.markdown(format_review(r))
                if len(reviews) > 5:
                    st.caption(f"还有 {len(reviews)-5} 条已发布评价")
            else:
                st.info("尚无已发布评价")
            with st.expander("添加学生评价（进入待审核，只有管理员可见）"):
                reviewer = st.text_input(
                    f"你的名字（可选） - {code}", key=f"rev_name_{code}"
                )
                rating = st.slider(
                    "评分（1-5）", 1, 5, 5, key=f"rev_rating_{code}"
                )
                comment = st.text_area(
                    "评价内容", key=f"rev_comment_{code}", height=120
                )
                if st.button("提交（进入待审核）", key=f"submit_rev_{code}"):
                    if not comment.strip():
                        st.warning("请输入评价内容")
                    else:
                        pid = submit_course_review_pending(
                            KB_PATH,
                            KB,
                            course_code=code,
                            reviewer=reviewer,
                            rating=rating,
                            comment=comment,
                        )
                        if pid:
                            st.success("已提交，管理员审核后发布")
                            KB.clear()
                            KB.update(load_knowledge_base(KB_PATH))
                            pending = next(
                                (
                                    p
                                    for p in KB.get("pending_reviews", []) or []
                                    if p.get("id") == pid
                                ),
                                None,
                            )
                            if pending:
                                notify_admins_new_pending(pending)
                        else:
                            st.error("提交失败")

    render_tab_ai_helper(
        "courses",
        "课程与学习路径",
        ai_agent,
        context="当前专业：" + major + "，已有课程：" + ", ".join(context_lines[:15]),
    )

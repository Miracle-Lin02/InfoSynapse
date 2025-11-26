# -*- coding: utf-8 -*-
"""
Tab 3: Practice resources view.
"""

from typing import Dict, Any
import streamlit as st

from utils.knowledge_loader import get_practice
from utils.recommend import SOCIAL_VALUE_KEYWORDS
from shared.ai_helpers import render_tab_ai_helper
from utils.user_activity import add_to_history


def render_practice_tab(KB: Dict[str, Any], ai_agent):
    """Render the practice resources tab."""
    st.header("🏫 校内实践资源")
    
    # Ideological & Political Education: Social responsibility
    with st.expander("🎯 社会责任与实践育人", expanded=False):
        st.markdown("""
        **实践中的价值引领**
        
        参与实践项目时，建议关注以下类型：
        
        - 🏅 **红色竞赛**："挑战杯"红色专项等弘扬主旋律的竞赛活动
        - 💝 **公益科研**：智慧助老、数字乡村等服务社会的技术项目
        - 🤝 **团队协作**：注重集体荣誉和团队精神的实践活动
        - 🇨🇳 **国产技术**：参与开源国产软件、自主可控技术的开发
        
        💡 这些实践不仅能提升技术能力，更能培养社会责任感和家国情怀。
        """)
    
    st.markdown("---")
    
    # Filter section
    st.markdown("#### 🔍 实践项目筛选")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        type_options = ["全部类型", "竞赛", "实验室", "科研项目", "社会实践", "创新创业"]
        selected_type = st.selectbox("项目类型", type_options)
    
    with col2:
        requirements_options = ["全部要求", "无基础要求", "需编程基础", "需专业基础", "需团队合作"]
        selected_requirements = st.selectbox("参与要求", requirements_options)
    
    with col3:
        q = st.text_input("🔎 关键词", placeholder="搜索项目名称...", key="prac_q")
    
    with col4:
        prioritize_social = st.checkbox(
            "💝 公益项目",
            value=st.session_state.get("prioritize_social_value", False),
            key="prioritize_social_value_checkbox",
            help="优先显示红色竞赛/公益项目"
        )
        st.session_state["prioritize_social_value"] = prioritize_social
    
    resources = get_practice(KB)
    
    # Apply type filter
    if selected_type != "全部类型":
        resources = [r for r in resources if selected_type in r.get("type", "")]
    
    # Apply requirements filter
    if selected_requirements != "全部要求":
        if selected_requirements == "无基础要求":
            resources = [r for r in resources if "无" in r.get("requirements", "") or not r.get("requirements", "").strip()]
        else:
            key_mapping = {
                "需编程基础": ["编程", "代码", "程序"],
                "需专业基础": ["专业", "基础课程"],
                "需团队合作": ["团队", "协作", "小组"]
            }
            keywords = key_mapping.get(selected_requirements, [])
            resources = [r for r in resources 
                        if any(kw in r.get("requirements", "") for kw in keywords)]
    
    # Apply search filter
    if q.strip():
        q_lower = q.strip().lower()
        resources = [r for r in resources 
                    if q_lower in r.get("name", "").lower()
                    or q_lower in r.get("desc", "").lower()]
    
    # Always calculate social value scoring for badges (not just when filter is on)
    for r in resources:
        name = (r.get("name", "") or "").lower()
        desc = (r.get("desc", "") or "").lower()
        # Check for red competition or public welfare keywords
        social_score = sum(1 for kw in SOCIAL_VALUE_KEYWORDS if kw in name or kw in desc)
        r["social_value_score"] = social_score
    
    # Sort by social value score if filter is enabled
    if prioritize_social:
        resources = sorted(resources, key=lambda x: x.get("social_value_score", 0), reverse=True)
    
    context_lines = []
    if not resources:
        st.info("暂无校内实践资源")
    else:
        for r in resources:
            practice_name = r.get("name", "")
            practice_id = r.get("id", practice_name)
            context_lines.append(practice_name)
            
            # Track browsing history when practice is displayed
            username = st.session_state.get("username")
            if username:
                add_to_history(username, "practice", practice_id, practice_name)
            
            # Add social value badge
            social_badge = ""
            social_score = r.get("social_value_score", 0)
            if social_score > 0:
                social_badge = " 💝"
            
            st.markdown(f"### {practice_name}{social_badge} — {r.get('type','')}")
            
            # Highlight social value
            if social_score > 0:
                st.info("🎯 **社会价值项目** - 该项目具有公益性质或服务国家战略，参与可培养社会责任感")
            
            st.write(r.get("desc", ""))
            if r.get("link"):
                st.markdown(f"[详情]({r.get('link')})")
            st.caption(f"匹配度：{r.get('match_score','N/A')}")
            st.divider()

    render_tab_ai_helper(
        "practice",
        "校内实践资源",
        ai_agent,
        context="已有实践项目示例：" + ", ".join(context_lines[:15]),
    )

# -*- coding: utf-8 -*-
"""
Tab 2: Advisors/mentors view and review submission.
"""

from typing import Dict, Any
import streamlit as st

from utils.knowledge_loader import (
    load_knowledge_base,
    get_advisors,
    submit_advisor_review_pending,
)
from utils.notify import notify_admins_new_pending
from shared.ai_helpers import format_review, render_tab_ai_helper
from utils.user_activity import add_to_history


def render_advisors_tab(KB_PATH: str, KB: Dict[str, Any], ai_agent):
    """Render the advisors tab."""
    st.header("👩‍🏫 导师匹配")
    
    # Ideological & Political Education: Research integrity and patriotism
    with st.expander("🔬 学术诚信与科研报国", expanded=False):
        st.markdown("""
        **科研诚信与技术向善**
        
        选择导师时，除了研究方向匹配，还应关注：
        
        - 📚 **学术诚信指导**：导师在学术规范、论文写作方面的指导能力
        - 🇨🇳 **国家重大项目参与**：导师在"卡脖子"技术攻关、公益科研项目中的贡献
        - 🎯 **价值引领**：导师对学生价值观、职业规划的正向引导
        
        💡 建议优先选择参与国家重大项目、具有家国情怀的科研团队。
        """)
    
    st.markdown("---")
    
    # Filter section
    st.markdown("#### 🔍 导师筛选")
    col1, col2, col3, col4 = st.columns(4)
    
    # Get all unique colleges/departments from advisors list
    all_advisors = KB.get("advisors", [])
    if isinstance(all_advisors, list):
        colleges = sorted(set(a.get("department", "其他") for a in all_advisors if a.get("department")))
        if not colleges:
            colleges = ["全部学院"]
        else:
            colleges.insert(0, "全部学院")
    else:
        colleges = ["全部学院"]
    
    with col1:
        selected_college = st.selectbox("学院/院系", colleges)
    
    with col2:
        title_options = ["全部职称", "教授", "副教授", "讲师", "研究员"]
        selected_title = st.selectbox("职称筛选", title_options)
    
    with col3:
        q = st.text_input("🔎 研究方向", placeholder="关键词...", key="adv_q")
    
    with col4:
        # Add filter for national major projects
        filter_national = st.checkbox(
            "🇨🇳 国家项目",
            value=st.session_state.get("filter_national_projects", False),
            key="filter_national_projects_checkbox",
            help="仅显示参与国家重大项目的导师"
        )
        st.session_state["filter_national_projects"] = filter_national
    
    # Get advisors and apply filters
    advisors = get_advisors(KB, q)
    
    # Filter by college if not "全部学院"
    if selected_college != "全部学院":
        advisors = [a for a in advisors if a.get("department", "") == selected_college]
    
    # Apply title filter
    if selected_title != "全部职称":
        advisors = [a for a in advisors if selected_title in a.get("title", "")]
    
    # Filter by national projects if enabled
    if filter_national:
        advisors = [a for a in advisors if a.get("national_projects", False)]
    
    context_lines = []
    if not advisors:
        st.info("未找到导师")
    else:
        for idx, a in enumerate(advisors):
            name = a.get("name", "")
            advisor_id = a.get("id", name)
            context_lines.append(name)
            
            # Track browsing history when advisor is displayed
            username = st.session_state.get("username")
            if username:
                add_to_history(username, "advisor", advisor_id, name)
            
            # Add badge for national project participation
            national_badge = ""
            if a.get("national_projects", False):
                national_badge = " 🇨🇳"
            
            st.markdown(f"### {name}{national_badge} — {a.get('department','')}")
            st.write(a.get("research", ""))
            
            # Show national projects if available
            if a.get("national_projects", False):
                with st.expander("🇨🇳 国家重大项目参与情况"):
                    national_projects_info = a.get("national_projects_info", "")
                    if national_projects_info:
                        st.info(national_projects_info)
                    else:
                        st.info("该导师参与国家重大科研项目，具体信息请访问导师主页查看")
            
            if a.get("homepage"):
                st.markdown(f"[主页]({a.get('homepage')})")
            revs = a.get("reviews", []) or []
            if revs:
                st.markdown("**学生评价（已发布）**")
                for r in revs[:5]:
                    st.markdown(format_review(r))
            else:
                st.info("尚无已发布评价")

            with st.expander("给导师提交评价（进入待审核）"):
                safe_name = str(name).replace(" ", "_")
                reviewer = st.text_input(
                    f"你的名字（可选） - 导师：{name}",
                    key=f"advisor_tab_rev_name_{safe_name}_{idx}",
                )
                rating = st.slider(
                    "评分（1-5）",
                    1,
                    5,
                    5,
                    key=f"advisor_tab_rev_rating_{safe_name}_{idx}",
                )
                # Add academic integrity rating
                academic_integrity = st.slider(
                    "学术诚信指导（1-5）",
                    1,
                    5,
                    5,
                    key=f"advisor_tab_integrity_{safe_name}_{idx}",
                    help="评价导师在学术规范、诚信指导方面的表现"
                )
                comment = st.text_area(
                    "评价内容",
                    key=f"advisor_tab_rev_comment_{safe_name}_{idx}",
                    height=120,
                )
                if st.button(
                    "提交（进入待审核）",
                    key=f"advisor_tab_submit_rev_{safe_name}_{idx}",
                ):
                    if not comment.strip():
                        st.warning("请输入评价内容")
                    else:
                        # Include academic integrity in review
                        enhanced_comment = f"{comment}\n\n【学术诚信指导评分：{academic_integrity}/5】"
                        pid = submit_advisor_review_pending(
                            KB_PATH,
                            KB,
                            advisor_name=name,
                            reviewer=reviewer,
                            rating=rating,
                            comment=enhanced_comment,
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
        "advisors",
        "导师匹配",
        ai_agent,
        context="当前检索关键词：" + (q or "未输入") + "，匹配导师：" + ", ".join(context_lines[:15]),
    )

# -*- coding: utf-8 -*-
"""
Tab 4: Job search & learning paths with AI-based career recommendations.
"""

import os
import json
import math
from typing import Dict, Any, List
import streamlit as st

from utils.recommend import (
    recommend_careers_by_interests_and_location,
    generate_learning_path_for_career,
)
from utils.knowledge_loader import get_alumni_cases, get_jds
from shared.ai_helpers import (
    render_tab_ai_helper,
    render_career_ai_summary,
    render_career_chat,
    safe_rerun,
)
from shared.config import CAREER_FEEDBACK_PATH
from utils.database import is_using_database, get_data_store


def load_career_feedback() -> Dict[str, Dict[str, Any]]:
    """Load career feedback data from database or JSON file."""
    # Try to load from database first if using PostgreSQL
    if is_using_database():
        try:
            store = get_data_store()
            if store:
                return store.get_career_feedback()
        except Exception as e:
            print(f"[career] 从数据库加载职业反馈失败: {e}")
    
    # Fallback to JSON file
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(CAREER_FEEDBACK_PATH):
        return {}
    try:
        with open(CAREER_FEEDBACK_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_career_feedback(data: Dict[str, Dict[str, Any]]):
    """Save career feedback data to database and JSON file."""
    # Save to database if using PostgreSQL
    if is_using_database():
        try:
            store = get_data_store()
            if store:
                for career_name, feedback in data.items():
                    store.set_career_feedback(
                        career_name, 
                        feedback.get('like', 0), 
                        feedback.get('dislike', 0)
                    )
        except Exception as e:
            print(f"[career] 保存职业反馈到数据库失败: {e}")
    
    # Also save to JSON file as backup
    os.makedirs("data", exist_ok=True)
    tmp = CAREER_FEEDBACK_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CAREER_FEEDBACK_PATH)


def add_career_feedback(career_name: str, feedback_type: str):
    """Add like/dislike feedback for a career."""
    # Update in database if using PostgreSQL
    if is_using_database():
        try:
            store = get_data_store()
            if store:
                like_delta = 1 if feedback_type == "like" else 0
                dislike_delta = 1 if feedback_type == "dislike" else 0
                store.update_career_feedback(career_name, like_delta, dislike_delta)
                return  # Success, no need to update JSON
        except Exception as e:
            print(f"[career] 更新数据库职业反馈失败: {e}")
    
    # Fallback to JSON file
    data = load_career_feedback()
    item = data.get(career_name, {"like": 0, "dislike": 0})
    if feedback_type == "like":
        item["like"] = int(item.get("like", 0)) + 1
    elif feedback_type == "dislike":
        item["dislike"] = int(item.get("dislike", 0)) + 1
    data[career_name] = item
    save_career_feedback(data)


def render_career_tab(KB: Dict[str, Any], ai_agent):
    """Render the career/job search tab."""
    st.header("💼 求职（智能职业推荐与学习路径）")

    interests = st.session_state.get("user_interests", [])
    location = st.session_state.get("work_location", "全国")

    st.markdown(
        f"📍 工作地区: **{location}** | 🎯 兴趣标签: **{', '.join(interests)}**"
    )
    
    # Ideological & Political Education: Career Value Guidance
    with st.expander("🎯 职业价值观引导", expanded=False):
        st.markdown("""
        **青年职业价值观引导**
        
        作为杭电学子，在职业规划时，可以关注以下国家战略重点领域：
        
        - 🌾 **乡村振兴**：投身基层，服务农村现代化建设
        - 🔬 **芯片自主**：助力国家半导体产业自立自强
        - 🛡️ **网络安全**：守护国家网络空间安全
        - 🚀 **航天科技**：参与国家航天事业发展
        - ⚡ **能源电力**：支持国家能源战略转型
        
        💡 **提示**：选择职业时，可勾选"优先推荐国家重点领域岗位"，系统将为您匹配相关机会。
        """)
        
        # Career integrity guidance
        st.markdown("---")
        st.markdown("**📋 职业诚信提醒**")
        st.info("💼 简历造假风险：虚假学历、工作经历可能导致解约或法律责任")
        st.info("⚖️ 职场合规：遵守行业规范，尊重知识产权，维护职业操守")
    
    st.markdown("---")
    
    # Add preference for grassroots/state-owned enterprises
    if "career_prefer_national" not in st.session_state:
        st.session_state["career_prefer_national"] = False
    
    # Unified preference checkbox + Alumni cases button in same row
    col_pref1, col_pref2 = st.columns([3, 1])
    with col_pref1:
        prefer_national = st.checkbox(
            "🇨🇳 优先推荐国企/基层/国家战略领域/校招重点企业",
            value=st.session_state.get("career_prefer_national", False),
            key="career_prefer_national_checkbox",
            help="启用后，AI 推荐将优先匹配国家战略领域职业（乡村振兴、芯片自主、航天科技等），同时校招职位列表也将优先显示国企/央企岗位"
        )
        st.session_state["career_prefer_national"] = prefer_national
    with col_pref2:
        if st.button("ℹ️ 查看校友案例", key="view_alumni_cases"):
            st.session_state["show_alumni_cases"] = not st.session_state.get("show_alumni_cases", False)
            safe_rerun()
    
    # Show alumni success stories
    if st.session_state.get("show_alumni_cases", False):
        with st.expander("🌟 杭电校友扎根重点领域典型案例", expanded=True):
            alumni_cases = get_alumni_cases(KB)
            if not alumni_cases:
                st.info("暂无校友案例数据。管理员可在后台添加案例。")
                # Keep the default cases as fallback
                st.markdown("""
                **案例一：投身航天科技，逐梦星辰大海**
                
                杭电2015届电子信息专业校友李明（化名），毕业后加入中国航天科技集团，
                参与北斗卫星导航系统研发工作。从基层技术岗做起，潜心钻研卫星通信技术，
                现已成长为项目技术骨干。他说："能为国家航天事业贡献力量，是我最大的荣耀。"
                
                ---
                
                **案例二：扎根基层，服务乡村振兴**
                
                杭电2017届计算机专业校友张华（化名），选择回到家乡参与"数字乡村"建设，
                运用大数据和物联网技术帮助农村实现智慧农业升级。三年时间，她带领团队
                帮助当地农产品销售额增长300%，用科技助力乡村振兴。
                
                ---
                
                **案例三：攻坚芯片技术，突破"卡脖子"难题**
                
                杭电2016届微电子专业校友王强（化名），加入国内某芯片设计公司，
                专注于高性能处理器研发。面对国外技术封锁，他和团队夜以继日攻关，
                终于突破关键技术瓶颈，为国产芯片自主可控贡献了智慧。
                """)
            else:
                for case in alumni_cases:
                    title = case.get("title", "")
                    field = case.get("field", "")
                    name = case.get("name", "")
                    year = case.get("year", "")
                    major = case.get("major", "")
                    content = case.get("content", "")
                    
                    st.markdown(f"**{title}**")
                    if year and major:
                        st.markdown(f"_杭电{year}{major}校友{name}_")
                    st.markdown(content)
                    if field:
                        st.caption(f"🇨🇳 重点领域：{field}")
                    st.markdown("---")
            
            if st.button("收起案例", key="hide_alumni_cases"):
                st.session_state["show_alumni_cases"] = False
                safe_rerun()
    
    st.markdown("---")
    
    # === Campus Recruitment Job Display Section ===
    st.subheader("🎓 校招职位展示")
    st.markdown("来自知识库的校招职位信息，助你了解就业市场需求。")
    
    jds_data = get_jds(KB)
    
    if jds_data:
        # Filter section
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            # Get unique companies
            companies = sorted(set(j.get("company", "") for j in jds_data if j.get("company")))
            companies.insert(0, "全部公司")
            selected_company_filter = st.selectbox("按公司筛选", companies, key="jd_company_filter")
        
        with col_f2:
            # Keyword search
            jd_search = st.text_input("🔎 搜索职位/技能", placeholder="输入职位名称或技能...", key="jd_search")
        
        with col_f3:
            pass  # Space reserved for future filter options
        
        # Apply filters
        filtered_jds = jds_data.copy()
        
        # Filter by company
        if selected_company_filter != "全部公司":
            filtered_jds = [j for j in filtered_jds if j.get("company") == selected_company_filter]
        
        # Filter by keyword search
        if jd_search.strip():
            search_lower = jd_search.strip().lower()
            filtered_jds = [j for j in filtered_jds 
                          if search_lower in j.get("company", "").lower()
                          or search_lower in j.get("position", "").lower()
                          or search_lower in j.get("jd", "").lower()
                          or any(search_lower in skill.lower() for skill in j.get("skills", []) if isinstance(j.get("skills"), list))]
        
        # National strategic keywords for prioritization
        NATIONAL_KEYWORDS = ["国家电网", "航天", "中国移动", "中国电信", "中国联通", "华为", 
                            "中兴", "中芯", "紫光", "国企", "央企", "研究院", "研究所",
                            "兵器", "航空", "船舶", "电子科技", "核工业", "能源"]
        
        # Add national priority score
        for j in filtered_jds:
            company = j.get("company", "").lower()
            position = j.get("position", "").lower()
            score = sum(1 for kw in NATIONAL_KEYWORDS if kw in company or kw in position)
            j["national_score"] = score
        
        # Sort by national score if preference is enabled (use unified preference)
        prefer_national_unified = st.session_state.get("career_prefer_national", False)
        if prefer_national_unified:
            filtered_jds = sorted(filtered_jds, key=lambda x: x.get("national_score", 0), reverse=True)
        
        # Pagination settings
        ITEMS_PER_PAGE = 5
        total_items = len(filtered_jds)
        total_pages = max(1, math.ceil(total_items / ITEMS_PER_PAGE))
        
        # Initialize page state
        if "jd_page" not in st.session_state:
            st.session_state["jd_page"] = 1
        
        current_page = st.session_state["jd_page"]
        
        # Ensure current page is valid
        if current_page > total_pages:
            current_page = total_pages
            st.session_state["jd_page"] = current_page
        
        # Display count
        st.info(f"找到 {total_items} 条职位信息 | 第 {current_page}/{total_pages} 页")
        
        # Calculate slice indices
        start_idx = (current_page - 1) * ITEMS_PER_PAGE
        end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)
        
        # Display current page items
        for idx, jd in enumerate(filtered_jds[start_idx:end_idx], start=start_idx + 1):
            company = jd.get("company", "未知公司")
            position = jd.get("position", "未知职位")
            jd_desc = jd.get("jd", "")
            skills = jd.get("skills", [])
            link = jd.get("link", "")
            is_national = jd.get("national_score", 0) > 0
            
            # Add national badge
            national_badge = " 🇨🇳" if is_national else ""
            
            with st.expander(f"📌 {company} - {position}{national_badge}", expanded=(idx == start_idx + 1)):
                if is_national:
                    st.success("🎯 **校招重点企业** - 国企/央企/国家战略领域企业")
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown("**职位描述：**")
                    if jd_desc:
                        st.markdown(jd_desc)
                    else:
                        st.markdown("_暂无详细描述_")
                    
                    if skills:
                        st.markdown("**技能要求：**")
                        if isinstance(skills, list):
                            for skill in skills:
                                st.markdown(f"- {skill}")
                        else:
                            st.markdown(f"- {skills}")
                
                with col2:
                    st.markdown("**公司：**")
                    st.markdown(f"🏢 {company}")
                    st.markdown("**职位：**")
                    st.markdown(f"💼 {position}")
                    if link:
                        st.markdown(f"[🔗 查看招聘详情]({link})")
        
        # Pagination controls
        st.markdown("---")
        col_prev, col_page, col_next = st.columns([1, 2, 1])
        
        with col_prev:
            if st.button("⬅️ 上一页", key="jd_prev_page", disabled=(current_page <= 1)):
                st.session_state["jd_page"] = current_page - 1
                safe_rerun()
        
        with col_page:
            # Page number input
            new_page = st.number_input(
                "跳转到页码",
                min_value=1,
                max_value=total_pages,
                value=current_page,
                step=1,
                key="jd_page_input"
            )
            if new_page != current_page:
                st.session_state["jd_page"] = new_page
                safe_rerun()
        
        with col_next:
            if st.button("下一页 ➡️", key="jd_next_page", disabled=(current_page >= total_pages)):
                st.session_state["jd_page"] = current_page + 1
                safe_rerun()
    else:
        st.info("暂无校招职位数据。管理员可在后台「💼 职位描述管理」中添加职位信息。")
    
    st.markdown("---")
    
    # === AI Career Recommendation Section ===
    st.subheader("🤖 AI 职业推荐")

    force_refresh = st.checkbox(
        "强制重新生成职业推荐与学习路径", key="career_force_refresh"
    )

    if st.button("💼 智能推荐职业 & 学习路径", key="career_recommend_btn"):
        if not interests:
            st.warning("请先在侧边栏选择兴趣标签")
        else:
            if st.session_state.get("career_recommendations") and not force_refresh:
                st.info(
                    "已存在上一轮职业推荐与学习路径，向下滚动即可查看。如需重新生成，请勾选『强制重新生成职业推荐与学习路径』。"
                )
            else:
                with st.spinner("正在生成职业推荐与学习路径..."):
                    prioritize_national_strategic = st.session_state.get("career_prefer_national", False)
                    careers = recommend_careers_by_interests_and_location(
                        interests, location, prioritize_national_strategic=prioritize_national_strategic
                    )
                    st.session_state["career_recommendations"] = careers

                    learning_paths = {}
                    for i, career_info in enumerate(careers):
                        career = career_info.get("career", "")
                        st.info(
                            f"正在为『{career}』生成学习路径... ({i+1}/{len(careers)})"
                        )
                        path = generate_learning_path_for_career(
                            career,
                            interests,
                            current_level="初级",
                            agent=ai_agent,
                        )
                        learning_paths[career] = path
                    st.session_state["learning_paths"] = learning_paths

                if careers:
                    st.success(f"✅ 已推荐 {len(careers)} 个职业方向")
                    safe_rerun()
                else:
                    st.info("暂无匹配的职业，请调整兴趣标签")

    st.markdown("---")

    careers = st.session_state.get("career_recommendations", [])
    if careers:
        st.subheader(f"🎯 推荐职业方向（{len(careers)} 个）")
        for i, career_info in enumerate(careers):
            career = career_info.get("career", "")
            skills = career_info.get("skills", [])
            salary = career_info.get("salary", "")
            companies = career_info.get("companies", "")
            is_national_strategic = career_info.get("national_strategic", False)
            strategic_field = career_info.get("strategic_field", "")
            
            # Add badge for national strategic positions
            title_suffix = ""
            if is_national_strategic:
                title_suffix = f" 🇨🇳 {strategic_field}"

            with st.expander(f"📌 {career}{title_suffix}（{salary}）", expanded=(i == 0)):
                # Show strategic position highlight
                if is_national_strategic:
                    st.info(f"🎯 **国家战略重点领域：{strategic_field}** - 投身国家重点领域，实现个人价值与国家需求的统一")
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown("**技能需求：**")
                    for skill in skills:
                        st.markdown(f"- {skill}")
                    st.markdown(f"**薪资范围：** {salary}")
                    st.markdown(f"**热门公司：** {companies}")
                    
                    # Show matching JD positions from knowledge base
                    if jds_data:
                        # Find matching JDs based on career name or skills
                        career_lower = career.lower()
                        matching_jds = []
                        for jd in jds_data:
                            jd_position = jd.get("position", "").lower()
                            jd_skills = [s.lower() for s in jd.get("skills", []) if isinstance(jd.get("skills"), list)]
                            # Match by position name or skill overlap
                            skill_match = any(skill.lower() in jd_position or any(skill.lower() in js for js in jd_skills) for skill in skills)
                            position_match = any(kw in jd_position for kw in career_lower.split())
                            if skill_match or position_match:
                                matching_jds.append(jd)
                        
                        if matching_jds:
                            st.markdown("**📋 校招企业岗位（来自知识库）：**")
                            for jd in matching_jds[:3]:  # Show top 3 matches
                                jd_company = jd.get("company", "")
                                jd_position = jd.get("position", "")
                                jd_link = jd.get("link", "")
                                if jd_link:
                                    st.markdown(f"- 🏢 **{jd_company}** - [{jd_position}]({jd_link})")
                                else:
                                    st.markdown(f"- 🏢 **{jd_company}** - {jd_position}")
                
                with col2:
                    st.markdown("**推荐程度**")
                    st.markdown("⭐⭐⭐⭐⭐")

                fb_col1, fb_col2 = st.columns(2)
                with fb_col1:
                    if st.button("👍 这个方向适合我", key=f"career_like_{i}"):
                        add_career_feedback(career, "like")
                        st.success("已记录你的反馈：适合你")
                with fb_col2:
                    if st.button("👎 不太适合我", key=f"career_dislike_{i}"):
                        add_career_feedback(career, "dislike")
                        st.info("已记录你的反馈：不太适合")

                st.markdown("---")
                st.markdown(f"### 📚 {career} 学习路径")
                learning_paths = st.session_state.get("learning_paths", {})
                if career in learning_paths:
                    st.markdown(learning_paths[career])
                else:
                    st.info("正在加载学习路径...")
    else:
        st.info("点击『💼 智能推荐职业 & 学习路径』按钮查看推荐")

    render_career_ai_summary(ai_agent)
    render_career_chat(ai_agent)
    render_tab_ai_helper("career_tab", "求职页面（补充提问）", ai_agent)

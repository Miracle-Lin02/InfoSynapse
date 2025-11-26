# -*- coding: utf-8 -*-
"""
Tab 8: Admin & moderation dashboard, KB editing, feedback stats.
"""

import math
from typing import Dict, Any
import streamlit as st
import pandas as pd

from utils.knowledge_loader import (
    load_knowledge_base,
    get_pending_reviews,
    approve_pending_review,
    reject_pending_review,
    get_moderation_log,
    add_course,
    delete_course,
    update_course,
    add_advisor,
    delete_advisor,
    update_advisor,
    add_practice,
    delete_practice,
    update_practice,
    get_alumni_cases,
    add_alumni_case,
    update_alumni_case,
    delete_alumni_case,
    get_jds,
    add_jd,
    update_jd,
    delete_jd,
    refresh_kb_from_database,
)
from utils.database import is_using_database
from utils.auth import list_users
from utils.notify import (
    annotate_moderation_log_with_admin,
    notify_admins_moderation_action,
)
from shared.profiles import load_user_profiles
from shared.ai_helpers import render_tab_ai_helper, safe_rerun
from tabs.career import load_career_feedback

# Import notification utilities
try:
    from utils.notifications import add_notification
except Exception:
    add_notification = None


def render_admin_tab(KB_PATH: str, KB: Dict[str, Any], ai_agent, ADMIN_PASS: str):
    """Render the admin & moderation tab."""
    st.header("🔧 KB 管理与审核（仅管理员）")
    if not ADMIN_PASS:
        st.error(
            "ADMIN_PASS 未配置！请在 .streamlit/secrets.toml 或环境变量设置 ADMIN_PASS 来启用审核功能。"
        )
    if not st.session_state.get("admin_authenticated", False):
        st.subheader("管理员登录")
        admin_user = st.text_input("管理员用户名（记录用）", key="admin_login_user")
        admin_pwd = st.text_input(
            "管理员口令", type="password", key="admin_login_pwd"
        )
        if st.button("登录"):
            if admin_pwd and admin_pwd == ADMIN_PASS:
                st.session_state["admin_authenticated"] = True
                st.session_state["admin_user"] = admin_user or "admin"
                st.success(f"管理员 {st.session_state['admin_user']} 已登录")
                safe_rerun()
            else:
                st.error("口令错误")
    else:
        st.success(f"管理员：{st.session_state.get('admin_user')}")
        if st.button("退出管理员"):
            st.session_state["admin_authenticated"] = False
            st.session_state["admin_user"] = ""
            safe_rerun()

        # Database status and refresh button
        col_db1, col_db2 = st.columns([3, 1])
        with col_db1:
            if is_using_database():
                st.info("🗄️ **数据源: PostgreSQL 数据库** - 点击刷新按钮从数据库同步最新数据")
            else:
                st.info("📄 **数据源: JSON 文件**")
        with col_db2:
            if st.button("🔄 刷新数据", help="从数据库重新加载最新数据，用于同步外部更改"):
                # Force reload KB from database and update session state
                new_kb = load_knowledge_base(KB_PATH)
                # Update KB dict in-place so all references get updated
                KB.clear()
                KB.update(new_kb)
                # Also update session state
                st.session_state["_kb_data"] = new_kb
                st.success("✅ 数据已从数据库重新加载")
                safe_rerun()

        st.markdown("### 全局统计")
        profiles = load_user_profiles()
        all_users = list_users()
        user_count = len(all_users) if isinstance(all_users, list) else 0
        pending = get_pending_reviews(KB)
        modlog = get_moderation_log(KB)

        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("注册用户数", user_count)
        with col_s2:
            st.metric("待审核评价数", len(pending or []))
        with col_s3:
            st.metric("审核日志条数", len(modlog or []))

        st.markdown("---")
        st.markdown("### 职业推荐反馈统计")
        fb_data = load_career_feedback()
        if not fb_data:
            st.info("暂时还没有学生对职业推荐给出反馈。")
        else:
            fb_rows = []
            for name, v in fb_data.items():
                fb_rows.append(
                    {
                        "职业": name,
                        "觉得适合(👍)": int(v.get("like", 0)),
                        "觉得不适合(👎)": int(v.get("dislike", 0)),
                    }
                )
            fb_df = pd.DataFrame(fb_rows).sort_values(
                by="觉得适合(👍)", ascending=False
            )
            st.dataframe(fb_df, use_container_width=True)

        st.markdown("---")
        st.markdown("### 📚 知识库管理")
        kb_tabs = st.tabs(
            [
                "📊 知识库管理",
                "📢 系统公告",
            ]
        )

        # Tab 0: Graphical Knowledge Base Management
        with kb_tabs[0]:
            st.subheader("📊 知识库管理（图形化界面）")
            st.markdown("""
            在此页面可以通过表格形式查看、编辑、添加和删除知识库中的所有内容。
            支持通过Excel、CSV和JSON文件批量导入数据。
            """)
            
            # Sub-tabs for different data types
            kb_mgmt_tabs = st.tabs([
                "📚 课程管理",
                "👨‍🏫 导师管理",
                "🏫 校内实践管理",
                "🎓 校友案例管理",
                "💼 职位描述管理"
            ])
            
            # === Course Management Tab ===
            with kb_mgmt_tabs[0]:
                st.markdown("#### 📚 课程数据管理")
                
                # Data display section
                courses_data = KB.get("courses", {})
                if courses_data:
                    # Select major to view
                    majors_list = list(courses_data.keys())
                    selected_major = st.selectbox(
                        "选择专业查看课程",
                        ["全部"] + majors_list,
                        key="kb_mgmt_course_major"
                    )
                    
                    # Build dataframe for display
                    all_courses = []
                    if selected_major == "全部":
                        for major, course_list in courses_data.items():
                            for c in course_list:
                                all_courses.append({
                                    "专业": major,
                                    "课程代码": c.get("code", ""),
                                    "课程名称": c.get("name", ""),
                                    "课程层次": c.get("level", ""),
                                    "先修课程": c.get("prereq", ""),
                                    "链接": c.get("link", ""),
                                    "思政课程": "是" if c.get("ideological") else "否"
                                })
                    else:
                        for c in courses_data.get(selected_major, []):
                            all_courses.append({
                                "专业": selected_major,
                                "课程代码": c.get("code", ""),
                                "课程名称": c.get("name", ""),
                                "课程层次": c.get("level", ""),
                                "先修课程": c.get("prereq", ""),
                                "链接": c.get("link", ""),
                                "思政课程": "是" if c.get("ideological") else "否"
                            })
                    
                    if all_courses:
                        # Pagination for courses
                        COURSE_PER_PAGE = 10
                        total_courses = len(all_courses)
                        total_course_pages = max(1, math.ceil(total_courses / COURSE_PER_PAGE))
                        
                        if "admin_course_page" not in st.session_state:
                            st.session_state["admin_course_page"] = 1
                        
                        course_page = st.session_state["admin_course_page"]
                        if course_page > total_course_pages:
                            course_page = total_course_pages
                            st.session_state["admin_course_page"] = course_page
                        
                        st.markdown(f"**共 {total_courses} 门课程** | 第 {course_page}/{total_course_pages} 页")
                        
                        # Slice for current page
                        course_start = (course_page - 1) * COURSE_PER_PAGE
                        course_end = min(course_start + COURSE_PER_PAGE, total_courses)
                        df_courses = pd.DataFrame(all_courses[course_start:course_end])
                        
                        # Display as interactive table
                        st.dataframe(
                            df_courses,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "链接": st.column_config.LinkColumn("链接", display_text="打开")
                            }
                        )
                        
                        # Pagination controls
                        if total_course_pages > 1:
                            col_cp, col_cn, col_cj = st.columns([1, 1, 2])
                            with col_cp:
                                if st.button("⬅️ 上一页", key="course_prev", disabled=(course_page <= 1)):
                                    st.session_state["admin_course_page"] = course_page - 1
                                    safe_rerun()
                            with col_cn:
                                if st.button("下一页 ➡️", key="course_next", disabled=(course_page >= total_course_pages)):
                                    st.session_state["admin_course_page"] = course_page + 1
                                    safe_rerun()
                            with col_cj:
                                new_cpage = st.number_input("跳转页", min_value=1, max_value=total_course_pages, value=course_page, key="course_jump")
                                if new_cpage != course_page:
                                    st.session_state["admin_course_page"] = new_cpage
                                    safe_rerun()
                        
                        # Quick add course form
                        st.markdown("---")
                        st.markdown("##### ➕ 快速添加课程")
                        with st.form("quick_add_course_form", clear_on_submit=True):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                new_major = st.selectbox("专业", majors_list, key="qadd_major")
                                new_code = st.text_input("课程代码", key="qadd_code")
                            with col2:
                                new_name = st.text_input("课程名称", key="qadd_name")
                                new_level = st.selectbox("课程层次", ["基础", "进阶", "选修", "价值引领类", "其他"], key="qadd_level")
                            with col3:
                                new_prereq = st.text_input("先修课程", key="qadd_prereq")
                                new_link = st.text_input("链接", key="qadd_link")
                            new_ideo = st.checkbox("思政课程", key="qadd_ideo")
                            
                            if st.form_submit_button("➕ 添加课程", type="primary"):
                                if new_code.strip() and new_name.strip():
                                    course_data = {
                                        "code": new_code.strip(),
                                        "name": new_name.strip(),
                                        "level": new_level,
                                        "prereq": new_prereq.strip(),
                                        "link": new_link.strip(),
                                        "outline": "",
                                        "reviews": [],
                                    }
                                    if new_ideo:
                                        course_data["ideological"] = True
                                    ok = add_course(KB_PATH, KB, new_major, course_data)
                                    if ok:
                                        st.success(f"✅ 已添加课程：{new_code} {new_name}")
                                        KB.clear()
                                        KB.update(load_knowledge_base(KB_PATH))
                                        safe_rerun()
                                    else:
                                        st.error("添加失败")
                                else:
                                    st.warning("课程代码和名称为必填")
                        
                        # Quick edit course section
                        st.markdown("---")
                        st.markdown("##### ✏️ 编辑课程")
                        edit_major = st.selectbox("选择专业", majors_list, key="qedit_major")
                        edit_course_list = courses_data.get(edit_major, [])
                        if edit_course_list:
                            edit_course_options = [c.get("code", "") + " - " + c.get("name", "") for c in edit_course_list]
                            edit_course_idx = st.selectbox("选择要编辑的课程", range(len(edit_course_options)), 
                                format_func=lambda x: edit_course_options[x], key="qedit_course")
                            selected_course = edit_course_list[edit_course_idx]
                            
                            with st.form("quick_edit_course_form"):
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    edit_code = st.text_input("课程代码", value=selected_course.get("code", ""), key="qedit_code")
                                    edit_name = st.text_input("课程名称", value=selected_course.get("name", ""), key="qedit_name")
                                with col2:
                                    edit_level = st.selectbox("课程层次", ["基础", "进阶", "选修", "价值引领类", "其他"], 
                                        index=["基础", "进阶", "选修", "价值引领类", "其他"].index(selected_course.get("level", "其他")) if selected_course.get("level") in ["基础", "进阶", "选修", "价值引领类", "其他"] else 4,
                                        key="qedit_level")
                                    edit_prereq = st.text_input("先修课程", value=selected_course.get("prereq", ""), key="qedit_prereq")
                                with col3:
                                    edit_link = st.text_input("链接", value=selected_course.get("link", ""), key="qedit_link")
                                edit_ideo = st.checkbox("思政课程", value=selected_course.get("ideological", False), key="qedit_ideo")
                                
                                if st.form_submit_button("💾 保存修改", type="primary"):
                                    if edit_code.strip() and edit_name.strip():
                                        updated_course = {
                                            "code": edit_code.strip(),
                                            "name": edit_name.strip(),
                                            "level": edit_level,
                                            "prereq": edit_prereq.strip(),
                                            "link": edit_link.strip(),
                                            "outline": selected_course.get("outline", ""),
                                        }
                                        if edit_ideo:
                                            updated_course["ideological"] = True
                                        ok = update_course(KB_PATH, KB, edit_major, selected_course.get("code"), updated_course)
                                        if ok:
                                            st.success(f"✅ 已更新课程：{edit_code} {edit_name}")
                                            KB.clear()
                                            KB.update(load_knowledge_base(KB_PATH))
                                            safe_rerun()
                                        else:
                                            st.error("更新失败")
                                    else:
                                        st.warning("课程代码和名称为必填")
                        else:
                            st.info("该专业下暂无课程可编辑")
                        
                        # Quick delete section
                        st.markdown("---")
                        st.markdown("##### 🗑️ 删除课程")
                        with st.form("quick_delete_course_form"):
                            del_major = st.selectbox("选择专业", majors_list, key="qdel_major")
                            del_course_list = [c.get("code", "") + " - " + c.get("name", "") for c in courses_data.get(del_major, [])]
                            if del_course_list:
                                del_course = st.selectbox("选择要删除的课程", del_course_list, key="qdel_course")
                                if st.form_submit_button("🗑️ 删除课程", type="secondary"):
                                    del_code = del_course.split(" - ")[0]
                                    ok = delete_course(KB_PATH, KB, del_major, del_code)
                                    if ok:
                                        st.success(f"✅ 已删除课程：{del_course}")
                                        KB.clear()
                                        KB.update(load_knowledge_base(KB_PATH))
                                        safe_rerun()
                                    else:
                                        st.error("删除失败")
                            else:
                                st.info("该专业下暂无课程")
                                st.form_submit_button("🗑️ 删除课程", disabled=True)
                    else:
                        st.info("该专业下暂无课程数据")
                else:
                    st.info("知识库中暂无课程数据")
                
                # Import section
                st.markdown("---")
                st.markdown("##### 📥 批量导入课程")
                st.info("支持 Excel (.xlsx)、CSV、JSON 格式")
                
                uploaded_course_file = st.file_uploader(
                    "选择课程数据文件",
                    type=["xlsx", "csv", "json"],
                    key="kb_mgmt_course_upload"
                )
                
                if uploaded_course_file:
                    st.success(f"已选择文件: {uploaded_course_file.name}")
                    if st.button("🚀 导入课程数据", key="import_courses_btn"):
                        with st.spinner("正在导入..."):
                            try:
                                from utils.dashboard_analytics import import_from_file
                                file_content = uploaded_course_file.read()
                                result = import_from_file(
                                    file_content=file_content,
                                    filename=uploaded_course_file.name,
                                    data_type="courses",
                                    mode="merge"
                                )
                                if result.get("success"):
                                    st.success("✅ " + result.get("message", "导入成功！"))
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("❌ " + result.get("message", "导入失败"))
                            except Exception as e:
                                st.error(f"导入出错: {str(e)}")
            
            # === Advisor Management Tab ===
            with kb_mgmt_tabs[1]:
                st.markdown("#### 👨‍🏫 导师数据管理")
                
                advisors_data = KB.get("advisors", []) or []
                if advisors_data:
                    # Build dataframe for display
                    all_advisors = []
                    for a in advisors_data:
                        all_advisors.append({
                            "姓名": a.get("name", ""),
                            "学院/部门": a.get("department", ""),
                            "研究方向": a.get("research", ""),
                            "主页": a.get("homepage", ""),
                            "国家项目": "是" if a.get("national_projects") else "否"
                        })
                    
                    # Filter by department first
                    departments = sorted(set(a.get("department", "") for a in advisors_data if a.get("department")))
                    selected_dept = st.selectbox("按学院筛选", ["全部"] + departments, key="kb_mgmt_adv_dept")
                    
                    filtered_advisors = all_advisors
                    if selected_dept != "全部":
                        filtered_advisors = [a for a in all_advisors if a["学院/部门"] == selected_dept]
                    
                    # Pagination for advisors
                    ADV_PER_PAGE = 10
                    total_advisors = len(filtered_advisors)
                    total_adv_pages = max(1, math.ceil(total_advisors / ADV_PER_PAGE))
                    
                    if "admin_advisor_page" not in st.session_state:
                        st.session_state["admin_advisor_page"] = 1
                    
                    adv_page = st.session_state["admin_advisor_page"]
                    if adv_page > total_adv_pages:
                        adv_page = total_adv_pages
                        st.session_state["admin_advisor_page"] = adv_page
                    
                    st.markdown(f"**共 {total_advisors} 位导师** | 第 {adv_page}/{total_adv_pages} 页")
                    
                    # Slice for current page
                    adv_start = (adv_page - 1) * ADV_PER_PAGE
                    adv_end = min(adv_start + ADV_PER_PAGE, total_advisors)
                    df_advisors = pd.DataFrame(filtered_advisors[adv_start:adv_end])
                    
                    if not df_advisors.empty:
                        st.dataframe(
                            df_advisors,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "主页": st.column_config.LinkColumn("主页", display_text="打开")
                            }
                        )
                        
                        # Pagination controls
                        if total_adv_pages > 1:
                            col_ap, col_an, col_aj = st.columns([1, 1, 2])
                            with col_ap:
                                if st.button("⬅️ 上一页", key="adv_prev", disabled=(adv_page <= 1)):
                                    st.session_state["admin_advisor_page"] = adv_page - 1
                                    safe_rerun()
                            with col_an:
                                if st.button("下一页 ➡️", key="adv_next", disabled=(adv_page >= total_adv_pages)):
                                    st.session_state["admin_advisor_page"] = adv_page + 1
                                    safe_rerun()
                            with col_aj:
                                new_apage = st.number_input("跳转页", min_value=1, max_value=total_adv_pages, value=adv_page, key="adv_jump")
                                if new_apage != adv_page:
                                    st.session_state["admin_advisor_page"] = new_apage
                                    safe_rerun()
                    
                    # Quick add advisor form
                    st.markdown("---")
                    st.markdown("##### ➕ 快速添加导师")
                    with st.form("quick_add_advisor_form", clear_on_submit=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            adv_name = st.text_input("导师姓名", key="qadd_adv_name")
                            adv_dept = st.text_input("学院/部门", value="计算机学院", key="qadd_adv_dept")
                        with col2:
                            adv_research = st.text_input("研究方向", key="qadd_adv_research")
                            adv_homepage = st.text_input("个人主页", key="qadd_adv_homepage")
                        adv_national = st.checkbox("参与国家重大项目", key="qadd_adv_national")
                        
                        if st.form_submit_button("➕ 添加导师", type="primary"):
                            if adv_name.strip():
                                advisor_data = {
                                    "name": adv_name.strip(),
                                    "department": adv_dept.strip(),
                                    "research": adv_research.strip(),
                                    "homepage": adv_homepage.strip(),
                                    "reviews": [],
                                    "national_projects": adv_national,
                                }
                                ok = add_advisor(KB_PATH, KB, advisor_data)
                                if ok:
                                    st.success(f"✅ 已添加导师：{adv_name}")
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("添加失败")
                            else:
                                st.warning("导师姓名为必填")
                    
                    # Quick edit section
                    st.markdown("---")
                    st.markdown("##### ✏️ 编辑导师")
                    advisor_names_for_edit = [a.get("name", "") for a in advisors_data if a.get("name")]
                    if advisor_names_for_edit:
                        edit_advisor_name = st.selectbox("选择要编辑的导师", advisor_names_for_edit, key="qedit_advisor")
                        # Find the selected advisor
                        selected_advisor = next((a for a in advisors_data if a.get("name") == edit_advisor_name), None)
                        
                        if selected_advisor:
                            with st.form("quick_edit_advisor_form"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    edit_adv_name = st.text_input("导师姓名", value=selected_advisor.get("name", ""), key="qedit_adv_name")
                                    edit_adv_dept = st.text_input("学院/部门", value=selected_advisor.get("department", ""), key="qedit_adv_dept")
                                with col2:
                                    edit_adv_research = st.text_input("研究方向", value=selected_advisor.get("research", ""), key="qedit_adv_research")
                                    edit_adv_homepage = st.text_input("个人主页", value=selected_advisor.get("homepage", ""), key="qedit_adv_homepage")
                                edit_adv_national = st.checkbox("参与国家重大项目", value=selected_advisor.get("national_projects", False), key="qedit_adv_national")
                                
                                if st.form_submit_button("💾 保存修改", type="primary"):
                                    if edit_adv_name.strip():
                                        updated_advisor = {
                                            "name": edit_adv_name.strip(),
                                            "department": edit_adv_dept.strip(),
                                            "research": edit_adv_research.strip(),
                                            "homepage": edit_adv_homepage.strip(),
                                            "national_projects": edit_adv_national,
                                        }
                                        ok = update_advisor(KB_PATH, KB, edit_advisor_name, updated_advisor)
                                        if ok:
                                            st.success(f"✅ 已更新导师：{edit_adv_name}")
                                            KB.clear()
                                            KB.update(load_knowledge_base(KB_PATH))
                                            safe_rerun()
                                        else:
                                            st.error("更新失败")
                                    else:
                                        st.warning("导师姓名为必填")
                    else:
                        st.info("暂无导师数据可编辑")
                    
                    # Quick delete section
                    st.markdown("---")
                    st.markdown("##### 🗑️ 删除导师")
                    with st.form("quick_delete_advisor_form"):
                        advisor_names = [a.get("name", "") for a in advisors_data if a.get("name")]
                        if advisor_names:
                            del_advisor = st.selectbox("选择要删除的导师", advisor_names, key="qdel_advisor")
                            if st.form_submit_button("🗑️ 删除导师", type="secondary"):
                                ok = delete_advisor(KB_PATH, KB, del_advisor)
                                if ok:
                                    st.success(f"✅ 已删除导师：{del_advisor}")
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("删除失败")
                        else:
                            st.info("暂无导师数据")
                            st.form_submit_button("🗑️ 删除导师", disabled=True)
                else:
                    st.info("知识库中暂无导师数据")
                
                # Import section
                st.markdown("---")
                st.markdown("##### 📥 批量导入导师")
                uploaded_advisor_file = st.file_uploader(
                    "选择导师数据文件",
                    type=["xlsx", "csv", "json"],
                    key="kb_mgmt_advisor_upload"
                )
                
                if uploaded_advisor_file:
                    st.success(f"已选择文件: {uploaded_advisor_file.name}")
                    if st.button("🚀 导入导师数据", key="import_advisors_btn"):
                        with st.spinner("正在导入..."):
                            try:
                                from utils.dashboard_analytics import import_from_file
                                file_content = uploaded_advisor_file.read()
                                result = import_from_file(
                                    file_content=file_content,
                                    filename=uploaded_advisor_file.name,
                                    data_type="advisors",
                                    mode="merge"
                                )
                                if result.get("success"):
                                    st.success("✅ " + result.get("message", "导入成功！"))
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("❌ " + result.get("message", "导入失败"))
                            except Exception as e:
                                st.error(f"导入出错: {str(e)}")
            
            # === Practice Management Tab ===
            with kb_mgmt_tabs[2]:
                st.markdown("#### 🏫 校内实践数据管理")
                
                practices_data = KB.get("practice", []) or []
                if practices_data:
                    # Build dataframe for display
                    all_practices = []
                    for p in practices_data:
                        all_practices.append({
                            "名称": p.get("name", ""),
                            "类型": p.get("type", ""),
                            "描述": p.get("desc", "")[:50] + "..." if len(p.get("desc", "")) > 50 else p.get("desc", ""),
                            "链接": p.get("link", "")
                        })
                    
                    # Filter by type first
                    practice_types = sorted(set(p.get("type", "") for p in practices_data if p.get("type")))
                    selected_type = st.selectbox("按类型筛选", ["全部"] + practice_types, key="kb_mgmt_prac_type")
                    
                    filtered_practices = all_practices
                    if selected_type != "全部":
                        filtered_practices = [p for p in all_practices if p["类型"] == selected_type]
                    
                    # Pagination for practices
                    PRAC_PER_PAGE = 10
                    total_practices = len(filtered_practices)
                    total_prac_pages = max(1, math.ceil(total_practices / PRAC_PER_PAGE))
                    
                    if "admin_practice_page" not in st.session_state:
                        st.session_state["admin_practice_page"] = 1
                    
                    prac_page = st.session_state["admin_practice_page"]
                    if prac_page > total_prac_pages:
                        prac_page = total_prac_pages
                        st.session_state["admin_practice_page"] = prac_page
                    
                    st.markdown(f"**共 {total_practices} 个实践项目** | 第 {prac_page}/{total_prac_pages} 页")
                    
                    # Slice for current page
                    prac_start = (prac_page - 1) * PRAC_PER_PAGE
                    prac_end = min(prac_start + PRAC_PER_PAGE, total_practices)
                    df_practices = pd.DataFrame(filtered_practices[prac_start:prac_end])
                    
                    if not df_practices.empty:
                        st.dataframe(
                            df_practices,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "链接": st.column_config.LinkColumn("链接", display_text="打开")
                            }
                        )
                        
                        # Pagination controls
                        if total_prac_pages > 1:
                            col_pp, col_pn, col_pj = st.columns([1, 1, 2])
                            with col_pp:
                                if st.button("⬅️ 上一页", key="prac_prev", disabled=(prac_page <= 1)):
                                    st.session_state["admin_practice_page"] = prac_page - 1
                                    safe_rerun()
                            with col_pn:
                                if st.button("下一页 ➡️", key="prac_next", disabled=(prac_page >= total_prac_pages)):
                                    st.session_state["admin_practice_page"] = prac_page + 1
                                    safe_rerun()
                            with col_pj:
                                new_ppage = st.number_input("跳转页", min_value=1, max_value=total_prac_pages, value=prac_page, key="prac_jump")
                                if new_ppage != prac_page:
                                    st.session_state["admin_practice_page"] = new_ppage
                                    safe_rerun()
                    
                    # Quick add practice form
                    st.markdown("---")
                    st.markdown("##### ➕ 快速添加实践项目")
                    with st.form("quick_add_practice_form", clear_on_submit=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            prac_name = st.text_input("实践名称", key="qadd_prac_name")
                            prac_type = st.text_input("类型（竞赛/实验室/社团/项目）", key="qadd_prac_type")
                        with col2:
                            prac_link = st.text_input("相关链接", key="qadd_prac_link")
                        prac_desc = st.text_area("实践简介", key="qadd_prac_desc", height=100)
                        
                        if st.form_submit_button("➕ 添加实践项目", type="primary"):
                            if prac_name.strip():
                                ok = add_practice(
                                    KB_PATH, KB,
                                    {
                                        "name": prac_name.strip(),
                                        "type": prac_type.strip(),
                                        "desc": prac_desc.strip(),
                                        "link": prac_link.strip(),
                                    }
                                )
                                if ok:
                                    st.success(f"✅ 已添加实践项目：{prac_name}")
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("添加失败")
                            else:
                                st.warning("实践名称为必填")
                    
                    # Quick edit practice section
                    st.markdown("---")
                    st.markdown("##### ✏️ 编辑实践项目")
                    practice_names_for_edit = [p.get("name", "") for p in practices_data if p.get("name")]
                    if practice_names_for_edit:
                        edit_practice_name = st.selectbox("选择要编辑的实践项目", practice_names_for_edit, key="qedit_practice")
                        selected_practice = next((p for p in practices_data if p.get("name") == edit_practice_name), None)
                        
                        if selected_practice:
                            with st.form("quick_edit_practice_form"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    edit_prac_name = st.text_input("实践名称", value=selected_practice.get("name", ""), key="qedit_prac_name")
                                    edit_prac_type = st.text_input("类型", value=selected_practice.get("type", ""), key="qedit_prac_type")
                                with col2:
                                    edit_prac_link = st.text_input("相关链接", value=selected_practice.get("link", ""), key="qedit_prac_link")
                                edit_prac_desc = st.text_area("实践简介", value=selected_practice.get("desc", ""), key="qedit_prac_desc", height=100)
                                
                                if st.form_submit_button("💾 保存修改", type="primary"):
                                    if edit_prac_name.strip():
                                        updated_practice = {
                                            "name": edit_prac_name.strip(),
                                            "type": edit_prac_type.strip(),
                                            "desc": edit_prac_desc.strip(),
                                            "link": edit_prac_link.strip(),
                                        }
                                        ok = update_practice(KB_PATH, KB, edit_practice_name, updated_practice)
                                        if ok:
                                            st.success(f"✅ 已更新实践项目：{edit_prac_name}")
                                            KB.clear()
                                            KB.update(load_knowledge_base(KB_PATH))
                                            safe_rerun()
                                        else:
                                            st.error("更新失败")
                                    else:
                                        st.warning("实践名称为必填")
                    else:
                        st.info("暂无实践项目可编辑")
                    
                    # Quick delete section
                    st.markdown("---")
                    st.markdown("##### 🗑️ 删除实践项目")
                    with st.form("quick_delete_practice_form"):
                        practice_names = [p.get("name", "") for p in practices_data if p.get("name")]
                        if practice_names:
                            del_practice = st.selectbox("选择要删除的实践项目", practice_names, key="qdel_practice")
                            if st.form_submit_button("🗑️ 删除实践项目", type="secondary"):
                                ok = delete_practice(KB_PATH, KB, del_practice)
                                if ok:
                                    st.success(f"✅ 已删除实践项目：{del_practice}")
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("删除失败")
                        else:
                            st.info("暂无实践项目数据")
                            st.form_submit_button("🗑️ 删除实践项目", disabled=True)
                else:
                    st.info("知识库中暂无校内实践数据")
                
                # Import section
                st.markdown("---")
                st.markdown("##### 📥 批量导入实践项目")
                uploaded_practice_file = st.file_uploader(
                    "选择实践项目数据文件",
                    type=["xlsx", "csv", "json"],
                    key="kb_mgmt_practice_upload"
                )
                
                if uploaded_practice_file:
                    st.success(f"已选择文件: {uploaded_practice_file.name}")
                    if st.button("🚀 导入实践项目数据", key="import_practices_btn"):
                        with st.spinner("正在导入..."):
                            try:
                                from utils.dashboard_analytics import import_from_file
                                file_content = uploaded_practice_file.read()
                                result = import_from_file(
                                    file_content=file_content,
                                    filename=uploaded_practice_file.name,
                                    data_type="practices",
                                    mode="merge"
                                )
                                if result.get("success"):
                                    st.success("✅ " + result.get("message", "导入成功！"))
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("❌ " + result.get("message", "导入失败"))
                            except Exception as e:
                                st.error(f"导入出错: {str(e)}")
            
            # === Alumni Cases Management Tab ===
            with kb_mgmt_tabs[3]:
                st.markdown("#### 🎓 校友案例数据管理")
                
                alumni_data = get_alumni_cases(KB)
                if alumni_data:
                    # Build dataframe for display
                    all_alumni = []
                    for a in alumni_data:
                        all_alumni.append({
                            "标题": a.get("title", ""),
                            "重点领域": a.get("field", ""),
                            "校友姓名": a.get("name", ""),
                            "毕业年份": a.get("year", ""),
                            "专业": a.get("major", ""),
                            "ID": a.get("id", "")
                        })
                    
                    st.markdown(f"**共 {len(all_alumni)} 个校友案例**")
                    df_alumni = pd.DataFrame(all_alumni)
                    
                    # Filter by field
                    fields = sorted(set(a.get("field", "") for a in alumni_data if a.get("field")))
                    selected_field = st.selectbox("按领域筛选", ["全部"] + fields, key="kb_mgmt_alumni_field")
                    
                    if selected_field != "全部":
                        df_alumni = df_alumni[df_alumni["重点领域"] == selected_field]
                    
                    # Hide ID column in display
                    st.dataframe(
                        df_alumni.drop(columns=["ID"]),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Quick add alumni case form
                    st.markdown("---")
                    st.markdown("##### ➕ 快速添加校友案例")
                    with st.form("quick_add_alumni_form", clear_on_submit=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            alum_title = st.text_input("案例标题", key="qadd_alum_title")
                            alum_field = st.selectbox(
                                "重点领域",
                                ["航天科技", "乡村振兴", "芯片自主", "网络安全", "能源电力", "其他"],
                                key="qadd_alum_field"
                            )
                            alum_name = st.text_input("校友姓名（可用化名）", key="qadd_alum_name")
                        with col2:
                            alum_year = st.text_input("毕业年份", key="qadd_alum_year")
                            alum_major = st.text_input("专业", key="qadd_alum_major")
                        alum_content = st.text_area("案例内容", key="qadd_alum_content", height=100)
                        
                        if st.form_submit_button("➕ 添加校友案例", type="primary"):
                            if alum_title.strip() and alum_content.strip():
                                case_data = {
                                    "title": alum_title.strip(),
                                    "field": alum_field,
                                    "name": alum_name.strip() if alum_name.strip() else "化名",
                                    "year": alum_year.strip(),
                                    "major": alum_major.strip(),
                                    "content": alum_content.strip(),
                                }
                                ok = add_alumni_case(KB_PATH, KB, case_data)
                                if ok:
                                    st.success(f"✅ 已添加校友案例：{alum_title}")
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("添加失败")
                            else:
                                st.warning("案例标题和内容为必填")
                    
                    # Quick edit alumni section
                    st.markdown("---")
                    st.markdown("##### ✏️ 编辑校友案例")
                    alumni_options_for_edit = [f"{a.get('title', '')} ({a.get('field', '')})" for a in alumni_data]
                    alumni_ids_for_edit = [a.get("id", "") for a in alumni_data]
                    if alumni_options_for_edit:
                        edit_alumni_idx = st.selectbox("选择要编辑的校友案例", range(len(alumni_options_for_edit)), 
                            format_func=lambda x: alumni_options_for_edit[x], key="qedit_alumni")
                        selected_alumni = alumni_data[edit_alumni_idx]
                        
                        with st.form("quick_edit_alumni_form"):
                            col1, col2 = st.columns(2)
                            with col1:
                                edit_alum_title = st.text_input("案例标题", value=selected_alumni.get("title", ""), key="qedit_alum_title")
                                edit_alum_field = st.selectbox(
                                    "重点领域",
                                    ["航天科技", "乡村振兴", "芯片自主", "网络安全", "能源电力", "其他"],
                                    index=["航天科技", "乡村振兴", "芯片自主", "网络安全", "能源电力", "其他"].index(selected_alumni.get("field", "其他")) if selected_alumni.get("field") in ["航天科技", "乡村振兴", "芯片自主", "网络安全", "能源电力", "其他"] else 5,
                                    key="qedit_alum_field"
                                )
                                edit_alum_name = st.text_input("校友姓名", value=selected_alumni.get("name", ""), key="qedit_alum_name")
                            with col2:
                                edit_alum_year = st.text_input("毕业年份", value=selected_alumni.get("year", ""), key="qedit_alum_year")
                                edit_alum_major = st.text_input("专业", value=selected_alumni.get("major", ""), key="qedit_alum_major")
                            edit_alum_content = st.text_area("案例内容", value=selected_alumni.get("content", ""), key="qedit_alum_content", height=100)
                            
                            if st.form_submit_button("💾 保存修改", type="primary"):
                                if edit_alum_title.strip() and edit_alum_content.strip():
                                    updated_case = {
                                        "title": edit_alum_title.strip(),
                                        "field": edit_alum_field,
                                        "name": edit_alum_name.strip() if edit_alum_name.strip() else "化名",
                                        "year": edit_alum_year.strip(),
                                        "major": edit_alum_major.strip(),
                                        "content": edit_alum_content.strip(),
                                    }
                                    ok = update_alumni_case(KB_PATH, KB, selected_alumni.get("id"), updated_case)
                                    if ok:
                                        st.success(f"✅ 已更新校友案例：{edit_alum_title}")
                                        KB.clear()
                                        KB.update(load_knowledge_base(KB_PATH))
                                        safe_rerun()
                                    else:
                                        st.error("更新失败")
                                else:
                                    st.warning("案例标题和内容为必填")
                    else:
                        st.info("暂无校友案例可编辑")
                    
                    # Quick delete section
                    st.markdown("---")
                    st.markdown("##### 🗑️ 删除校友案例")
                    with st.form("quick_delete_alumni_form"):
                        alumni_options = [f"{a.get('title', '')} ({a.get('field', '')})" for a in alumni_data]
                        alumni_ids = [a.get("id", "") for a in alumni_data]
                        if alumni_options:
                            del_idx = st.selectbox("选择要删除的校友案例", range(len(alumni_options)), 
                                format_func=lambda x: alumni_options[x], key="qdel_alumni")
                            if st.form_submit_button("🗑️ 删除校友案例", type="secondary"):
                                del_id = alumni_ids[del_idx]
                                ok = delete_alumni_case(KB_PATH, KB, del_id)
                                if ok:
                                    st.success(f"✅ 已删除校友案例：{alumni_options[del_idx]}")
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("删除失败")
                        else:
                            st.info("暂无校友案例数据")
                            st.form_submit_button("🗑️ 删除校友案例", disabled=True)
                else:
                    st.info("知识库中暂无校友案例数据")
                
                # Import section
                st.markdown("---")
                st.markdown("##### 📥 批量导入校友案例")
                uploaded_alumni_file = st.file_uploader(
                    "选择校友案例数据文件",
                    type=["xlsx", "csv", "json"],
                    key="kb_mgmt_alumni_upload"
                )
                
                if uploaded_alumni_file:
                    st.success(f"已选择文件: {uploaded_alumni_file.name}")
                    if st.button("🚀 导入校友案例数据", key="import_alumni_btn"):
                        with st.spinner("正在导入..."):
                            try:
                                from utils.dashboard_analytics import import_from_file
                                file_content = uploaded_alumni_file.read()
                                result = import_from_file(
                                    file_content=file_content,
                                    filename=uploaded_alumni_file.name,
                                    data_type="alumni_cases",
                                    mode="merge"
                                )
                                if result.get("success"):
                                    st.success("✅ " + result.get("message", "导入成功！"))
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("❌ " + result.get("message", "导入失败"))
                            except Exception as e:
                                st.error(f"导入出错: {str(e)}")
            
            # === JD (Job Description) Management Tab ===
            with kb_mgmt_tabs[4]:
                st.markdown("#### 💼 职位描述 (JD) 数据管理")
                
                jds_data = get_jds(KB)
                if jds_data:
                    # Build dataframe for display
                    all_jds = []
                    for j in jds_data:
                        all_jds.append({
                            "公司": j.get("company", ""),
                            "职位": j.get("position", ""),
                            "职位描述": j.get("jd", "")[:50] + "..." if len(j.get("jd", "")) > 50 else j.get("jd", ""),
                            "技能要求": ", ".join(j.get("skills", [])) if isinstance(j.get("skills"), list) else str(j.get("skills", "")),
                            "链接": j.get("link", "")
                        })
                    
                    st.markdown(f"**共 {len(all_jds)} 条职位描述**")
                    df_jds = pd.DataFrame(all_jds)
                    
                    # Filter by company
                    companies = sorted(set(j.get("company", "") for j in jds_data if j.get("company")))
                    selected_company = st.selectbox("按公司筛选", ["全部"] + companies, key="kb_mgmt_jd_company")
                    
                    if selected_company != "全部":
                        df_jds = df_jds[df_jds["公司"] == selected_company]
                    
                    st.dataframe(
                        df_jds,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "链接": st.column_config.LinkColumn("链接", display_text="打开")
                        }
                    )
                    
                    # Quick add JD form
                    st.markdown("---")
                    st.markdown("##### ➕ 快速添加职位描述")
                    with st.form("quick_add_jd_form", clear_on_submit=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            jd_company = st.text_input("公司名称", key="qadd_jd_company")
                            jd_position = st.text_input("职位名称", key="qadd_jd_position")
                        with col2:
                            jd_skills = st.text_input("技能要求（用逗号分隔）", key="qadd_jd_skills")
                            jd_link = st.text_input("招聘链接", key="qadd_jd_link")
                        jd_desc = st.text_area("职位描述", key="qadd_jd_desc", height=100)
                        
                        if st.form_submit_button("➕ 添加职位描述", type="primary"):
                            if jd_company.strip() and jd_position.strip():
                                skills_list = [s.strip() for s in jd_skills.split(",") if s.strip()] if jd_skills else []
                                jd_data = {
                                    "company": jd_company.strip(),
                                    "position": jd_position.strip(),
                                    "jd": jd_desc.strip(),
                                    "skills": skills_list,
                                    "link": jd_link.strip(),
                                }
                                ok = add_jd(KB_PATH, KB, jd_data)
                                if ok:
                                    st.success(f"✅ 已添加职位描述：{jd_company} - {jd_position}")
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("添加失败")
                            else:
                                st.warning("公司名称和职位名称为必填")
                    
                    # Quick edit JD section
                    st.markdown("---")
                    st.markdown("##### ✏️ 编辑职位描述")
                    jd_options_for_edit = [f"{j.get('company', '')} - {j.get('position', '')}" for j in jds_data]
                    if jd_options_for_edit:
                        edit_jd_idx = st.selectbox("选择要编辑的职位描述", range(len(jd_options_for_edit)), 
                            format_func=lambda x: jd_options_for_edit[x], key="qedit_jd")
                        selected_jd = jds_data[edit_jd_idx]
                        
                        with st.form("quick_edit_jd_form"):
                            col1, col2 = st.columns(2)
                            with col1:
                                edit_jd_company = st.text_input("公司名称", value=selected_jd.get("company", ""), key="qedit_jd_company")
                                edit_jd_position = st.text_input("职位名称", value=selected_jd.get("position", ""), key="qedit_jd_position")
                            with col2:
                                existing_skills = ", ".join(selected_jd.get("skills", [])) if isinstance(selected_jd.get("skills"), list) else str(selected_jd.get("skills", ""))
                                edit_jd_skills = st.text_input("技能要求（用逗号分隔）", value=existing_skills, key="qedit_jd_skills")
                                edit_jd_link = st.text_input("招聘链接", value=selected_jd.get("link", ""), key="qedit_jd_link")
                            edit_jd_desc = st.text_area("职位描述", value=selected_jd.get("jd", ""), key="qedit_jd_desc", height=100)
                            
                            if st.form_submit_button("💾 保存修改", type="primary"):
                                if edit_jd_company.strip() and edit_jd_position.strip():
                                    skills_list = [s.strip() for s in edit_jd_skills.split(",") if s.strip()] if edit_jd_skills else []
                                    updated_jd = {
                                        "company": edit_jd_company.strip(),
                                        "position": edit_jd_position.strip(),
                                        "jd": edit_jd_desc.strip(),
                                        "skills": skills_list,
                                        "link": edit_jd_link.strip(),
                                    }
                                    # Use original company and position as identifiers
                                    ok = update_jd(KB_PATH, KB, selected_jd.get("company"), selected_jd.get("position"), updated_jd)
                                    if ok:
                                        st.success(f"✅ 已更新职位描述：{edit_jd_company} - {edit_jd_position}")
                                        KB.clear()
                                        KB.update(load_knowledge_base(KB_PATH))
                                        safe_rerun()
                                    else:
                                        st.error("更新失败")
                                else:
                                    st.warning("公司名称和职位名称为必填")
                    else:
                        st.info("暂无职位描述可编辑")
                    
                    # Quick delete section
                    st.markdown("---")
                    st.markdown("##### 🗑️ 删除职位描述")
                    with st.form("quick_delete_jd_form"):
                        jd_options = [f"{j.get('company', '')} - {j.get('position', '')}" for j in jds_data]
                        if jd_options:
                            del_jd_idx = st.selectbox("选择要删除的职位描述", range(len(jd_options)), 
                                format_func=lambda x: jd_options[x], key="qdel_jd")
                            if st.form_submit_button("🗑️ 删除职位描述", type="secondary"):
                                del_jd = jds_data[del_jd_idx]
                                ok = delete_jd(KB_PATH, KB, del_jd.get("company"), del_jd.get("position"))
                                if ok:
                                    st.success(f"✅ 已删除职位描述：{jd_options[del_jd_idx]}")
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("删除失败")
                        else:
                            st.info("暂无职位描述数据")
                            st.form_submit_button("🗑️ 删除职位描述", disabled=True)
                else:
                    st.info("知识库中暂无职位描述数据")
                    
                    # Quick add JD form when no data exists
                    st.markdown("---")
                    st.markdown("##### ➕ 快速添加职位描述")
                    with st.form("quick_add_jd_form_empty", clear_on_submit=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            jd_company = st.text_input("公司名称", key="qadd_jd_company_empty")
                            jd_position = st.text_input("职位名称", key="qadd_jd_position_empty")
                        with col2:
                            jd_skills = st.text_input("技能要求（用逗号分隔）", key="qadd_jd_skills_empty")
                            jd_link = st.text_input("招聘链接", key="qadd_jd_link_empty")
                        jd_desc = st.text_area("职位描述", key="qadd_jd_desc_empty", height=100)
                        
                        if st.form_submit_button("➕ 添加职位描述", type="primary"):
                            if jd_company.strip() and jd_position.strip():
                                skills_list = [s.strip() for s in jd_skills.split(",") if s.strip()] if jd_skills else []
                                jd_data = {
                                    "company": jd_company.strip(),
                                    "position": jd_position.strip(),
                                    "jd": jd_desc.strip(),
                                    "skills": skills_list,
                                    "link": jd_link.strip(),
                                }
                                ok = add_jd(KB_PATH, KB, jd_data)
                                if ok:
                                    st.success(f"✅ 已添加职位描述：{jd_company} - {jd_position}")
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("添加失败")
                            else:
                                st.warning("公司名称和职位名称为必填")
            
            # Download templates section
            st.markdown("---")
            st.markdown("### 📋 下载导入模板")
            st.info("下载模板文件，填充数据后上传即可批量导入。")
            
            from utils.dashboard_analytics import get_import_template_csv, get_import_template_json, get_import_template_excel
            
            template_cols = st.columns(4)
            with template_cols[0]:
                st.markdown("**课程模板**")
                st.download_button("📄 CSV", get_import_template_csv("courses"), "courses_template.csv", "text/csv", key="dl_course_csv")
                st.download_button("📊 Excel", get_import_template_excel("courses"), "courses_template.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_course_xlsx")
            with template_cols[1]:
                st.markdown("**导师模板**")
                st.download_button("📄 CSV", get_import_template_csv("advisors"), "advisors_template.csv", "text/csv", key="dl_adv_csv")
                st.download_button("📊 Excel", get_import_template_excel("advisors"), "advisors_template.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_adv_xlsx")
            with template_cols[2]:
                st.markdown("**实践模板**")
                st.download_button("📄 CSV", get_import_template_csv("practices"), "practices_template.csv", "text/csv", key="dl_prac_csv")
                st.download_button("📊 Excel", get_import_template_excel("practices"), "practices_template.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_prac_xlsx")
            with template_cols[3]:
                st.markdown("**校友案例模板**")
                st.download_button("📄 CSV", get_import_template_csv("alumni_cases"), "alumni_template.csv", "text/csv", key="dl_alum_csv")
                st.download_button("📊 Excel", get_import_template_excel("alumni_cases"), "alumni_template.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_alum_xlsx")

        # Tab 1: System Announcements
        with kb_tabs[1]:
            st.subheader("📢 系统公告")
            
            if add_notification:
                st.markdown("""
                向所有用户发送系统公告。公告将出现在所有用户的通知中心。
                """)
                
                announcement_title = st.text_input("公告标题", placeholder="例如：平台维护通知")
                announcement_content = st.text_area(
                    "公告内容", 
                    placeholder="请输入公告详细内容...",
                    height=150
                )
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button("📢 发送公告", type="primary"):
                        if not announcement_title.strip() or not announcement_content.strip():
                            st.error("公告标题和内容不能为空")
                        else:
                            # Get all users
                            users_list = list_users()
                            if not isinstance(users_list, list):
                                users_list = []
                            
                            if users_list:
                                success_count = 0
                                failed_count = 0
                                
                                # Send notification to each user
                                for user in users_list:
                                    username = user.get("username")
                                    if username:
                                        try:
                                            add_notification(
                                                username=username,
                                                notification_type="announcement",
                                                title=announcement_title,
                                                message=announcement_content,
                                                link="",
                                                metadata={"admin": st.session_state.get("admin_user", "system")}
                                            )
                                            success_count += 1
                                        except Exception as e:
                                            failed_count += 1
                                            st.error(f"发送给 {username} 失败: {str(e)}")
                                
                                if failed_count == 0:
                                    st.success(f"✅ 公告已成功发送给 {success_count} 位用户！")
                                else:
                                    st.warning(f"⚠️ 成功: {success_count}, 失败: {failed_count}")
                            else:
                                st.warning("没有找到用户")
                
                st.markdown("---")
                st.markdown("### 💡 使用提示")
                st.info("""
                - 公告会发送给所有注册用户
                - 用户可以在侧边栏的"🔔 通知中心"查看
                - 建议公告内容简洁明了
                - 重要公告建议在标题中标注【重要】或【紧急】
                """)
            else:
                st.warning("通知系统未启用")

    render_tab_ai_helper(
        "admin",
        "管理与审核页面",
        ai_agent,
        context="当前待审核数量：" + str(len(get_pending_reviews(KB))),
    )

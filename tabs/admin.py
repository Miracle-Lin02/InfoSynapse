# -*- coding: utf-8 -*-
"""
Tab 8: Admin & moderation dashboard, KB editing, feedback stats.
"""

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
)
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
        st.markdown("### 📚 知识库编辑（课程 / 校内实践 / 导师 / 校友案例）")
        kb_tabs = st.tabs(
            [
                "新增课程",
                "管理课程",
                "新增校内实践",
                "管理校内实践",
                "新增导师",
                "管理导师",
                "新增校友案例",
                "管理校友案例",
                "📥 数据导入",
                "📢 系统公告",
            ]
        )

        with kb_tabs[0]:
            st.subheader("新增课程")

            # 预置一批常见专业（你可以按自己学校情况继续增删）
            preset_majors = [
                "计算机科学与技术",
                "软件工程",
                "人工智能",
                "数据科学与大数据技术",
                "网络工程",
                "信息安全",
                "物联网工程",
                "电子信息工程",
                "通信工程",
            ]
            # KB 中已有的专业
            kb_majors = list(KB.get("courses", {}).keys())
            # 合并预置 + 已有，并去重排序
            majors = sorted(set(preset_majors + kb_majors)) or ["计算机科学与技术"]

            with st.form("form_add_course"):
                major = st.selectbox("所属专业", majors, index=0)
                code = st.text_input("课程代码（如 CS101）")
                name = st.text_input("课程名称")
                level = st.selectbox(
                    "课程层次", ["基础", "进阶", "选修", "价值引领类", "其他"], index=0
                )
                prereq = st.text_input("先修课程（可空）")
                link = st.text_input("课程主页/资料链接（可空）")
                outline = st.text_area("课程简介 / 大纲", height=150)
                is_ideological = st.checkbox("标记为思政课程", value=False)
                submitted = st.form_submit_button("保存到知识库")
                if submitted:
                    if not code.strip() or not name.strip():
                        st.warning("课程代码和课程名称为必填")
                    else:
                        course_data = {
                            "code": code.strip(),
                            "name": name.strip(),
                            "level": level.strip(),
                            "prereq": prereq.strip(),
                            "link": link.strip(),
                            "outline": outline.strip(),
                            "reviews": [],
                        }
                        if is_ideological:
                            course_data["ideological"] = True
                        ok = add_course(KB_PATH, KB, major, course_data)
                        if ok:
                            st.success(f"已为专业『{major}』新增课程：{code} {name}")
                            KB.clear()
                            KB.update(load_knowledge_base(KB_PATH))
                            safe_rerun()
                        else:
                            st.error("写入知识库失败")

        with kb_tabs[1]:
            st.subheader("管理课程（编辑/删除）")
            courses_by_major = KB.get("courses", {})
            majors = list(courses_by_major.keys())
            if not majors:
                st.info("当前知识库中还没有课程数据。")
            else:
                major_sel = st.selectbox(
                    "选择专业", majors, key="manage_course_major"
                )
                course_list = courses_by_major.get(major_sel, [])
                if not course_list:
                    st.info(f"专业『{major_sel}』下暂无课程。")
                else:
                    for idx, c in enumerate(course_list):
                        code = c.get("code", "")
                        name = c.get("name", "")
                        with st.expander(f"📚 {code} {name}"):
                            with st.form(f"form_edit_course_{major_sel}_{code}_{idx}"):
                                st.markdown("**编辑课程信息**")
                                new_name = st.text_input("课程名称", value=name)
                                new_level = st.selectbox(
                                    "课程层次",
                                    ["基础", "进阶", "选修", "价值引领类", "其他"],
                                    index=(
                                        ["基础", "进阶", "选修", "价值引领类", "其他"].index(c.get("level", "基础"))
                                        if c.get("level") in ["基础", "进阶", "选修", "价值引领类", "其他"]
                                        else 0
                                    ),
                                )
                                new_prereq = st.text_input("先修课程", value=c.get("prereq", ""))
                                new_link = st.text_input("课程主页/资料链接", value=c.get("link", ""))
                                new_outline = st.text_area("课程简介 / 大纲", value=c.get("outline", ""), height=120)
                                new_ideological = st.checkbox(
                                    "标记为思政课程", value=c.get("ideological", False)
                                )
                                
                                col_edit1, col_edit2 = st.columns(2)
                                with col_edit1:
                                    save_edit = st.form_submit_button("💾 保存修改")
                                with col_edit2:
                                    delete_btn = st.form_submit_button("🗑 删除课程")
                                
                                if save_edit:
                                    updated_course = {
                                        "code": code,
                                        "name": new_name.strip(),
                                        "level": new_level,
                                        "prereq": new_prereq.strip(),
                                        "link": new_link.strip(),
                                        "outline": new_outline.strip(),
                                    }
                                    if new_ideological:
                                        updated_course["ideological"] = True
                                    ok = update_course(KB_PATH, KB, major_sel, code, updated_course)
                                    if ok:
                                        st.success(f"已更新课程：{code} {new_name}")
                                        KB.clear()
                                        KB.update(load_knowledge_base(KB_PATH))
                                        safe_rerun()
                                    else:
                                        st.error("更新失败")
                                
                                if delete_btn:
                                    ok = delete_course(KB_PATH, KB, major_sel, code)
                                    if ok:
                                        st.success(f"已删除课程：{code} {name}")
                                        KB.clear()
                                        KB.update(load_knowledge_base(KB_PATH))
                                        safe_rerun()
                                    else:
                                        st.error("删除失败，可能已不存在")

        with kb_tabs[2]:
            st.subheader("新增校内实践")
            with st.form("form_add_practice"):
                name = st.text_input("实践名称（如：ACM 校队 / 科创竞赛 / 实验室开放）")
                ptype = st.text_input("类型（如：竞赛 / 实验室 / 社团 / 项目）")
                desc = st.text_area("实践简介", height=150)
                link = st.text_input("相关链接（可空）")
                submitted = st.form_submit_button("保存到知识库")
                if submitted:
                    if not name.strip():
                        st.warning("实践名称为必填")
                    else:
                        ok = add_practice(
                            KB_PATH,
                            KB,
                            {
                                "name": name.strip(),
                                "type": ptype.strip(),
                                "desc": desc.strip(),
                                "link": link.strip(),
                            },
                        )
                        if ok:
                            st.success(f"已新增校内实践：{name}")
                            KB.clear()
                            KB.update(load_knowledge_base(KB_PATH))
                            safe_rerun()
                        else:
                            st.error("写入知识库失败")

        with kb_tabs[3]:
            st.subheader("管理校内实践（编辑/删除）")
            practices = KB.get("practice", []) or []
            if not practices:
                st.info("当前知识库中还没有校内实践数据。")
            else:
                for idx, p in enumerate(practices):
                    pname = p.get("name", "")
                    ptype = p.get("type", "")
                    with st.expander(f"🏫 {pname} ({ptype})"):
                        with st.form(f"form_edit_practice_{idx}"):
                            st.markdown("**编辑实践信息**")
                            new_name = st.text_input("实践名称", value=pname)
                            new_type = st.text_input("类型", value=ptype)
                            new_desc = st.text_area("实践简介", value=p.get("desc", ""), height=120)
                            new_link = st.text_input("相关链接", value=p.get("link", ""))
                            
                            col_edit1, col_edit2 = st.columns(2)
                            with col_edit1:
                                save_edit = st.form_submit_button("💾 保存修改")
                            with col_edit2:
                                delete_btn = st.form_submit_button("🗑 删除")
                            
                            if save_edit:
                                updated_practice = {
                                    "name": new_name.strip(),
                                    "type": new_type.strip(),
                                    "desc": new_desc.strip(),
                                    "link": new_link.strip(),
                                }
                                ok = update_practice(KB_PATH, KB, pname, updated_practice)
                                if ok:
                                    st.success(f"已更新校内实践：{new_name}")
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("更新失败")
                            
                            if delete_btn:
                                ok = delete_practice(KB_PATH, KB, pname)
                                if ok:
                                    st.success(f"已删除校内实践：{pname}")
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("删除失败，可能已不存在")

        with kb_tabs[4]:
            st.subheader("新增导师")
            with st.form("form_add_advisor"):
                name = st.text_input("导师姓名")
                department = st.text_input("学院/部门", value="计算机学院")
                research = st.text_area(
                    "研究方向（如：机器学习 / 软件工程）", height=120
                )
                homepage = st.text_input("个人主页链接（可空）")
                national_projects = st.checkbox("参与国家重大项目", value=False)
                national_projects_info = st.text_area(
                    "国家重大项目信息（可空）", height=80,
                    help="如果勾选了参与国家重大项目，可以在此填写具体项目信息"
                )
                submitted = st.form_submit_button("保存到知识库")
                if submitted:
                    if not name.strip():
                        st.warning("导师姓名为必填")
                    else:
                        advisor_data = {
                            "name": name.strip(),
                            "department": department.strip(),
                            "research": research.strip(),
                            "homepage": homepage.strip(),
                            "reviews": [],
                            "national_projects": national_projects,
                        }
                        if national_projects and national_projects_info.strip():
                            advisor_data["national_projects_info"] = national_projects_info.strip()
                        ok = add_advisor(KB_PATH, KB, advisor_data)
                        if ok:
                            st.success(f"已新增导师：{name}")
                            KB.clear()
                            KB.update(load_knowledge_base(KB_PATH))
                            safe_rerun()
                        else:
                            st.error("写入知识库失败")

        with kb_tabs[5]:
            st.subheader("管理导师（编辑/删除）")
            advisors = KB.get("advisors", []) or []
            if not advisors:
                st.info("当前知识库中还没有导师数据。")
            else:
                for idx, a in enumerate(advisors):
                    name = a.get("name", "")
                    dept = a.get("department", "")
                    with st.expander(f"👨‍🏫 {name} ({dept})"):
                        with st.form(f"form_edit_advisor_{idx}"):
                            st.markdown("**编辑导师信息**")
                            new_name = st.text_input("导师姓名", value=name)
                            new_dept = st.text_input("学院/部门", value=dept)
                            new_research = st.text_area("研究方向", value=a.get("research", ""), height=100)
                            new_homepage = st.text_input("个人主页链接", value=a.get("homepage", ""))
                            new_national_projects = st.checkbox(
                                "参与国家重大项目",
                                value=a.get("national_projects", False)
                            )
                            new_national_projects_info = st.text_area(
                                "国家重大项目信息",
                                value=a.get("national_projects_info", ""),
                                height=80
                            )
                            
                            col_edit1, col_edit2 = st.columns(2)
                            with col_edit1:
                                save_edit = st.form_submit_button("💾 保存修改")
                            with col_edit2:
                                delete_btn = st.form_submit_button("🗑 删除")
                            
                            if save_edit:
                                updated_advisor = {
                                    "name": new_name.strip(),
                                    "department": new_dept.strip(),
                                    "research": new_research.strip(),
                                    "homepage": new_homepage.strip(),
                                    "national_projects": new_national_projects,
                                }
                                if new_national_projects and new_national_projects_info.strip():
                                    updated_advisor["national_projects_info"] = new_national_projects_info.strip()
                                ok = update_advisor(KB_PATH, KB, name, updated_advisor)
                                if ok:
                                    st.success(f"已更新导师：{new_name}")
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("更新失败")
                            
                            if delete_btn:
                                ok = delete_advisor(KB_PATH, KB, name)
                                if ok:
                                    st.success(f"已删除导师：{name}")
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("删除失败，可能已不存在")

        # Alumni cases management tabs
        with kb_tabs[6]:
            st.subheader("新增校友案例")
            st.info("添加杭电校友扎根重点领域的典型案例，将在职业规划页面展示")
            with st.form("form_add_alumni"):
                case_title = st.text_input("案例标题（如：投身航天科技，逐梦星辰大海）")
                case_field = st.selectbox(
                    "重点领域",
                    ["航天科技", "乡村振兴", "芯片自主", "网络安全", "能源电力", "其他"],
                    index=0
                )
                case_name = st.text_input("校友姓名（可用化名，可空）")
                case_year = st.text_input("毕业年份（如：2015届）")
                case_major = st.text_input("专业（如：电子信息专业）")
                case_content = st.text_area("案例内容", height=200, 
                    help="描述校友的奋斗历程、成就和感悟")
                submitted = st.form_submit_button("保存到知识库")
                if submitted:
                    if not case_title.strip() or not case_content.strip():
                        st.warning("案例标题和内容为必填")
                    else:
                        case_data = {
                            "title": case_title.strip(),
                            "field": case_field,
                            "name": case_name.strip() if case_name.strip() else "化名",
                            "year": case_year.strip(),
                            "major": case_major.strip(),
                            "content": case_content.strip(),
                        }
                        ok = add_alumni_case(KB_PATH, KB, case_data)
                        if ok:
                            st.success(f"已新增校友案例：{case_title}")
                            KB.clear()
                            KB.update(load_knowledge_base(KB_PATH))
                            safe_rerun()
                        else:
                            st.error("写入知识库失败")

        with kb_tabs[7]:
            st.subheader("管理校友案例（编辑/删除）")
            alumni_cases = get_alumni_cases(KB)
            if not alumni_cases:
                st.info("当前知识库中还没有校友案例数据。")
            else:
                for idx, case in enumerate(alumni_cases):
                    case_id = case.get("id", "")
                    title = case.get("title", "")
                    field = case.get("field", "")
                    with st.expander(f"🌟 {title} ({field})"):
                        with st.form(f"form_edit_alumni_{case_id}_{idx}"):
                            st.markdown("**编辑校友案例**")
                            new_title = st.text_input("案例标题", value=title)
                            new_field = st.selectbox(
                                "重点领域",
                                ["航天科技", "乡村振兴", "芯片自主", "网络安全", "能源电力", "其他"],
                                index=(
                                    ["航天科技", "乡村振兴", "芯片自主", "网络安全", "能源电力", "其他"].index(field)
                                    if field in ["航天科技", "乡村振兴", "芯片自主", "网络安全", "能源电力", "其他"]
                                    else 0
                                )
                            )
                            new_name = st.text_input("校友姓名", value=case.get("name", ""))
                            new_year = st.text_input("毕业年份", value=case.get("year", ""))
                            new_major = st.text_input("专业", value=case.get("major", ""))
                            new_content = st.text_area("案例内容", value=case.get("content", ""), height=180)
                            
                            col_edit1, col_edit2 = st.columns(2)
                            with col_edit1:
                                save_edit = st.form_submit_button("💾 保存修改")
                            with col_edit2:
                                delete_btn = st.form_submit_button("🗑 删除")
                            
                            if save_edit:
                                updated_case = {
                                    "title": new_title.strip(),
                                    "field": new_field,
                                    "name": new_name.strip(),
                                    "year": new_year.strip(),
                                    "major": new_major.strip(),
                                    "content": new_content.strip(),
                                }
                                ok = update_alumni_case(KB_PATH, KB, case_id, updated_case)
                                if ok:
                                    st.success(f"已更新校友案例：{new_title}")
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("更新失败")
                            
                            if delete_btn:
                                ok = delete_alumni_case(KB_PATH, KB, case_id)
                                if ok:
                                    st.success(f"已删除校友案例：{title}")
                                    KB.clear()
                                    KB.update(load_knowledge_base(KB_PATH))
                                    safe_rerun()
                                else:
                                    st.error("删除失败，可能已不存在")

        st.markdown("---")
        st.markdown("### 待审核评价列表")
        pending = get_pending_reviews(KB)
        modlog = get_moderation_log(KB)
        if not pending:
            st.info("当前无待审核评价")
        else:
            st.write(f"待审核数量：{len(pending)}")
            for p in pending:
                st.markdown(
                    f"**ID:** {p.get('id')}  ·  目标: {p.get('target_type')}={p.get('target_id')}"
                )
                st.markdown(
                    f"- 提交者: {p.get('reviewer')}  |  评分: {p.get('rating')}  |  时间: {p.get('time')}"
                )
                st.write(p.get("comment", ""))
                cols = st.columns([1, 1, 3])
                with cols[0]:
                    if st.button("Approve", key=f"approve_{p.get('id')}"):
                        ok = approve_pending_review(KB_PATH, KB, p.get("id"))
                        if ok:
                            annotated = annotate_moderation_log_with_admin(
                                KB_PATH,
                                p.get("id"),
                                "approved",
                                st.session_state.get("admin_user", "admin"),
                            )
                            notify_admins_moderation_action(
                                p.get("id"),
                                "approved",
                                st.session_state.get("admin_user", "admin"),
                            )
                            if not annotated:
                                st.warning("已批准，但未能写入 admin_user")
                            st.success("已批准并发布评价")
                            safe_rerun()
                        else:
                            st.error("批准失败")
                with cols[1]:
                    reason_key = f"reject_reason_{p.get('id')}"
                    reason = st.text_input(
                        "拒绝理由（可选）", key=reason_key, value=""
                    )
                    if st.button("Reject", key=f"reject_{p.get('id')}"):
                        ok = reject_pending_review(
                            KB_PATH, KB, p.get("id"), reason=reason
                        )
                        if ok:
                            annotated = annotate_moderation_log_with_admin(
                                KB_PATH,
                                p.get("id"),
                                "rejected",
                                st.session_state.get("admin_user", "admin"),
                                reason=reason,
                            )
                            notify_admins_moderation_action(
                                p.get("id"),
                                "rejected",
                                st.session_state.get("admin_user", "admin"),
                                reason=reason,
                            )
                            if not annotated:
                                st.warning("已拒绝，但未能写入 admin_user")
                            st.success("已拒绝并记录理由")
                            safe_rerun()
                        else:
                            st.error("拒绝失败")
                with cols[2]:
                    st.text("提交来源：" + str(p.get("submitted_via", "web")))
                st.markdown("---")

        st.markdown("### 审核日志（moderation_log）")
        if not modlog:
            st.info("暂无审核日志")
        else:
            for m in modlog[:200]:
                st.markdown(
                    f"- [{m.get('time')}] {m.get('action').upper()} pending_id={m.get('pending_id')}  管理员：{m.get('admin_user','')}  理由：{m.get('reason','')}"
                )
                item = m.get("item", {})
                if item:
                    st.text(
                        f"  目标: {item.get('target_type')}={item.get('target_id')} 提交者:{item.get('reviewer')}  时间:{item.get('time')}"
                    )

        # 数据导入标签页
        with kb_tabs[8]:
            st.subheader("📥 数据导入（批量导入：JSON / CSV / Excel）")
            
            st.markdown("""
            ### 使用说明
            支持三种文件格式：JSON、CSV、Excel (.xlsx/.xls)
            
            **导入类型：**
            - **课程数据**: 批量导入课程信息
            - **导师数据**: 批量导入导师信息
            - **校内实践**: 批量导入实践项目
            - **校友案例**: 批量导入校友案例
            
            **导入模式：**
            - **合并模式**: 添加新数据，保留现有数据
            - **覆盖模式**: 替换所有数据（会自动备份）
            """)
            
            st.markdown("---")
            
            # 导入配置
            col1, col2 = st.columns(2)
            
            with col1:
                data_type = st.selectbox(
                    "选择数据类型",
                    ["courses", "advisors", "practices", "alumni_cases"],
                    format_func=lambda x: {
                        "courses": "📚 课程数据",
                        "advisors": "👨‍🏫 导师数据",
                        "practices": "🏫 校内实践",
                        "alumni_cases": "🎓 校友案例"
                    }[x]
                )
            
            with col2:
                import_mode = st.selectbox(
                    "选择导入模式",
                    ["merge", "overwrite"],
                    format_func=lambda x: "➕ 合并模式" if x == "merge" else "🔄 覆盖模式"
                )
            
            # 模板下载
            st.markdown("### 📋 下载模板")
            st.info("💡 下载模板文件，填充数据后上传。支持CSV、Excel、JSON三种格式。")
            
            from utils.dashboard_analytics import get_import_template_csv, get_import_template_json, get_import_template_excel
            
            # 三列布局显示三种模板下载按钮
            col_csv, col_excel, col_json = st.columns(3)
            
            with col_csv:
                template_csv = get_import_template_csv(data_type)
                st.download_button(
                    label="📄 CSV模板",
                    data=template_csv,
                    file_name=f"{data_type}_template.csv",
                    mime="text/csv",
                    help="适合Excel/WPS编辑"
                )
            
            with col_excel:
                template_excel = get_import_template_excel(data_type)
                st.download_button(
                    label="📊 Excel模板",
                    data=template_excel,
                    file_name=f"{data_type}_template.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Excel原生格式"
                )
            
            with col_json:
                template_json = get_import_template_json(data_type)
                st.download_button(
                    label="📋 JSON模板",
                    data=template_json,
                    file_name=f"{data_type}_template.json",
                    mime="application/json",
                    help="开发者友好格式"
                )
            
            # 文件上传
            st.markdown("### 📤 上传文件")
            uploaded_file = st.file_uploader(
                "选择文件 (JSON/CSV/Excel)",
                type=["json", "csv", "xlsx", "xls"],
                key=f"import_file_{data_type}"
            )
            
            if uploaded_file is not None:
                st.success(f"✅ 已选择文件: {uploaded_file.name}")
                
                # 显示文件信息
                file_ext = uploaded_file.name.split('.')[-1].lower()
                st.info(f"📄 文件格式: {file_ext.upper()}")
                
                # 导入按钮
                if st.button("🚀 开始导入", type="primary"):
                    with st.spinner("正在导入数据..."):
                        try:
                            from utils.dashboard_analytics import import_from_file
                            
                            # 读取文件内容
                            file_content = uploaded_file.read()
                            
                            # 执行导入
                            result = import_from_file(
                                file_content=file_content,
                                filename=uploaded_file.name,
                                data_type=data_type,
                                mode=import_mode
                            )
                            
                            # 显示结果
                            if result.get("success"):
                                st.success("✅ " + result.get("message", "导入成功！"))
                                
                                # 显示统计信息
                                if "stats" in result:
                                    st.markdown("### 📊 导入统计")
                                    stats = result["stats"]
                                    
                                    if data_type == "courses":
                                        st.metric("导入课程数", stats.get("courses", 0))
                                    elif data_type == "advisors":
                                        st.metric("导入导师数", stats.get("advisors", 0))
                                    elif data_type == "practices":
                                        st.metric("导入实践数", stats.get("practices", 0))
                                    elif data_type == "alumni_cases":
                                        st.metric("导入校友案例数", stats.get("alumni_cases", 0))
                                
                                st.info("💾 原数据已自动备份")
                                
                            else:
                                st.error("❌ " + result.get("message", "导入失败"))
                                
                        except Exception as e:
                            st.error(f"❌ 导入出错: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())
            
            # 格式说明
            st.markdown("---")
            st.markdown("### 📝 格式说明")
            
            if data_type == "courses":
                st.code("""
CSV格式示例 (courses):
major,name,level,type,prerequisites,link,description
计算机,数据结构,本科,必修,程序设计基础,http://example.com,课程描述
计算机,算法设计,本科,必修,数据结构,http://example.com,算法课程描述
                """)
            elif data_type == "advisors":
                st.code("""
CSV格式示例 (advisors):
name,title,research_area,major,contact,lab,projects,national_project
张老师,教授,人工智能,计算机,zhang@example.com,AI实验室,5,true
李老师,副教授,数据库,计算机,li@example.com,数据库实验室,3,false
                """)
            elif data_type == "practices":
                st.code("""
CSV格式示例 (practices):
name,type,description,link,social_value
挑战杯红色专项,竞赛,红色主题创新竞赛,http://example.com,true
智慧助老公益项目,项目,智能助老公益实践,http://example.com,true
算法竞赛,竞赛,ACM算法竞赛,http://example.com,false
                """)
            elif data_type == "alumni_cases":
                st.code("""
CSV格式示例 (alumni_cases):
title,focus_area,alumni_name,alumni_background,content
扎根基层教育,教育事业,王校友,2015届计算机专业,毕业后选择到乡村学校任教...
服务国家战略,科技创新,李校友,2018届软件工程,参与国家重大科研项目开发...
                """)

        # Tab 10: System Announcements
        with kb_tabs[9]:
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

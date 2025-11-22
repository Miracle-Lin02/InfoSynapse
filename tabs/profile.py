# -*- coding: utf-8 -*-
"""
Tab 0: Personal homepage/profile management.
"""

from typing import Dict, Any
import streamlit as st

from shared.profiles import (
    get_user_profile,
    save_user_profile,
    _normalize_learning_item,
    _update_profile_field,
)
from shared.ai_helpers import render_tab_ai_helper, safe_rerun


def render_profile_tab(KB: Dict[str, Any], ai_agent, available_tags: list):
    """Render the personal profile tab."""
    st.header("👤 个人主页")
    with st.expander("🔍 我该怎么开始用这个网站？（新手引导）", expanded=True):
        st.markdown(
            """
- [x] 第一步：在左侧完成 **登录 / 注册**，并在本页填写「专业、当前阶段、目标职业、技能」。
- [ ] 第二步：在左侧 **兴趣标签** 中勾选你最感兴趣的 1~3 个方向（例如 *机器学习*、*Python开发*）。
- [ ] 第三步：去 **「💼 求职」Tab**，点击「智能推荐职业 & 学习路径」，看看系统给你的职业方向和学习路线。
- [ ] 第四步：在求职 Tab 中打开每个职业卡片，阅读技能需求和学习路径，如果有想法就对职业点个 👍/👎。
- [ ] 第五步：去 **「📊 综合推荐」Tab**，把你觉得合适的课程/实践/项目加到「我的学习计划」里。
- [ ] 第六步：在 **「⭐ GitHub」Tab** 中挑 1~2 个项目，收藏并尝试完成，之后可以在个人主页导出完整画像。
- [ ] 随时回来用「求职多轮对话助手」补充你的情况，问"接下来 2 周该做点什么？"。
            """
        )

    st.markdown(
        """
**👣 推荐使用路径（简版）：**

1. 在左侧完成登录 / 注册，在本页完善「个人简介、当前阶段、目标职业、技能、兴趣标签」。
2. 在左侧边栏选择你感兴趣的方向（如 Python 开发、机器学习）和目标工作城市。
3. 打开「💼 求职」标签页，点击「智能推荐职业 & 学习路径」查看职业和学习路线。
4. 打开「📊 综合推荐」查看课程 / 实践 / 项目等综合资源，并加入学习计划。
5. 在「⭐ GitHub 项目推荐」中挑项目、收藏和标记完成，形成自己的项目清单。
"""
    )

    current_user = st.session_state.get("user")
    if not current_user:
        st.info("请先登录以查看和编辑个人信息")
    else:
        username = current_user.get("username")
        profile = get_user_profile(username)
        st.markdown(f"### 欢迎，{current_user.get('display_name')}! 👋")
        
        # Display ideological growth badge
        completed_tasks = st.session_state.get("ideological_tasks_completed", [])
        if len(completed_tasks) >= 3:
            st.success("🏆 **思政成长勋章** - 您已完成多项思政微任务，展现出良好的价值观和社会责任感！")
        
        st.markdown("---")

        st.subheader("📝 编辑个人信息")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**基本信息**")
            bio = st.text_area(
                "个人简介",
                value=profile.get("bio", ""),
                height=100,
                key="profile_bio",
            )
            major = st.text_input(
                "专业", value=profile.get("major", ""), key="profile_major"
            )
            stage = st.selectbox(
                "当前阶段",
                ["", "大一", "大二", "大三", "大四", "已毕业", "其他"],
                index=(
                    ["", "大一", "大二", "大三", "大四", "已毕业", "其他"].index(
                        profile.get("stage", "")
                    )
                    if profile.get("stage", "")
                    in ["", "大一", "大二", "大三", "大四", "已毕业", "其他"]
                    else 0
                ),
                key="profile_stage",
            )
        with col2:
            st.markdown("**目标设置**")
            target_career = st.text_input(
                "目标职业（如：后端工程师、算法工程师）",
                value=profile.get("target_career", ""),
                key="profile_target_career",
            )
            target_direction = st.text_input(
                "目标方向（如：大厂后端、AI 研究等）",
                value=profile.get("target_direction", ""),
                key="profile_target_direction",
            )

        st.markdown("---")
        st.markdown("**兴趣标签（个人档案中的长期偏好）**")
        available_tags_ext = available_tags + ["移动开发", "DevOps"]
        profile_interests = st.multiselect(
            "个人兴趣标签",
            available_tags_ext,
            default=profile.get("interests", []),
            key="profile_interests",
        )
        st.info("提示：真正用于推荐的是左侧边栏的『兴趣标签』，这里主要记录你的长期偏好。")

        st.markdown("---")
        st.markdown("**技能掌握**")
        skills_text = st.text_area(
            "已掌握的技能（用逗号分隔，如：Python, JavaScript, React 等）",
            value=", ".join(profile.get("skills", [])),
            height=80,
            key="profile_skills",
        )
        skills = [s.strip() for s in skills_text.split(",") if s.strip()]

        st.markdown("---")
        if st.button("💾 保存个人信息"):
            new_profile = {
                "bio": bio,
                "major": major,
                "stage": stage,
                "target_career": target_career,
                "target_direction": target_direction,
                "interests": profile_interests,
                "skills": skills,
                "starred_repos": st.session_state.get("starred_repos", []),
                "finished_repos": st.session_state.get("finished_repos", []),
                "learning_plan": st.session_state.get("my_learning_plan", []),
            }
            save_user_profile(username, new_profile)
            st.success("✅ 个人信息已保存！")
            st.balloons()

        st.markdown("---")
        st.markdown("### 📊 个人统计")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("兴趣标签", len(profile_interests))
        with col2:
            st.metric("技能掌握", len(skills))
        with col3:
            st.metric("目标职业", "已设置" if target_career else "未设置")
        with col4:
            st.metric("专业", major or "未设置")
        with col5:
            st.metric("当前阶段", stage or "未设置")

        st.markdown("---")
        st.subheader("📅 我的学习计划（可管理）")
        plan_items = st.session_state.get("my_learning_plan", [])
        if not plan_items:
            st.info("还没有加入任何学习计划，可以在『📊 综合推荐』中点击『加入我的学习计划』。")
        else:
            ongoing = [p for p in plan_items if p.get("status") != "done"]
            done = [p for p in plan_items if p.get("status") == "done"]
            if ongoing:
                st.markdown("#### ⏳ 进行中 / 待开始")
                for idx, item in enumerate(ongoing):
                    col_a, col_b, col_c = st.columns([3, 1, 1])
                    with col_a:
                        st.markdown(
                            f"- **{item.get('name')}**（来源：{item.get('source')}，类型：{item.get('type')}）"
                        )
                    with col_b:
                        status = st.selectbox(
                            "状态",
                            ["todo", "doing", "done"],
                            index=["todo", "doing", "done"].index(
                                item.get("status", "todo")
                            ),
                            key=f"plan_status_{item.get('id')}_{idx}",
                        )
                        if status != item.get("status"):
                            item["status"] = status
                            all_items = st.session_state["my_learning_plan"]
                            for i, it in enumerate(all_items):
                                if it.get("id") == item.get("id"):
                                    all_items[i] = item
                                    break
                            st.session_state["my_learning_plan"] = all_items
                            _update_profile_field(
                                username,
                                learning_plan=[
                                    _normalize_learning_item(x)
                                    for x in st.session_state["my_learning_plan"]
                                ],
                            )
                            safe_rerun()
                    with col_c:
                        if st.button(
                            "🗑 删除", key=f"del_plan_{item.get('id')}_{idx}"
                        ):
                            all_items = [
                                it
                                for it in st.session_state["my_learning_plan"]
                                if it.get("id") != item.get("id")
                            ]
                            st.session_state["my_learning_plan"] = all_items
                            _update_profile_field(
                                username,
                                learning_plan=[
                                    _normalize_learning_item(x)
                                    for x in all_items
                                ],
                            )
                            safe_rerun()
            if done:
                st.markdown("#### ✅ 已完成")
                for idx, item in enumerate(done):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.markdown(
                            f"- ~~{item.get('name')}~~（来源：{item.get('source')}，类型：{item.get('type')}）"
                        )
                    with col_b:
                        if st.button(
                            "🗑 删除", key=f"del_done_plan_{item.get('id')}_{idx}"
                        ):
                            all_items = [
                                it
                                for it in st.session_state["my_learning_plan"]
                                if it.get("id") != item.get("id")
                            ]
                            st.session_state["my_learning_plan"] = all_items
                            _update_profile_field(
                                username,
                                learning_plan=[
                                    _normalize_learning_item(x)
                                    for x in all_items
                                ],
                            )
                            safe_rerun()

        st.markdown("---")
        if st.button("导出我的整体画像（Markdown）"):
            starred = st.session_state.get("starred_repos", [])
            finished = st.session_state.get("finished_repos", [])
            plan_items = st.session_state.get("my_learning_plan", [])

            def _fmt_repo_line(r: Dict[str, Any]) -> str:
                full_name = r.get("full_name", "")
                url = r.get("html_url", "")
                lang = r.get("language", "") or "未标注"
                stars = r.get("stargazers_count", 0)
                desc = (r.get("description") or "").strip()
                return f"- [{full_name}]({url}) · 语言：{lang} · ⭐ {stars}\n  - {desc}"

            def _fmt_plan_line(p: Dict[str, Any]) -> str:
                return f"- [{p.get('status','todo')}] {p.get('name')}（来源：{p.get('source')}, 类型：{p.get('type')}）"

            lines = []
            lines.append(
                f"# 个人画像：{current_user.get('display_name')} (@{username})\n"
            )
            lines.append("## 基本信息")
            lines.append(f"- 专业：{major or '未填写'}")
            lines.append(f"- 当前阶段：{stage or '未填写'}")
            lines.append(f"- 目标职业：{target_career or '未填写'}")
            lines.append(f"- 目标方向：{target_direction or '未填写'}")
            lines.append(f"- 简介：{bio or '未填写'}\n")
            lines.append("## 兴趣与技能")
            lines.append(
                f"- 兴趣标签：{', '.join(profile_interests) or '未设置'}"
            )
            lines.append(f"- 技能：{', '.join(skills) or '未填写'}\n")
            lines.append("## 学习计划")
            if not plan_items:
                lines.append("- （当前暂无计划）\n")
            else:
                for p in plan_items:
                    lines.append(_fmt_plan_line(p))
                lines.append("")
            lines.append("## 收藏的项目")
            if not starred:
                lines.append("- （暂无收藏项目）\n")
            else:
                for r in starred:
                    lines.append(_fmt_repo_line(r))
                lines.append("")
            lines.append("## 已完成的项目")
            if not finished:
                lines.append("- （暂无已完成项目）\n")
            else:
                for r in finished:
                    lines.append(_fmt_repo_line(r))
                lines.append("")

            md_export = "\n".join(lines)
            st.download_button(
                "下载个人画像 Markdown 文件",
                data=md_export.encode("utf-8"),
                file_name=f"profile_{username}.md",
                mime="text/markdown",
                key="download_profile_md",
            )

        render_tab_ai_helper("profile", "个人主页", ai_agent)

# -*- coding: utf-8 -*-
"""
Tab 5: GitHub project recommendations (random + AI-assisted).
"""

from typing import Dict, Any
import streamlit as st

from utils.recommend import (
    recommend_random_repos,
    recommend_projects_by_agent,
    PATRIOTIC_OPENSOURCE_KEYWORDS,
)
from shared.profiles import (
    get_user_profile,
    _normalize_repo_item,
    _update_profile_field,
)
from shared.ai_helpers import render_tab_ai_helper, safe_rerun


def render_github_tab(KB: Dict[str, Any], ai_agent, github_crawler):
    """Render the GitHub projects recommendation tab."""
    st.header("⭐ GitHub 高星项目推荐")

    interests = st.session_state.get("user_interests", [])
    current_user = st.session_state.get("user")
    user_skills = []
    user_target_career = ""
    username = None
    if current_user:
        username = current_user.get("username")
        profile = get_user_profile(username)
        user_skills = profile.get("skills", [])
        user_target_career = profile.get("target_career", "")
    
    # Ideological & Political Education: Open-source patriotism
    with st.expander("🇨🇳 开源创新与技术自立自强", expanded=False):
        st.markdown("""
        **青年参与开源，助力技术自立自强**
        
        推荐关注以下类型的开源项目：
        
        - 🇨🇳 **国产技术替代**：开源操作系统（openEuler、openKylin）、自主可控算法等
        - 💝 **开源公益**：服务社会的开源项目，如教育、医疗、环保领域
        - 🔧 **基础软件**：数据库、中间件等关键基础软件的国产替代方案
        - 🤝 **社区贡献**：积极参与开源社区，为国产开源生态做贡献
        
        💡 参与开源不仅是技术学习，更是为国家技术自主可控贡献力量。
        """)
    
    st.markdown("---")
    
    # Add filter for open-source public welfare and domestic tech projects
    if "filter_patriotic_opensource" not in st.session_state:
        st.session_state["filter_patriotic_opensource"] = False
    
    filter_patriotic = st.checkbox(
        "优先推荐国产技术/公益开源项目",
        value=st.session_state.get("filter_patriotic_opensource", False),
        key="filter_patriotic_opensource_checkbox",
        help="启用后，将优先推荐国产技术替代和开源公益类项目"
    )
    st.session_state["filter_patriotic_opensource"] = filter_patriotic

    st.markdown("---")
    st.markdown("### 随机推荐")
    if st.button("🌟 随机推荐 GitHub 高星项目"):
        if not interests:
            st.warning("请先在侧边栏选择兴趣标签")
        else:
            with st.spinner("正在推荐 GitHub 项目..."):
                repos = recommend_random_repos(
                    interests, github_crawler=github_crawler
                )
                st.session_state["github_repos"] = repos
            topics_used = st.session_state.get("github_topics_used", [])
            fetch_count = st.session_state.get("github_fetch_count", 0)
            if topics_used:
                st.caption(
                    f"本次根据这些 topic 抓取项目：{', '.join(topics_used)}（共抓取 {fetch_count} 个候选仓库）"
                )
            if not github_crawler:
                st.warning(
                    "当前未启用 GitHub 实时抓取（可能未配置 GITHUB_TOKEN），仅使用已有缓存。"
                )
            if repos:
                st.success(f"已推荐 {len(repos)} 个项目")
                safe_rerun()
            else:
                st.info("未能从 GitHub 拉取到项目，请检查 GITHUB_TOKEN 或稍后再试。")

    st.markdown("---")
    st.markdown("### 🤖 智能体推荐")
    if st.button("🧠 使用智能体推荐项目", key="agent_recommend_projects_btn"):
        if not interests:
            st.warning("请先在侧边栏选择兴趣标签")
        else:
            with st.spinner("智能体正在分析并推荐项目..."):
                projects = recommend_projects_by_agent(
                    interests, user_skills, user_target_career
                )
                st.session_state["agent_project_recs"] = projects
            if projects:
                st.success(f"✅ 已生成 {len(projects)} 个推荐项目")
                safe_rerun()

    st.markdown("---")
    st.markdown("### 📊 推荐结果")

    repos = st.session_state.get("github_repos", [])
    min_stars = 0
    if repos:
        max_stars = max(r.get("stargazers_count", 0) or 0 for r in repos)
        min_stars = st.slider(
            "最小 star 数（仅显示不少于该星数的项目）",
            min_value=0,
            max_value=max(1000, max_stars),
            value=0,
            step=50,
            key="github_min_stars",
        )
        filtered_repos = [
            r
            for r in repos
            if (r.get("stargazers_count", 0) or 0) >= min_stars
        ]
    else:
        filtered_repos = []

    starred_list = st.session_state.get("starred_repos", [])
    finished_list = st.session_state.get("finished_repos", [])
    starred_keys = {r.get("full_name") for r in starred_list}
    finished_keys = {r.get("full_name") for r in finished_list}
    
    # Add patriotic/public welfare scoring
    filter_patriotic = st.session_state.get("filter_patriotic_opensource", False)
    if filter_patriotic and filtered_repos:
        for repo in filtered_repos:
            name = (repo.get("full_name", "") or "").lower()
            desc = (repo.get("description", "") or "").lower()
            patriotic_score = sum(1 for kw in PATRIOTIC_OPENSOURCE_KEYWORDS if kw in name or kw in desc)
            repo["patriotic_score"] = patriotic_score
        
        # Sort by patriotic score
        filtered_repos = sorted(filtered_repos, key=lambda x: x.get("patriotic_score", 0), reverse=True)

    if filtered_repos:
        st.subheader(
            f"🌟 随机推荐的项目（{len(filtered_repos)} 个，已按最小 star ≥ {min_stars} 过滤）"
        )
        for repo in filtered_repos:
            full_name = repo.get("full_name")
            repo_key = full_name or repo.get("html_url")
            norm_repo = _normalize_repo_item(repo)
            
            # Show patriotic/public welfare badge
            patriotic_score = repo.get("patriotic_score", 0)
            patriotic_badge = ""
            if patriotic_score > 0:
                patriotic_badge = " 🇨🇳"
            
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**[{full_name}{patriotic_badge}]({repo.get('html_url')})**")
                
                # Highlight if it's a patriotic or public welfare project
                if patriotic_score > 0:
                    st.info("🎯 **价值引领项目** - 该项目与国产技术自主或开源公益相关")
                
                st.write(repo.get("description", "暂无描述")[:250])
                tags = [repo.get("language"), repo.get("matched_interest")]
                tags = [t for t in tags if t]
                if tags:
                    st.caption(f"🏷️ {', '.join(tags)}")
            with col2:
                stars = repo.get("stargazers_count", 0)
                st.markdown(f"⭐ **{stars}** stars")
            with col3:
                is_starred = full_name in starred_keys
                star_label = "已收藏" if is_starred else "⭐ 收藏"
                if st.button(star_label, key=f"star_{repo_key}"):
                    if is_starred:
                        st.session_state["starred_repos"] = [
                            r
                            for r in starred_list
                            if r.get("full_name") != full_name
                        ]
                    else:
                        st.session_state["starred_repos"].append(norm_repo)
                    if username:
                        _update_profile_field(
                            username,
                            starred_repos=st.session_state["starred_repos"],
                        )
                    safe_rerun()
                is_finished = full_name in finished_keys
                done_label = "✅ 已完成" if is_finished else "✅ 标记完成"
                if st.button(done_label, key=f"done_{repo_key}"):
                    if is_finished:
                        st.session_state["finished_repos"] = [
                            r
                            for r in finished_list
                            if r.get("full_name") != full_name
                        ]
                    else:
                        st.session_state["finished_repos"].append(norm_repo)
                    if username:
                        _update_profile_field(
                            username,
                            finished_repos=st.session_state["finished_repos"],
                        )
                    safe_rerun()
            st.divider()
    elif repos:
        st.info("当前最小 star 过滤条件过高，导致没有项目，请降低阈值。")

    agent_projects = st.session_state.get("agent_project_recs", [])
    if agent_projects:
        st.subheader(f"🧠 智能体推荐的项目（{len(agent_projects)} 个）")
        for project in agent_projects:
            with st.expander(
                f"📌 {project.get('name')} — {project.get('difficulty')}"
            ):
                st.markdown(f"**描述：** {project.get('description')}")
                st.markdown(f"**学习价值：** {project.get('learning_value')}")
                st.markdown(f"**难度：** {project.get('difficulty')}")
                st.markdown(
                    f"**预期学习时间：** {project.get('estimated_time')} 周"
                )
                st.markdown(
                    f"**技术栈：** {', '.join(project.get('tech_stack', []))}"
                )
                st.markdown(f"**[查看 GitHub]({project.get('url')})**")

    if not repos and not agent_projects:
        st.info("点击上方按钮开始获取推荐")

    st.markdown("---")
    st.subheader("⭐ 我的收藏项目")
    if not starred_list:
        st.caption(
            "还没有收藏任何项目，在上面的列表中点击『⭐ 收藏』即可加入。（再次点击『已收藏』可取消）"
        )
    else:
        for r in starred_list:
            st.markdown(
                f"- **[{r.get('full_name')}]({r.get('html_url')})** · 语言：{r.get('language') or '未标注'} · ⭐ {r.get('stargazers_count',0)}  \n  { (r.get('description') or '').strip() }"
            )

    st.subheader("✅ 我已完成的项目")
    if not finished_list:
        st.caption(
            "还没有标记完成的项目，在上面的列表中点击『✅ 标记完成』即可。（再次点击『已完成』可取消）"
        )
    else:
        for r in finished_list:
            st.markdown(
                f"- **[{r.get('full_name')}]({r.get('html_url')})** · 语言：{r.get('language') or '未标注'} · ⭐ {r.get('stargazers_count',0)}  \n  { (r.get('description') or '').strip() }"
            )

    render_tab_ai_helper(
        "github",
        "GitHub 项目推荐",
        ai_agent,
        context="当前兴趣：" + ", ".join(interests),
    )

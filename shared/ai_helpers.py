# -*- coding: utf-8 -*-
"""
AI helper functions for InfoSynapse application.
Contains render functions for AI-assisted features across different tabs.
"""

from typing import Dict, Any
import streamlit as st

from utils.recommend import AIAgent
from utils.prompts import (
    build_tab_helper_prompt,
    build_career_plan_prompt,
    build_mixed_plan_prompt,
    build_career_chat_prompt,
)

from shared.profiles import get_user_profile


def format_review(r: Dict[str, Any]) -> str:
    """Format a review dictionary into a readable string."""
    reviewer = r.get("reviewer", "匿名")
    rating = r.get("rating", None)
    time_ = r.get("time", "")
    comment = r.get("comment", "")
    if rating is not None:
        header = f"{reviewer} — {rating}/5  ·  {time_}"
    else:
        header = f"{reviewer}  ·  {time_}"
    return f"**{header}**\n\n{comment}"


def _get_current_stage() -> str:
    """Get the current user's stage from their profile."""
    user = st.session_state.get("user")
    if not user:
        return ""
    profile = get_user_profile(user["username"])
    return profile.get("stage", "")


def safe_rerun():
    """Safely trigger a Streamlit rerun."""
    try:
        if hasattr(st, "rerun"):
            st.rerun()
            return
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
            return
    except Exception:
        pass
    st.warning("自动刷新不可用，请手动刷新页面。")


def render_tab_ai_helper(tab_key: str, title: str, ai_agent: AIAgent, context: str = ""):
    """Render a tab-specific AI helper widget."""
    st.markdown("---")
    st.subheader(f"🤖 本页智能体助手 · {title}")
    stage = _get_current_stage() or "未设置"
    interests = ", ".join(st.session_state.get("user_interests", [])) or "未设置"

    role_hint_map = {
        "profile": "你主要是帮学生梳理个人情况、目标职业和长期规划。",
        "courses": "你主要是帮助学生在当前专业和阶段下，做选课决策和学习顺序规划。",
        "advisors": "你主要是帮助学生选择合适的导师，并给出联系导师的建议（比如怎么写第一封邮件）。",
        "practice": "你主要是帮助学生从校内实践资源中选出适合当前阶段的机会，以及如何参与和积累成果。",
        "career_tab": "你是职业规划顾问，补充页面已有推荐之外的个性化建议。",
        "github": "你是项目选题顾问，帮助学生从项目中选出更适合练手和简历展示的方向。",
        "community": "你主要是帮助学生更好地使用社区（提问、分享、跟进话题）。",
        "mixed": "你主要是帮助学生把综合推荐转化为可执行的学习/实践路线。",
        "admin": "你主要是帮助管理员思考审核策略和如何改进系统规则。",
    }
    role_hint = role_hint_map.get(tab_key, "你是一个大学学业与职业规划助手。")

    user_input = st.text_area(
        "可以补充你在本页相关的疑问或想让智能体帮你思考的内容（可选）：",
        height=80,
        key=f"tab_ai_input_{tab_key}",
    )

    if st.button("让智能体根据本页内容给一些建议", key=f"tab_ai_btn_{tab_key}"):
        prompt = build_tab_helper_prompt(
            tab_key=tab_key,
            role_hint=role_hint,
            title=title,
            stage=stage,
            interests=interests,
            context=context,
            user_input=user_input or "",
        )
        with st.spinner("智能体正在思考这页可以怎么用得更好..."):
            ans = ai_agent.call(prompt, temperature=0.5, max_tokens=1200)
        if "【本地回退】" in ans:
            st.warning("当前智能体服务暂不可用，下面是本地示例回答，仅供参考。")
        st.session_state["tab_ai_answers"][tab_key] = ans

    if st.session_state["tab_ai_answers"].get(tab_key):
        st.markdown("#### 本页智能体建议")
        st.markdown(st.session_state["tab_ai_answers"][tab_key])


def render_career_ai_summary(ai_agent: AIAgent):
    """Render AI-generated career planning summary."""
    interests = st.session_state.get("user_interests", [])
    location = st.session_state.get("work_location", "全国")
    careers = st.session_state.get("career_recommendations", [])
    stage = _get_current_stage() or "未设置"

    st.markdown("---")
    st.subheader("🤖 智能助手 · 求职行动计划")

    if not careers:
        st.info("先点击上面的『智能推荐职业 & 学习路径』生成职业列表，再使用智能助手。")
        return

    user_extra = st.text_area(
        "可以补充一些你的情况（可选），比如是否考研、已有项目经历等：",
        height=80,
        key="career_ai_extra",
    )

    if st.button("让智能体总结一份职业行动计划", key="career_ai_btn"):
        career_brief = "\n".join(
            [
                f"- {c.get('career')}（技能：{', '.join(c.get('skills', []))}；薪资：{c.get('salary','')}；公司：{c.get('companies','')}）"
                for c in careers[:6]
            ]
        )
        prompt = build_career_plan_prompt(
            careers_brief=career_brief,
            interests=", ".join(interests),
            location=location,
            stage=stage,
            extra=user_extra or "",
        )
        with st.spinner("智能体正在综合分析你的职业规划..."):
            summary = ai_agent.call(prompt, temperature=0.4, max_tokens=2000)
        if "【本地回退】" in summary:
            st.warning("当前未配置 DEEPSEEK_API_KEY 或服务不可用，职业计划为本地示例，仅供参考。")
        st.session_state["career_ai_summary"] = summary

    if st.session_state.get("career_ai_summary"):
        st.markdown("#### 智能助手建议")
        st.markdown(st.session_state["career_ai_summary"])
        md_content = st.session_state["career_ai_summary"]
        st.download_button(
            "下载职业行动计划（Markdown）",
            data=md_content.encode("utf-8"),
            file_name="career_plan.md",
            mime="text/markdown",
            key="download_career_plan",
        )


def render_career_chat(ai_agent: AIAgent):
    """Render multi-turn career chat assistant."""
    st.markdown("---")
    st.subheader("🗣 职业对话助手（多轮）")

    careers = st.session_state.get("career_recommendations", [])
    if not careers:
        st.info("先使用上面的『智能推荐职业 & 学习路径』生成职业列表，再来和职业助手对话。")
        return

    chat = st.session_state.get("career_chat", [])

    if chat:
        for msg in chat:
            if msg["role"] == "user":
                st.markdown(f"**你：** {msg['content']}")
            else:
                st.markdown(f"**职业助手：** {msg['content']}")
    else:
        st.caption("这里是一个可以持续追问的职业助手，你可以多轮补充自己的情况和疑问。")

    user_msg = st.text_area("输入你的问题，继续和职业助手聊：", key="career_chat_input")

    col_send, col_clear = st.columns([1, 1])
    with col_send:
        send_clicked = st.button("发送", key="career_chat_send")
    with col_clear:
        clear_clicked = st.button("清空对话", key="career_chat_clear")

    if clear_clicked:
        st.session_state["career_chat"] = []
        safe_rerun()
        return

    if not send_clicked:
        return

    if not user_msg.strip():
        st.warning("问题不能为空")
        return

    chat.append({"role": "user", "content": user_msg.strip()})

    interests_str = ", ".join(st.session_state.get("user_interests", [])) or "未设置"
    location = st.session_state.get("work_location", "全国")
    stage = _get_current_stage() or "未设置"

    careers_brief = "\n".join(
        [
            f"- {c.get('career')}（技能：{', '.join(c.get('skills', []))}；薪资：{c.get('salary','')}）"
            for c in careers[:5]
        ]
    )

    history_lines = []
    for m in chat:
        if m["role"] == "user":
            history_lines.append(f"学生：{m['content']}")
        else:
            history_lines.append(f"职业助手：{m['content']}")
    history_text = "\n".join(history_lines)

    prompt = build_career_chat_prompt(
        careers_brief=careers_brief,
        interests=interests_str,
        location=location,
        stage=stage,
        history_text=history_text,
    )

    with st.spinner("职业助手正在思考..."):
        ans = ai_agent.call(prompt, temperature=0.5, max_tokens=1500)

    if "【本地回退】" in ans:
        st.warning("当前智能体服务暂不可用，下面是本地示例回答，仅供参考。")

    chat.append({"role": "assistant", "content": ans})
    st.session_state["career_chat"] = chat
    safe_rerun()


def render_mixed_ai_plan(ai_agent: AIAgent):
    """Render AI-generated mixed recommendations action plan."""
    interests = st.session_state.get("user_interests", [])
    combined = st.session_state.get("combined_recs", [])
    stage = _get_current_stage() or "未设置"

    st.markdown("---")
    st.subheader("🤖 智能助手 · 综合行动路线")

    if not combined:
        st.info("先点击上面的『生成综合推荐』，再使用智能助手。")
        return

    force_refresh = st.checkbox("强制重新生成综合行动计划", key="mix_force_refresh")

    user_extra = st.text_area(
        "简单说一下你目前的时间精力和目标（可选），例如：每周能投入多久、短期目标是啥：",
        height=80,
        key="mix_ai_extra",
    )

    if st.button("让智能体基于这些推荐制定行动计划", key="mix_ai_btn2"):
        if st.session_state.get("mix_ai_plan") and not force_refresh:
            st.info(
                "已存在上一轮综合行动计划，向下滚动即可查看。如需重新生成，请勾选『强制重新生成综合行动计划』。"
            )
        else:
            brief = "\n".join(
                [
                    f"- [{item.get('type')}] {item.get('name')}（来源：{item.get('source')}，得分：{item.get('score')}；匹配原因：{item.get('match_reason')}）"
                    for item in combined[:15]
                ]
            )
            prompt = build_mixed_plan_prompt(
                brief_recs=brief,
                interests=", ".join(interests),
                stage=stage,
                extra=user_extra or "",
            )
            with st.spinner("智能体正在制定综合行动计划..."):
                plan = ai_agent.call(prompt, temperature=0.4, max_tokens=2200)
            if "【本地回退】" in plan:
                st.warning("当前未配置 DEEPSEEK_API_KEY 或服务不可用，综合行动计划为本地示例，仅供参考。")
            st.session_state["mix_ai_plan"] = plan

    if st.session_state.get("mix_ai_plan"):
        st.markdown("#### 智能助手给出的行动路线")
        st.markdown(st.session_state["mix_ai_plan"])
        md_content = st.session_state["mix_ai_plan"]
        st.download_button(
            "下载综合行动计划（Markdown）",
            data=md_content.encode("utf-8"),
            file_name="mixed_plan.md",
            mime="text/markdown",
            key="download_mixed_plan",
        )

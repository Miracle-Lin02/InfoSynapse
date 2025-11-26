# -*- coding: utf-8 -*-
"""
Tab 7: Combined recommendations (courses + practice + projects).
"""

from typing import Dict, Any
import streamlit as st
import pandas as pd

from utils.recommend import get_combined_recommendations
from shared.profiles import (
    _normalize_learning_item,
    _update_profile_field,
)
from shared.ai_helpers import render_tab_ai_helper, render_mixed_ai_plan


def render_mixed_tab(KB: Dict[str, Any], ai_agent, config: Dict[str, Any]):
    """Render the combined recommendations tab."""
    st.header("📊 综合推荐")
    interests = st.session_state.get("user_interests", [])
    current_user = st.session_state.get("user")
    username = current_user.get("username") if current_user else None
    
    st.markdown("---")

    if not interests:
        st.info("请在侧边栏选择兴趣标签")
    else:
        if st.button("生成综合推荐"):
            recs = get_combined_recommendations(
                KB, interests, max_items=config["RECOMMEND_MAX_ITEMS"]
            )
            st.session_state["combined_recs"] = recs
        recs = st.session_state.get("combined_recs", [])

        if recs:
            df = pd.DataFrame(recs)
            if "type" in df.columns:
                st.markdown("#### 推荐类型分布")
                type_counts = df["type"].value_counts()
                st.bar_chart(type_counts)

        if not recs:
            st.info("暂无推荐")
        else:
            for r in recs:
                st.markdown(
                    f"### {r.get('name')} — {r.get('source')} （得分: {r.get('score'):.1f}）"
                )
                if r.get("url"):
                    st.markdown(f"[链接]({r.get('url')})")
                st.write(r.get("desc", "")[:400])
                st.caption(f"匹配原因: {r.get('match_reason')}")
                rec_id = r.get("id") or r.get("name")
                btn_key = f"add_plan_{rec_id}"
                if st.button("加入我的学习计划", key=btn_key):
                    current_plan = st.session_state.get("my_learning_plan", [])
                    exists = any(
                        x.get("id") == rec_id and x.get("name") == r.get("name")
                        for x in current_plan
                    )
                    if not exists:
                        new_item = _normalize_learning_item(
                            {
                                "id": rec_id,
                                "name": r.get("name"),
                                "source": r.get("source"),
                                "type": r.get("type"),
                                "status": "todo",
                            }
                        )
                        current_plan.append(new_item)
                        st.session_state["my_learning_plan"] = current_plan
                        if username:
                            _update_profile_field(
                                username,
                                learning_plan=current_plan,
                            )
                        st.success("已加入『我的学习计划』")
                    else:
                        st.info("该项已在『我的学习计划』中")
                st.divider()

        render_mixed_ai_plan(ai_agent)
        render_tab_ai_helper(
            "mixed",
            "综合推荐页面（补充提问）",
            ai_agent,
            context="当前兴趣：" + ", ".join(interests),
        )

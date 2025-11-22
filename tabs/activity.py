# -*- coding: utf-8 -*-
"""
User Activity Tab: Display browsing history and bookmarks.
"""

import streamlit as st
from typing import Dict, Any
from datetime import datetime

from utils.user_activity import get_history, get_bookmarks, remove_bookmark


def render_activity_tab(kb: Dict[str, Any]):
    """Render the user activity tab."""
    user_info = st.session_state.get("user") or {}
    username = user_info.get("username", "") if user_info else ""
    
    if not username:
        st.warning("请先登录以查看您的收藏历史和收藏")
        return
    
    st.header("📊 我的动态")
    
    # Usage guide
    with st.expander("💡 如何使用收藏功能", expanded=False):
        st.markdown("""
        **使用步骤：**
        
        1. **搜索内容**：前往 🔍 搜索 标签页，输入关键词搜索课程、导师或实践资源
        2. **收藏内容**：在搜索结果中，点击展开感兴趣的项目，然后点击 ☆ 收藏 按钮
        3. **查看收藏**：返回本页面，在 ⭐ 我的收藏 标签中查看所有收藏的内容
        
        **注意事项：**
        - 📜 收藏历史会自动记录您收藏过的项目
        - ⭐ 收藏功能目前通过搜索页面使用
        - 🔄 未来版本将支持在其他页面直接收藏
        
        **小提示：**
        使用搜索功能可以快速找到您需要的课程、导师和实践资源，比浏览所有页面更高效！
        """)
    
    st.markdown("---")
    
    activity_tabs = st.tabs(["📜 收藏历史", "⭐ 我的收藏"])
    
    # History tab
    with activity_tabs[0]:
        st.subheader("最近收藏")
        history = get_history(username, limit=30)
        
        if not history:
            st.info("暂无收藏记录")
        else:
            for item in history:
                item_type = item.get("type", "")
                item_name = item.get("name", "")
                timestamp = item.get("timestamp", "")
                
                # Format timestamp
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    time_str = timestamp
                
                # Icon based on type
                icon = {
                    "course": "📚",
                    "advisor": "👨‍🏫",
                    "practice": "🏫",
                    "career": "💼",
                    "github": "⭐"
                }.get(item_type, "📄")
                
                type_name = {
                    "course": "课程",
                    "advisor": "导师",
                    "practice": "实践",
                    "career": "职业",
                    "github": "项目"
                }.get(item_type, "项目")
                
                st.markdown(f"{icon} **{item_name}** · {type_name} · {time_str}")
    
    # Bookmarks tab
    with activity_tabs[1]:
        st.subheader("我的收藏")
        bookmarks = get_bookmarks(username)
        
        if not bookmarks:
            st.info("暂无收藏内容")
        else:
            for item in bookmarks:
                item_type = item.get("type", "")
                item_id = item.get("id", "")
                item_name = item.get("name", "")
                timestamp = item.get("timestamp", "")
                
                # Format timestamp
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    time_str = timestamp
                
                # Icon based on type
                icon = {
                    "course": "📚",
                    "advisor": "👨‍🏫",
                    "practice": "🏫",
                    "career": "💼",
                    "github": "⭐"
                }.get(item_type, "📄")
                
                type_name = {
                    "course": "课程",
                    "advisor": "导师",
                    "practice": "实践",
                    "career": "职业",
                    "github": "项目"
                }.get(item_type, "内容")
                
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"{icon} **{item_name}** · {type_name} · {time_str}")
                with col2:
                    if st.button("🗑️", key=f"remove_{item_type}_{item_id}", help="取消收藏"):
                        remove_bookmark(username, item_type, item_id)
                        st.rerun()

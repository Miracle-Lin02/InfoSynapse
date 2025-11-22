# -*- coding: utf-8 -*-
"""
Tab 6: Community discussion board.
"""

from typing import Dict, Any
import streamlit as st

from utils.community import (
    list_threads,
    create_thread,
    get_thread,
    add_post,
    delete_post,
    delete_thread,
    toggle_like_thread,
    toggle_like_post,
    get_like_count,
    is_liked_by,
)
from shared.ai_helpers import render_tab_ai_helper, safe_rerun

# Import notification utilities
try:
    from utils.notifications import add_notification
except Exception:
    add_notification = None


def render_community_tab(KB: Dict[str, Any], ai_agent):
    """Render the community discussion board tab."""
    st.header("🌐 社区讨论")
    
    threads = list_threads()
    st.subheader("创建新话题")
    current_user = st.session_state.get("user")
    if current_user:
        new_title = st.text_input("话题标题", key="new_thread_title")
        
        # Add ideological topic category option
        topic_category = st.selectbox(
            "话题类型",
            ["技术讨论", "学习交流", "求职经验", "思政话题", "其他"],
            key="new_thread_category",
            help="选择'思政话题'可标记为价值引领类话题"
        )
        
        new_content = st.text_area("首帖内容", key="new_thread_content", height=140)
        if st.button("创建话题"):
            if not new_title.strip() or not new_content.strip():
                st.warning("标题和内容不能为空")
            else:
                # Add category prefix for ideological topics
                title_with_category = new_title.strip()
                if topic_category == "思政话题":
                    title_with_category = f"【思政】{new_title.strip()}"
                
                create_thread(
                    title_with_category,
                    current_user.get("username"),
                    current_user.get("display_name"),
                    new_content.strip(),
                    category=topic_category,
                )
                st.success("话题已创建")
                safe_rerun()
    else:
        st.info("登录后可创建话题/回复")

    st.markdown("---")
    st.subheader("话题列表")
    
    # Add topic filter
    col_filter1, col_filter2 = st.columns([3, 1])
    with col_filter1:
        filter_category = st.selectbox(
            "筛选话题类型",
            ["全部", "技术讨论", "学习交流", "求职经验", "思政话题", "其他"],
            key="community_filter_category",
            help="根据话题类型筛选帖子"
        )
    with col_filter2:
        st.write("")  # Spacing
    
    # Filter threads based on selection
    if filter_category == "全部":
        filtered_threads = threads
    else:
        filtered_threads = [t for t in threads if t.get("category", "其他") == filter_category]
    
    context_lines = []
    if not filtered_threads:
        if filter_category == "全部":
            st.info("尚无话题")
        else:
            st.info(f"暂无『{filter_category}』类型的话题")
    else:
        for t in filtered_threads:
            context_lines.append(t.get("title", ""))
            category = t.get("category", "其他")
            category_badge = ""
            if category == "思政话题":
                category_badge = " 🎓"
            elif category == "技术讨论":
                category_badge = " 💻"
            elif category == "学习交流":
                category_badge = " 📚"
            elif category == "求职经验":
                category_badge = " 💼"
            
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.markdown(f"### {t.get('title')}{category_badge}")
                st.caption(
                    f"类型：{category} | 由 {t.get('created_by_name')} 于 {t.get('created_at')}"
                )
                snippet = (
                    (t.get("posts", []) or [])[0].get("content", "")[:300]
                    if t.get("posts")
                    else ""
                )
                st.write(snippet)
            with col2:
                # Like button
                like_count = get_like_count(t)
                if current_user:
                    is_liked = is_liked_by(t, current_user.get("username"))
                    like_icon = "❤️" if is_liked else "🤍"
                    if st.button(f"{like_icon} {like_count}", key=f"like_thread_{t.get('id')}"):
                        toggle_like_thread(t.get('id'), current_user.get("username"))
                        safe_rerun()
                else:
                    st.caption(f"🤍 {like_count}")
            with col3:
                if st.button("查看话题", key=f"open_{t.get('id')}"):
                    st.session_state["open_thread"] = t.get("id")
                    safe_rerun()
                # Add admin delete button for threads
                if st.session_state.get("admin_authenticated"):
                    if st.button("🗑 删除", key=f"delthread_{t.get('id')}"):
                        if delete_thread(t.get("id")):
                            st.success("已删除话题")
                            safe_rerun()
                        else:
                            st.error("删除失败")
            st.divider()

    if st.session_state.get("open_thread"):
        tid = st.session_state.get("open_thread")
        thread = get_thread(tid)
        if thread:
            st.markdown("---")
            col_header1, col_header2 = st.columns([5, 1])
            with col_header1:
                st.header(thread.get("title"))
                category = thread.get("category", "其他")
                st.caption(
                    f"类型：{category} | 由 {thread.get('created_by_name')} 创建于 {thread.get('created_at')}"
                )
            with col_header2:
                # Admin can delete entire thread
                if st.session_state.get("admin_authenticated"):
                    if st.button("🗑 删除话题", key="delete_thread_detail"):
                        if delete_thread(tid):
                            st.success("已删除话题")
                            st.session_state["open_thread"] = None
                            safe_rerun()
                        else:
                            st.error("删除失败")
            
            for p in thread.get("posts", []):
                col_post1, col_post2 = st.columns([5, 1])
                with col_post1:
                    st.markdown(
                        f"**{p.get('author_name') or p.get('author')}**  ·  {p.get('time')}"
                    )
                    st.write(p.get("content"))
                with col_post2:
                    # Like button for posts
                    post_like_count = get_like_count(p)
                    if current_user:
                        post_is_liked = is_liked_by(p, current_user.get("username"))
                        post_like_icon = "❤️" if post_is_liked else "🤍"
                        if st.button(f"{post_like_icon} {post_like_count}", key=f"like_post_{p.get('id')}"):
                            toggle_like_post(tid, p.get('id'), current_user.get("username"))
                            safe_rerun()
                    else:
                        st.caption(f"🤍 {post_like_count}")
                    
                    # Admin delete button
                    if st.session_state.get("admin_authenticated"):
                        if st.button(
                            "🗑 删除", key=f"delpost_{p.get('id')}"
                        ):
                            delete_post(tid, p.get("id"))
                            st.success("已删除")
                            safe_rerun()
                st.divider()
            st.markdown("----")
            if current_user:
                reply = st.text_area("回复该话题", key="reply_content")
                if st.button("发表回复"):
                    if not reply.strip():
                        st.warning("回复不能为空")
                    else:
                        add_post(
                            tid,
                            current_user.get("username"),
                            current_user.get("display_name"),
                            reply.strip(),
                        )
                        
                        # Trigger notification for thread creator and all participants
                        if add_notification:
                            # Notify thread creator
                            thread_creator = thread.get("created_by")
                            if thread_creator and thread_creator != current_user.get("username"):
                                try:
                                    add_notification(
                                        username=thread_creator,
                                        notification_type="reply",
                                        title="新回复通知",
                                        message=f"{current_user.get('display_name')} 回复了你的话题「{thread.get('title')}」",
                                        link=f"thread_{tid}",
                                        metadata={"thread_id": tid}
                                    )
                                except Exception:
                                    pass  # Silently fail if notification fails
                            
                            # Notify all post authors (except self and creator already notified)
                            notified_users = {current_user.get("username"), thread_creator}
                            for post in thread.get("posts", []):
                                post_author = post.get("author")
                                if post_author and post_author not in notified_users:
                                    try:
                                        add_notification(
                                            username=post_author,
                                            notification_type="reply",
                                            title="新回复通知",
                                            message=f"{current_user.get('display_name')} 在话题「{thread.get('title')}」中发表了新回复",
                                            link=f"thread_{tid}",
                                            metadata={"thread_id": tid}
                                        )
                                        notified_users.add(post_author)
                                    except Exception:
                                        pass
                        
                        st.success("已发表")
                        safe_rerun()
            else:
                st.info("请登录以回复")
            if st.button("返回列表"):
                st.session_state["open_thread"] = None
                safe_rerun()

    render_tab_ai_helper(
        "community",
        "社区讨论",
        ai_agent,
        context="当前话题示例：" + ", ".join(context_lines[:15]),
    )

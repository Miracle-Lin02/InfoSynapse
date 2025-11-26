# -*- coding: utf-8 -*-
"""
InfoSynapse: Intelligent Course & Career Recommendation System
Entry point for the Streamlit application.
"""

import os
import logging
import time
import traceback
from typing import Dict, Any

import streamlit as st

from utils.knowledge_loader import load_knowledge_base
from utils.auth import register_user, verify_password
from utils.recommend import AIAgent

try:
    from utils.github_crawler import GitHubCrawler
except Exception:
    GitHubCrawler = None

try:
    from utils.search_client import SearchClient
except Exception:
    SearchClient = None

try:
    from utils.agent_recommender import AgentRecommender
except Exception:
    AgentRecommender = None

# Import shared utilities
from shared.profiles import _sync_profile_to_session, get_user_profile
from shared.ai_helpers import safe_rerun
from shared.config import (
    KB_PATH,
    USER_PROFILE_PATH,
    CAREER_FEEDBACK_PATH,
    DEFAULT_WEIGHTS,
    CONFIG,
)

# Import tab rendering functions
from tabs.profile import render_profile_tab
from tabs.courses import render_courses_tab
from tabs.advisors import render_advisors_tab
from tabs.practice import render_practice_tab
from tabs.career import render_career_tab

# Import notification utilities
try:
    from utils.notifications import get_notifications, get_unread_count, mark_as_read, clear_notifications
except Exception:
    get_notifications = None
    get_unread_count = None
    mark_as_read = None
    clear_notifications = None
from tabs.github_tab import render_github_tab
from tabs.community import render_community_tab
from tabs.mixed import render_mixed_tab
from tabs.admin import render_admin_tab
from tabs.search import render_search_tab
from tabs.activity import render_activity_tab

LOGLEVEL = os.getenv("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=LOGLEVEL)
logger = logging.getLogger("infosynapse")


def _load_kb():
    """Load knowledge base from database or JSON file."""
    try:
        return load_knowledge_base(KB_PATH)
    except Exception as e:
        logger.error(f"加载知识库失败: {e}")
        return {}

# Note: KB is loaded lazily via session state to ensure Streamlit secrets are available
KB = {}


def load_secret(name: str) -> str:
    try:
        v = st.secrets.get(name, "") if hasattr(st, "secrets") else ""
    except Exception:
        v = ""
    if not v:
        v = os.getenv(name, "") or ""
    return v


DEEPSEEK_API_KEY = load_secret("DEEPSEEK_API_KEY")
GITHUB_TOKEN = load_secret("GITHUB_TOKEN")
SEARCH_PROVIDER = (load_secret("SEARCH_API_PROVIDER") or "").lower()
SEARCH_KEY = load_secret("SEARCH_API_KEY")
ADMIN_PASS = load_secret("ADMIN_PASS")
# DeepSeek API 超时设置（秒），默认 120 秒
DEEPSEEK_TIMEOUT = int(load_secret("DEEPSEEK_TIMEOUT") or "120")

ai_agent = AIAgent(api_key=DEEPSEEK_API_KEY, timeout=DEEPSEEK_TIMEOUT)

# Initialize LangChain Agent with RAG support
try:
    from utils.langchain_agent import get_langchain_agent
    from utils.rag_knowledge_base import get_rag_knowledge_base
    
    # Initialize RAG knowledge base and load data
    rag_kb = get_rag_knowledge_base()
    if rag_kb.available:
        # RAG will be loaded lazily after session initialization when KB data is available
        logger.info("RAG knowledge base initialized, will load data after session setup")
    
    # Create LangChain agent with RAG enabled
    langchain_agent = get_langchain_agent(enable_memory=True, enable_rag=True)
    
    # Use LangChain agent if available, fallback to simple agent
    if langchain_agent.available:
        ai_agent = langchain_agent
        logger.info("Using LangChain Agent with RAG support")
    else:
        logger.warning("LangChain not available, using simple AIAgent")
except Exception as e:
    logger.warning(f"Failed to initialize LangChain/RAG: {e}")
    # Continue with simple agent

if "_global_ai_agent" not in st.session_state:
    st.session_state["_global_ai_agent"] = ai_agent

github_crawler = GitHubCrawler(token=GITHUB_TOKEN or None) if GitHubCrawler else None
search_client = (
    SearchClient(provider=SEARCH_PROVIDER, api_key=SEARCH_KEY)
    if (SearchClient and SEARCH_PROVIDER and SEARCH_KEY)
    else None
)
agent_recommender = (
    AgentRecommender(ai_agent, KB, github_crawler, search_client)
    if (AgentRecommender and github_crawler)
    else None
)



def initialize_session():
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "admin_authenticated" not in st.session_state:
        st.session_state["admin_authenticated"] = False
    if "admin_user" not in st.session_state:
        st.session_state["admin_user"] = ""
    if "github_repos" not in st.session_state:
        st.session_state["github_repos"] = []
    if "combined_recs" not in st.session_state:
        st.session_state["combined_recs"] = []
    if "agent_recs" not in st.session_state:
        st.session_state["agent_recs"] = []
    if "user_interests" not in st.session_state:
        st.session_state["user_interests"] = []
    if "open_thread" not in st.session_state:
        st.session_state["open_thread"] = None
    if "recommended_jobs" not in st.session_state:
        st.session_state["recommended_jobs"] = []
    if "career_recommendations" not in st.session_state:
        st.session_state["career_recommendations"] = []
    if "learning_paths" not in st.session_state:
        st.session_state["learning_paths"] = {}
    if "agent_project_recs" not in st.session_state:
        st.session_state["agent_project_recs"] = []
    if "career_ai_summary" not in st.session_state:
        st.session_state["career_ai_summary"] = ""
    if "mix_ai_plan" not in st.session_state:
        st.session_state["mix_ai_plan"] = ""
    if "github_topics_used" not in st.session_state:
        st.session_state["github_topics_used"] = []
    if "github_fetch_count" not in st.session_state:
        st.session_state["github_fetch_count"] = 0
    if "tab_ai_answers" not in st.session_state:
        st.session_state["tab_ai_answers"] = {}
    if "starred_repos" not in st.session_state:
        st.session_state["starred_repos"] = []
    if "finished_repos" not in st.session_state:
        st.session_state["finished_repos"] = []
    if "my_learning_plan" not in st.session_state:
        st.session_state["my_learning_plan"] = []
    if "career_chat" not in st.session_state:
        st.session_state["career_chat"] = []
    # Load knowledge base into session state if not already loaded
    if "_kb_data" not in st.session_state:
        st.session_state["_kb_data"] = _load_kb()
        
        # Initialize RAG with the loaded knowledge base data
        if "_rag_initialized" not in st.session_state:
            try:
                from utils.rag_knowledge_base import get_rag_knowledge_base
                rag_kb = get_rag_knowledge_base()
                if rag_kb.available:
                    stats = rag_kb.get_stats()
                    if stats.get('total_documents', 0) == 0:
                        logger.info("Loading knowledge base into RAG...")
                        doc_count = rag_kb.load_from_dict(st.session_state["_kb_data"])
                        logger.info(f"✅ Loaded {doc_count} documents into RAG knowledge base")
                st.session_state["_rag_initialized"] = True
            except Exception as e:
                logger.warning(f"Failed to initialize RAG: {e}")
                st.session_state["_rag_initialized"] = False

    for k, v in DEFAULT_WEIGHTS.items():
        if k not in st.session_state:
            st.session_state[k] = v


def get_kb():
    """Get the knowledge base from session state."""
    global KB
    if "_kb_data" in st.session_state:
        return st.session_state["_kb_data"]
    return KB


def _set_admin_authenticated_if_admin(user_info: Dict[str, Any]):
    """
    Helper function to automatically set admin_authenticated flag
    if the user has admin role.
    """
    if user_info and user_info.get("role") == "admin":
        st.session_state["admin_authenticated"] = True
        st.session_state["admin_user"] = user_info.get("username", "admin")


def main():
    st.set_page_config(
        page_title="InfoSynapse",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    initialize_session()

    if not DEEPSEEK_API_KEY:
        st.warning("当前未配置 DEEPSEEK_API_KEY，智能体使用的是本地示例回答，仅供体验。")
    else:
        # Check if RAG is enabled
        rag_status = ""
        try:
            from utils.rag_knowledge_base import get_rag_knowledge_base
            rag_kb = get_rag_knowledge_base()
            if rag_kb.available:
                stats = rag_kb.get_stats()
                doc_count = stats.get('total_documents', 0)
                if doc_count > 0:
                    rag_status = f" **✅ RAG知识库已启用** (已加载 {doc_count} 个文档，AI 可以检索课程、导师、实践等数据)"
                else:
                    rag_status = " ⚠️ RAG知识库未加载数据"
        except Exception:
            pass
        
        st.info(f"已连接 DeepSeek API，页面中的智能助手回答来自在线模型。{rag_status}")

    current_user = st.session_state.get("user")
    current_username = current_user.get("display_name") if current_user else "未登录"

    col1, col2, col3 = st.columns([2, 3, 2])
    with col1:
        st.title("🎓 InfoSynapse")
    with col2:
        st.write("")
    with col3:
        st.markdown(
            f"""
        <div style='text-align: right'>
        <small>当前用户: <b>{current_username}</b></small>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # === Sidebar ===
    with st.sidebar:
        st.header("👤 账户与设置")
        user = st.session_state.get("user")

        if user:
            st.markdown("✅ **已登录**")
            st.markdown(f"👤 {user.get('display_name')} (@{user.get('username')})")
            st.markdown(f"🔖 {user.get('role')}")
            
            # Notification Center
            if get_notifications and get_unread_count:
                st.markdown("---")
                st.subheader("🔔 通知中心")
                username = user.get("username")
                unread_count = get_unread_count(username)
                
                # Display unread count badge
                if unread_count > 0:
                    st.markdown(f"**未读通知: {unread_count}**")
                else:
                    st.markdown("*暂无未读通知*")
                
                # Show/hide notifications toggle
                if st.checkbox("显示通知", key="show_notifications"):
                    notifications = get_notifications(username, unread_only=False)
                    
                    if notifications:
                        # Show latest 10 notifications
                        for notif in notifications[:10]:
                            notif_type = notif.get("type", "")
                            message = notif.get("message", "")
                            # Ensure message is a string
                            if not isinstance(message, str):
                                message = str(message) if message else ""
                            timestamp = notif.get("timestamp", "")
                            is_read = notif.get("read", False)
                            notif_id = notif.get("id", "")
                            
                            # Icon based on type
                            icon = "💬" if notif_type == "reply" else "📢" if notif_type == "announcement" else "📧"
                            read_status = "✓" if is_read else "●"
                            
                            # Truncate message for expander title
                            message_preview = message[:30] + "..." if len(message) > 30 else message
                            with st.expander(f"{icon} {read_status} {message_preview}", expanded=False):
                                st.write(message)
                                st.caption(timestamp)
                                if not is_read:
                                    if st.button("标记已读", key=f"mark_read_{notif_id}"):
                                        mark_as_read(username, notif_id)
                                        safe_rerun()
                        
                        # Clear all button
                        if st.button("清空所有通知"):
                            clear_notifications(username)
                            st.success("已清空所有通知")
                            safe_rerun()
                    else:
                        st.info("暂无通知")
            
            st.markdown("---")
            if st.button("📤 登出"):
                st.session_state["user"] = None
                st.session_state["admin_authenticated"] = False
                st.success("已登出")
                safe_rerun()
        else:
            st.subheader("🔐 用户登录")
            with st.form("login_form", clear_on_submit=True):
                login_user = st.text_input("用户名")
                login_pwd = st.text_input("密码", type="password")
                login_submit = st.form_submit_button("登录")
                if login_submit:
                    if not login_user or not login_pwd:
                        st.error("用户名和密码不能为空")
                    else:
                        res = verify_password(login_user, login_pwd)
                        if res.get("success"):
                            user_info = res.get("user")
                            st.session_state["user"] = user_info
                            # Automatically set admin authentication if user has admin role
                            _set_admin_authenticated_if_admin(user_info)
                            _sync_profile_to_session(user_info["username"], st.session_state)
                            st.success(res.get("msg"))
                            time.sleep(0.5)
                            safe_rerun()
                        else:
                            st.error(res.get("msg"))

            st.markdown("---")
            st.subheader("📝 用户注册")
            with st.form("register_form", clear_on_submit=True):
                reg_user = st.text_input("用户名")
                reg_display = st.text_input("显示名（可选）")
                reg_pwd = st.text_input("密码", type="password")
                reg_pwd2 = st.text_input("确认密码", type="password")
                reg_admin_flag = st.checkbox("注册为管理员（需要 ADMIN_PASS）")
                # Always show admin pass field, but only require it when checkbox is checked
                reg_admin_pass = st.text_input(
                    "管理员口令（仅管理员注册时需要）", 
                    type="password", 
                    key="reg_admin_pwd",
                    help="只有在勾选'注册为管理员'时才需要填写"
                )
                reg_submit = st.form_submit_button("注册")
                if reg_submit:
                    if not reg_user or not reg_pwd:
                        st.error("用户名和密码不能为空")
                    elif reg_pwd != reg_pwd2:
                        st.error("两次密码不一致")
                    else:
                        role = "admin" if reg_admin_flag else "user"
                        r = register_user(
                            reg_user.strip(),
                            reg_pwd.strip(),
                            display_name=reg_display.strip() or reg_user.strip(),
                            role=role,
                            admin_pass=reg_admin_pass,
                        )
                        if r.get("success"):
                            # Create user profile
                            _ = get_user_profile(reg_user.strip())
                            # Auto-login the user after successful registration
                            user_info = {
                                "username": reg_user.strip(),
                                "display_name": reg_display.strip() or reg_user.strip(),
                                "role": role
                            }
                            st.session_state["user"] = user_info
                            # Automatically set admin authentication if registered as admin
                            _set_admin_authenticated_if_admin(user_info)
                            _sync_profile_to_session(reg_user.strip(), st.session_state)
                            st.success(f"{r.get('msg')} 已自动登录！")
                            time.sleep(0.5)
                            safe_rerun()
                        else:
                            st.error(r.get("msg"))

        st.markdown("---")
        st.subheader("🎯 兴趣 & 推荐")
        available_tags = [
            "Python开发",
            "机器学习",
            "前端",
            "后端",
            "算法",
            "嵌入式",
            "区块链",
            "计算机视觉",
        ]
        st.multiselect(
            "兴趣标签（用于推荐）",
            available_tags,
            default=st.session_state.get("user_interests", []),
            key="user_interests",
        )

        locations = [
            "全国",
            "北京",
            "上海",
            "深圳",
            "杭州",
            "南京",
            "成都",
            "武汉",
            "西安",
            "广州",
        ]
        st.selectbox("工作地区", locations, index=0, key="work_location")

        st.markdown("---")
        st.subheader("⚖️ 实时评分权重")

        name_weight = st.number_input(
            "名称匹配权重",
            min_value=0.0,
            max_value=200.0,
            value=float(
                st.session_state.get(
                    "INTEREST_NAME_WEIGHT", DEFAULT_WEIGHTS["INTEREST_NAME_WEIGHT"]
                )
            ),
            step=1.0,
            key="INTEREST_NAME_WEIGHT_INPUT",
        )
        desc_weight = st.number_input(
            "描述匹配权重",
            min_value=0.0,
            max_value=200.0,
            value=float(
                st.session_state.get(
                    "INTEREST_DESC_WEIGHT", DEFAULT_WEIGHTS["INTEREST_DESC_WEIGHT"]
                )
            ),
            step=1.0,
            key="INTEREST_DESC_WEIGHT_INPUT",
        )
        st.session_state["INTEREST_NAME_WEIGHT"] = name_weight
        st.session_state["INTEREST_DESC_WEIGHT"] = desc_weight

        st.markdown("**评分模式预设**")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            if st.button("偏课程", key="preset_course"):
                st.session_state["INTEREST_NAME_WEIGHT"] = 22.0
                st.session_state["INTEREST_DESC_WEIGHT"] = 28.0
                st.session_state["KB_BASE_SCORE"] = 8.0
                st.session_state["SOURCE_KB_BONUS"] = 3.0
                st.success("已应用『偏课程』模式")
        with col_p2:
            if st.button("偏项目", key="preset_project"):
                st.session_state["INTEREST_NAME_WEIGHT"] = 36.0
                st.session_state["INTEREST_DESC_WEIGHT"] = 16.0
                st.session_state["GITHUB_STAR_WEIGHT_FACTOR"] = 8.0
                st.session_state["SOURCE_GITHUB_BONUS"] = 7.0
                st.success("已应用『偏项目』模式")
        with col_p3:
            if st.button("偏求职", key="preset_job"):
                st.session_state["INTEREST_NAME_WEIGHT"] = 28.0
                st.session_state["INTEREST_DESC_WEIGHT"] = 24.0
                st.session_state["KB_BASE_SCORE"] = 7.0
                st.session_state["SOURCE_KB_BONUS"] = 3.0
                st.success("已应用『偏求职』模式")

        if st.button("恢复默认权重", key="reset_weights"):
            for k, v in DEFAULT_WEIGHTS.items():
                st.session_state[k] = v
            st.success("已恢复默认评分权重")

    # === Tabs ===
    tabs = st.tabs(
        [
            "👤 个人主页",
            "🔍 搜索",
            "📊 我的动态",
            "🏫 课程",
            "👩‍🏫 导师",
            "🏫 校内实践",
            "💼 求职",
            "⭐ GitHub",
            "🌐 社区",
            "📊 综合推荐",
            "🔧 管理(审核)",
        ]
    )

    # Get KB from session state (loaded from database if configured)
    KB = get_kb()

    # ---- Tab 0: 个人主页 ----
    with tabs[0]:
        render_profile_tab(KB, ai_agent, available_tags)

    # ---- Tab 1: 搜索 ----
    with tabs[1]:
        render_search_tab(KB)

    # ---- Tab 2: 我的动态 ----
    with tabs[2]:
        render_activity_tab(KB)

    # ---- Tab 3: 课程 ----
    with tabs[3]:
        render_courses_tab(KB_PATH, KB, ai_agent)

    # ---- Tab 4: 导师 ----
    with tabs[4]:
        render_advisors_tab(KB_PATH, KB, ai_agent)

    # ---- Tab 5: 校内实践 ----
    with tabs[5]:
        render_practice_tab(KB, ai_agent)

    # ---- Tab 6: 求职 ----
    with tabs[6]:
        render_career_tab(KB, ai_agent)

    # ---- Tab 7: GitHub ----
    with tabs[7]:
        render_github_tab(KB, ai_agent, github_crawler)

    # ---- Tab 8: 社区 ----
    with tabs[8]:
        render_community_tab(KB, ai_agent)

    # ---- Tab 9: 综合推荐 ----
    with tabs[9]:
        render_mixed_tab(KB, ai_agent, CONFIG)

    # ---- Tab 10: 管理 / 审核 ----
    with tabs[10]:
        render_admin_tab(KB_PATH, KB, ai_agent, ADMIN_PASS)

    st.markdown("---")
    st.caption(
        "说明：该应用为杭州电子科技大学易班大赛-智能体AIGC应用演示版。如在使用中遇到问题，欢迎前往 GitHub 仓库提交 issue 或 PR：https://github.com/Miracle-Lin02/InfoSynapse"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error("主程序异常: " + str(e))
        traceback.print_exc()
        try:
            st.error("应用发生未捕获异常，请查看终端日志。错误：" + str(e))
        except Exception:
            pass
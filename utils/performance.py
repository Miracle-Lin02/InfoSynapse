# -*- coding: utf-8 -*-
"""
Performance optimization utilities: caching and pagination.
"""

import streamlit as st
from typing import List, Tuple, Any
import time


def paginate_items(items: List[Any], page: int = 1, per_page: int = 20) -> Tuple[List[Any], dict]:
    """
    Paginate a list of items.
    
    Args:
        items: List of items to paginate
        page: Current page number (1-indexed)
        per_page: Number of items per page
        
    Returns:
        Tuple of (paginated_items, pagination_info)
    """
    total_items = len(items)
    total_pages = max(1, (total_items + per_page - 1) // per_page)
    
    # Ensure page is within bounds
    page = max(1, min(page, total_pages))
    
    # Calculate slice indices
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_items)
    
    paginated_items = items[start_idx:end_idx]
    
    pagination_info = {
        "current_page": page,
        "total_pages": total_pages,
        "per_page": per_page,
        "total_items": total_items,
        "start_idx": start_idx + 1,  # 1-indexed for display
        "end_idx": end_idx,
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }
    
    return paginated_items, pagination_info


def render_pagination_controls(pagination_info: dict, key_prefix: str = "page"):
    """
    Render pagination controls in Streamlit.
    
    Args:
        pagination_info: Pagination information from paginate_items()
        key_prefix: Unique prefix for Streamlit widget keys
        
    Returns:
        Selected page number
    """
    if pagination_info["total_pages"] <= 1:
        return pagination_info["current_page"]
    
    col1, col2, col3, col4 = st.columns([2, 3, 2, 2])
    
    with col1:
        st.markdown(f"**显示 {pagination_info['start_idx']}-{pagination_info['end_idx']} / 共 {pagination_info['total_items']} 项**")
    
    with col2:
        per_page_options = [10, 20, 50, 100]
        current_per_page = pagination_info["per_page"]
        if current_per_page not in per_page_options:
            per_page_options.append(current_per_page)
            per_page_options.sort()
        
        selected_per_page = st.selectbox(
            "每页显示",
            per_page_options,
            index=per_page_options.index(current_per_page),
            key=f"{key_prefix}_per_page"
        )
        
        if selected_per_page != current_per_page:
            st.session_state[f"{key_prefix}_per_page_value"] = selected_per_page
            st.session_state[f"{key_prefix}_page_num"] = 1
            st.rerun()
    
    with col3:
        page_num = st.number_input(
            "页码",
            min_value=1,
            max_value=pagination_info["total_pages"],
            value=pagination_info["current_page"],
            key=f"{key_prefix}_input"
        )
        
        if page_num != pagination_info["current_page"]:
            st.session_state[f"{key_prefix}_page_num"] = page_num
            st.rerun()
    
    with col4:
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("⬅️ 上一页", disabled=not pagination_info["has_prev"], key=f"{key_prefix}_prev"):
                st.session_state[f"{key_prefix}_page_num"] = pagination_info["current_page"] - 1
                st.rerun()
        with col_next:
            if st.button("下一页 ➡️", disabled=not pagination_info["has_next"], key=f"{key_prefix}_next"):
                st.session_state[f"{key_prefix}_page_num"] = pagination_info["current_page"] + 1
                st.rerun()
    
    return pagination_info["current_page"]


def get_page_state(key_prefix: str) -> Tuple[int, int]:
    """
    Get current page and per_page values from session state.
    
    Args:
        key_prefix: Unique prefix for session state keys
        
    Returns:
        Tuple of (page_num, per_page)
    """
    page_num = st.session_state.get(f"{key_prefix}_page_num", 1)
    per_page = st.session_state.get(f"{key_prefix}_per_page_value", 20)
    return page_num, per_page


def show_performance_metrics(start_time: float, item_count: int):
    """
    Show performance metrics for data loading.
    
    Args:
        start_time: Start time from time.time()
        item_count: Number of items loaded
    """
    elapsed = time.time() - start_time
    st.caption(f"⚡ 加载时间: {elapsed:.3f}秒 | 项目数: {item_count}")

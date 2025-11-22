# -*- coding: utf-8 -*-
"""
通知模块：Slack / 邮件 / 审核日志标记
"""

import os
import json
import logging
from typing import List, Dict, Any

import requests
from email.mime.text import MIMEText

from .knowledge_loader import load_knowledge_base, save_knowledge_base

logger = logging.getLogger("notify")


def _load_secret(name: str) -> str:
    try:
        import streamlit as st

        v = st.secrets.get(name, "") if hasattr(st, "secrets") else ""
    except Exception:
        v = ""
    if not v:
        v = os.getenv(name, "") or ""
    return v


SLACK_WEBHOOK = _load_secret("SLACK_WEBHOOK")
SMTP_HOST = _load_secret("SMTP_HOST")
SMTP_PORT = int(_load_secret("SMTP_PORT") or 0) if _load_secret("SMTP_PORT") else 0
SMTP_USER = _load_secret("SMTP_USER")
SMTP_PASS = _load_secret("SMTP_PASS")
ADMIN_EMAILS = [
    e.strip() for e in (_load_secret("ADMIN_EMAILS") or "").split(",") if e.strip()
]


def send_slack_notification(text: str) -> bool:
    if not SLACK_WEBHOOK:
        return False
    try:
        resp = requests.post(SLACK_WEBHOOK, json={"text": text}, timeout=8)
        return resp.status_code == 200
    except Exception as e:
        logger.warning(f"Slack notify failed: {e}")
        return False


def send_email(subject: str, body: str, recipients: List[str]) -> bool:
    if not SMTP_HOST or not SMTP_PORT or not recipients:
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER or "infosynapse@example.com"
        msg["To"] = ", ".join(recipients)

        import smtplib

        s = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
        s.ehlo()
        if SMTP_USER and SMTP_PASS:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(msg["From"], recipients, msg.as_string())
        s.quit()
        return True
    except Exception as e:
        logger.warning(f"Email notify failed: {e}")
        return False


def notify_admins_new_pending(pending: Dict[str, Any]):
    from datetime import datetime, timezone

    title = f"[InfoSynapse] 新待审核评价：{pending.get('target_type')}={pending.get('target_id')}"
    text = (
        f"提交者: {pending.get('reviewer')}\n"
        f"目标: {pending.get('target_type')}={pending.get('target_id')}\n"
        f"评分: {pending.get('rating')}\n"
        f"时间: {pending.get('time')}\n\n"
        f"{pending.get('comment')}"
    )
    ok1 = send_slack_notification(title + "\n\n" + text) if SLACK_WEBHOOK else False
    ok2 = send_email(title, text, ADMIN_EMAILS) if ADMIN_EMAILS and SMTP_HOST else False
    logger.info(f"notify_admins_new_pending slack={ok1} email={ok2}")


def notify_admins_moderation_action(
    pending_id: str, action: str, admin_user: str, reason: str = ""
):
    from datetime import datetime, timezone

    title = f"[InfoSynapse] pending {pending_id} 已 {action} by {admin_user}"
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    text = (
        f"pending_id: {pending_id}\n"
        f"action: {action}\n"
        f"admin: {admin_user}\n"
        f"reason: {reason}\n"
        f"时间: {now_str}"
    )
    ok1 = send_slack_notification(title + "\n\n" + text) if SLACK_WEBHOOK else False
    ok2 = send_email(title, text, ADMIN_EMAILS) if ADMIN_EMAILS and SMTP_HOST else False
    logger.info(f"notify_admins_moderation_action slack={ok1} email={ok2}")


def annotate_moderation_log_with_admin(
    kb_path: str, pending_id: str, action: str, admin_user: str, reason: str = ""
) -> bool:
    """
    在 moderation_log 中补充 admin_user 和 reason 信息。
    """
    try:
        kb_new = load_knowledge_base(kb_path)
        modlog = kb_new.get("moderation_log", []) or []
        updated = False
        for entry in modlog:
            if entry.get("pending_id") == pending_id and entry.get("action") == action:
                entry["admin_user"] = admin_user
                if reason:
                    entry["reason"] = reason
                updated = True
                break
        if updated:
            save_knowledge_base(kb_path, kb_new)
            return True
        return False
    except Exception as e:
        logger.warning(f"annotate_moderation_log_with_admin error: {e}")
        return False
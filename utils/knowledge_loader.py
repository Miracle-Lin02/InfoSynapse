# -*- coding: utf-8 -*-
"""
utils/knowledge_loader.py

扩展说明：
- KB 基础结构（courses / advisors / practice / jds / alumni / templates）
- pending_reviews：提交的学生评价先存为 pending（待审核），管理员可以 approve/reject。
- moderation_log：记录审核操作日志。
- 直接写入类接口：add_course_review / add_advisor_review
- 待审核接口：submit_course_review_pending / submit_advisor_review_pending /
  get_pending_reviews / approve_pending_review / reject_pending_review / get_moderation_log
- 图形化管理接口：
  - add_course / delete_course
  - add_advisor / delete_advisor
  - add_practice / delete_practice
- 保存时会自动备份原文件到 data/hdu_knowledge_base.json.bak.TIMESTAMP
"""
import json
import os
import shutil
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

KB_DEFAULT = {
    "courses": {},      # map major -> list of course dicts
    "advisors": [],     # list of advisor dicts
    "practice": [],     # practice resources
    "jds": [],          # job descriptions
    "alumni": [],       # alumni experiences
    "templates": {},
    "pending_reviews": [],   # list of pending review dicts
    "moderation_log": []     # moderation actions log
}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_knowledge_base(path: str) -> Dict[str, Any]:
    """
    Load knowledge base JSON. If file missing, return default structure.
    Ensure proper fields exist and reviews lists are initialized.
    """
    if not os.path.exists(path):
        kb = json.loads(json.dumps(KB_DEFAULT))
        return kb
    with open(path, "r", encoding="utf-8") as f:
        kb = json.load(f)
    # normalize top-level
    for key in [
        "courses",
        "advisors",
        "practice",
        "jds",
        "alumni",
        "templates",
        "pending_reviews",
        "moderation_log",
    ]:
        if key not in kb:
            kb[key] = KB_DEFAULT[key]
    # ensure reviews exist for courses and advisors
    for major, courselist in kb.get("courses", {}).items():
        for c in courselist:
            if "reviews" not in c or not isinstance(c.get("reviews"), list):
                c["reviews"] = []
    for a in kb.get("advisors", []):
        if "reviews" not in a or not isinstance(a.get("reviews"), list):
            a["reviews"] = []
    # ensure pending_reviews and moderation_log are lists
    if not isinstance(kb.get("pending_reviews", []), list):
        kb["pending_reviews"] = []
    if not isinstance(kb.get("moderation_log", []), list):
        kb["moderation_log"] = []
    return kb


def save_knowledge_base(path: str, kb: Dict[str, Any]) -> None:
    """
    Save KB to path. Before overwriting, create a timestamped backup.
    """
    if os.path.exists(path):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak_path = f"{path}.bak.{ts}"
        try:
            shutil.copy2(path, bak_path)
        except Exception:
            print(f"[knowledge_loader] Warning: failed to create backup {bak_path}")
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


# ---------------------- Convenience accessors ----------------------
def get_courses(kb: Dict[str, Any], major: str) -> List[Dict[str, Any]]:
    return kb.get("courses", {}).get(major, [])


def get_advisors(kb: Dict[str, Any], research_area: str = "") -> List[Dict[str, Any]]:
    advisors = kb.get("advisors", []) or []
    if research_area:
        q = research_area.lower()
        out = []
        for a in advisors:
            if (
                q in (a.get("research", "") or "").lower()
                or q in (a.get("department", "") or "").lower()
                or q in (a.get("name", "") or "").lower()
            ):
                out.append(a)
        return out
    return advisors


def get_practice(kb: Dict[str, Any]) -> List[Dict[str, Any]]:
    return kb.get("practice", []) or []


def get_jds(kb: Dict[str, Any]) -> List[Dict[str, Any]]:
    return kb.get("jds", []) or []


def get_alumni_experience(
    kb: Dict[str, Any], company: str = "", position: str = ""
) -> List[Dict[str, Any]]:
    out = []
    for rec in kb.get("alumni", []) or []:
        if company and company.lower() not in (rec.get("company", "") or "").lower():
            continue
        if position and position.lower() not in (rec.get("position", "") or "").lower():
            continue
        out.append(rec)
    return out


# ---------------------- Review operations (immediate write) ----------------------
def add_course_review(
    path: str, kb: Dict[str, Any], course_code: str, reviewer: str, rating: int, comment: str
) -> bool:
    if not course_code:
        return False
    found = False
    for major, courselist in kb.get("courses", {}).items():
        for c in courselist:
            code = c.get("code") or c.get("id") or ""
            if code and str(code) == str(course_code):
                if "reviews" not in c or not isinstance(c.get("reviews"), list):
                    c["reviews"] = []
                review = {
                    "reviewer": reviewer or "匿名",
                    "rating": int(rating) if rating else None,
                    "comment": comment or "",
                    "time": _now_iso(),
                }
                c["reviews"].insert(0, review)
                found = True
                break
        if found:
            break
    if not found:
        return False
    try:
        save_knowledge_base(path, kb)
        return True
    except Exception as e:
        print(f"[knowledge_loader] Error saving KB: {e}")
        return False


def add_advisor_review(
    path: str, kb: Dict[str, Any], advisor_name: str, reviewer: str, rating: int, comment: str
) -> bool:
    if not advisor_name:
        return False
    found = False
    for a in kb.get("advisors", []) or []:
        name = a.get("name", "") or ""
        if advisor_name.lower() in name.lower():
            if "reviews" not in a or not isinstance(a.get("reviews"), list):
                a["reviews"] = []
            review = {
                "reviewer": reviewer or "匿名",
                "rating": int(rating) if rating else None,
                "comment": comment or "",
                "time": _now_iso(),
            }
            a["reviews"].insert(0, review)
            found = True
            break
    if not found:
        return False
    try:
        save_knowledge_base(path, kb)
        return True
    except Exception as e:
        print(f"[knowledge_loader] Error saving KB: {e}")
        return False


# ---------------------- Pending (moderation) operations ----------------------
def submit_course_review_pending(
    path: str, kb: Dict[str, Any], course_code: str, reviewer: str, rating: int, comment: str
) -> Optional[str]:
    if not course_code:
        return None
    pending_id = str(uuid.uuid4())
    pending = {
        "id": pending_id,
        "target_type": "course",
        "target_id": str(course_code),
        "reviewer": reviewer or "匿名",
        "rating": int(rating) if rating else None,
        "comment": comment or "",
        "time": _now_iso(),
        "status": "pending",
        "submitted_via": "web",
    }
    if "pending_reviews" not in kb or not isinstance(kb.get("pending_reviews"), list):
        kb["pending_reviews"] = []
    kb["pending_reviews"].insert(0, pending)
    try:
        save_knowledge_base(path, kb)
        return pending_id
    except Exception as e:
        print(f"[knowledge_loader] Error saving pending review: {e}")
        return None


def submit_advisor_review_pending(
    path: str, kb: Dict[str, Any], advisor_name: str, reviewer: str, rating: int, comment: str
) -> Optional[str]:
    if not advisor_name:
        return None
    pending_id = str(uuid.uuid4())
    pending = {
        "id": pending_id,
        "target_type": "advisor",
        "target_id": advisor_name,
        "reviewer": reviewer or "匿名",
        "rating": int(rating) if rating else None,
        "comment": comment or "",
        "time": _now_iso(),
        "status": "pending",
        "submitted_via": "web",
    }
    if "pending_reviews" not in kb or not isinstance(kb.get("pending_reviews"), list):
        kb["pending_reviews"] = []
    kb["pending_reviews"].insert(0, pending)
    try:
        save_knowledge_base(path, kb)
        return pending_id
    except Exception as e:
        print(f"[knowledge_loader] Error saving pending advisor review: {e}")
        return None


def get_pending_reviews(kb: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        p
        for p in (kb.get("pending_reviews") or [])
        if p.get("status") == "pending"
    ]


def approve_pending_review(path: str, kb: Dict[str, Any], pending_id: str) -> bool:
    pending_list = kb.get("pending_reviews", []) or []
    idx = None
    pending = None
    for i, p in enumerate(pending_list):
        if p.get("id") == pending_id:
            idx = i
            pending = p
            break
    if idx is None or pending is None:
        return False
    ttype = pending.get("target_type")
    tid = pending.get("target_id")
    if ttype == "course":
        found = False
        for major, courselist in kb.get("courses", {}).items():
            for c in courselist:
                code = c.get("code") or c.get("id") or ""
                if code and str(code) == str(tid):
                    if "reviews" not in c or not isinstance(c.get("reviews"), list):
                        c["reviews"] = []
                    c["reviews"].insert(
                        0,
                        {
                            "reviewer": pending.get("reviewer"),
                            "rating": pending.get("rating"),
                            "comment": pending.get("comment"),
                            "time": pending.get("time"),
                        },
                    )
                    found = True
                    break
            if found:
                break
        if not found:
            return False
    elif ttype == "advisor":
        found = False
        for a in kb.get("advisors", []) or []:
            name = a.get("name", "") or ""
            if tid.lower() in name.lower():
                if "reviews" not in a or not isinstance(a.get("reviews"), list):
                    a["reviews"] = []
                a["reviews"].insert(
                    0,
                    {
                        "reviewer": pending.get("reviewer"),
                        "rating": pending.get("rating"),
                        "comment": pending.get("comment"),
                        "time": pending.get("time"),
                    },
                )
                found = True
                break
        if not found:
            return False
    else:
        return False

    mod_entry = {
        "pending_id": pending_id,
        "action": "approved",
        "reason": "",
        "time": _now_iso(),
        "item": pending,
    }
    modlog = kb.get("moderation_log", []) or []
    modlog.insert(0, mod_entry)
    kb["moderation_log"] = modlog

    try:
        pending_list.pop(idx)
        kb["pending_reviews"] = pending_list
        save_knowledge_base(path, kb)
        return True
    except Exception as e:
        print(f"[knowledge_loader] Error approving pending review: {e}")
        return False


def reject_pending_review(
    path: str, kb: Dict[str, Any], pending_id: str, reason: str = ""
) -> bool:
    pending_list = kb.get("pending_reviews", []) or []
    idx = None
    pending = None
    for i, p in enumerate(pending_list):
        if p.get("id") == pending_id:
            idx = i
            pending = p
            break
    if idx is None or pending is None:
        return False
    modlog = kb.get("moderation_log", []) or []
    entry = {
        "pending_id": pending_id,
        "action": "rejected",
        "reason": reason or "",
        "time": _now_iso(),
        "item": pending,
    }
    modlog.insert(0, entry)
    kb["moderation_log"] = modlog
    try:
        pending_list.pop(idx)
        kb["pending_reviews"] = pending_list
        save_knowledge_base(path, kb)
        return True
    except Exception as e:
        print(f"[knowledge_loader] Error rejecting pending review: {e}")
        return False


def get_moderation_log(kb: Dict[str, Any]) -> List[Dict[str, Any]]:
    return kb.get("moderation_log", []) or []


# ---------------------- 图形化管理用：课程 / 导师 / 校内实践 ----------------------
def add_course(
    kb_path: str, kb: Dict[str, Any], major: str, course: Dict[str, Any]
) -> bool:
    try:
        kb.setdefault("courses", {})
        kb["courses"].setdefault(major, [])
        kb["courses"][major].append(course)
        save_knowledge_base(kb_path, kb)
        return True
    except Exception as e:
        print(f"[knowledge_loader] add_course failed: {e}")
        return False


def delete_course(
    kb_path: str, kb: Dict[str, Any], major: str, course_code: str
) -> bool:
    try:
        courses_by_major = kb.get("courses", {})
        if major not in courses_by_major:
            return False
        before = len(courses_by_major[major])
        courses_by_major[major] = [
            c for c in courses_by_major[major] if c.get("code") != course_code
        ]
        kb["courses"] = courses_by_major
        if len(courses_by_major[major]) != before:
            save_knowledge_base(kb_path, kb)
            return True
        return False
    except Exception as e:
        print(f"[knowledge_loader] delete_course failed: {e}")
        return False


def add_advisor(
    kb_path: str, kb: Dict[str, Any], advisor: Dict[str, Any]
) -> bool:
    try:
        kb.setdefault("advisors", [])
        advisor.setdefault("reviews", [])
        kb["advisors"].append(advisor)
        save_knowledge_base(kb_path, kb)
        return True
    except Exception as e:
        print(f"[knowledge_loader] add_advisor failed: {e}")
        return False


def delete_advisor(kb_path: str, kb: Dict[str, Any], name: str) -> bool:
    try:
        advisors = kb.get("advisors", []) or []
        before = len(advisors)
        advisors = [a for a in advisors if a.get("name") != name]
        kb["advisors"] = advisors
        if len(advisors) != before:
            save_knowledge_base(kb_path, kb)
            return True
        return False
    except Exception as e:
        print(f"[knowledge_loader] delete_advisor failed: {e}")
        return False


def add_practice(kb_path: str, kb: Dict[str, Any], practice: Dict[str, Any]) -> bool:
    """
    新增一条校内实践（供管理后台使用）。
    """
    try:
        kb.setdefault("practice", [])
        kb["practice"].append(practice)
        save_knowledge_base(kb_path, kb)
        return True
    except Exception as e:
        print(f"[knowledge_loader] add_practice failed: {e}")
        return False


def delete_practice(kb_path: str, kb: Dict[str, Any], name: str) -> bool:
    """
    删除一条校内实践（按 name 精确匹配）。
    """
    try:
        practices = kb.get("practice", []) or []
        before = len(practices)
        practices = [p for p in practices if p.get("name") != name]
        kb["practice"] = practices
        if len(practices) != before:
            save_knowledge_base(kb_path, kb)
            return True
        return False
    except Exception as e:
        print(f"[knowledge_loader] delete_practice failed: {e}")
        return False


# ---------------------- Alumni cases management ----------------------
def get_alumni_cases(kb: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get all alumni cases from knowledge base."""
    return kb.get("alumni", []) or []


def add_alumni_case(kb_path: str, kb: Dict[str, Any], case: Dict[str, Any]) -> bool:
    """
    Add a new alumni case to knowledge base.
    Expected fields: title, field, content, year, major, name (optional)
    """
    try:
        kb.setdefault("alumni", [])
        # Add an ID if not present
        if "id" not in case:
            case["id"] = str(uuid.uuid4())
        kb["alumni"].append(case)
        save_knowledge_base(kb_path, kb)
        return True
    except Exception as e:
        print(f"[knowledge_loader] add_alumni_case failed: {e}")
        return False


def update_alumni_case(kb_path: str, kb: Dict[str, Any], case_id: str, updated_case: Dict[str, Any]) -> bool:
    """
    Update an existing alumni case by ID.
    """
    try:
        alumni_list = kb.get("alumni", []) or []
        found = False
        for i, case in enumerate(alumni_list):
            if case.get("id") == case_id:
                # Preserve the ID
                updated_case["id"] = case_id
                alumni_list[i] = updated_case
                found = True
                break
        if found:
            kb["alumni"] = alumni_list
            save_knowledge_base(kb_path, kb)
            return True
        return False
    except Exception as e:
        print(f"[knowledge_loader] update_alumni_case failed: {e}")
        return False


def delete_alumni_case(kb_path: str, kb: Dict[str, Any], case_id: str) -> bool:
    """
    Delete an alumni case by ID.
    """
    try:
        alumni_list = kb.get("alumni", []) or []
        before = len(alumni_list)
        alumni_list = [c for c in alumni_list if c.get("id") != case_id]
        kb["alumni"] = alumni_list
        if len(alumni_list) != before:
            save_knowledge_base(kb_path, kb)
            return True
        return False
    except Exception as e:
        print(f"[knowledge_loader] delete_alumni_case failed: {e}")
        return False


# ---------------------- Edit functions for existing items ----------------------
def update_course(kb_path: str, kb: Dict[str, Any], major: str, course_code: str, updated_course: Dict[str, Any]) -> bool:
    """
    Update an existing course by code within a major.
    """
    try:
        courses_by_major = kb.get("courses", {})
        if major not in courses_by_major:
            return False
        found = False
        for i, course in enumerate(courses_by_major[major]):
            if course.get("code") == course_code:
                # Preserve reviews
                updated_course["reviews"] = course.get("reviews", [])
                courses_by_major[major][i] = updated_course
                found = True
                break
        if found:
            kb["courses"] = courses_by_major
            save_knowledge_base(kb_path, kb)
            return True
        return False
    except Exception as e:
        print(f"[knowledge_loader] update_course failed: {e}")
        return False


def update_advisor(kb_path: str, kb: Dict[str, Any], advisor_name: str, updated_advisor: Dict[str, Any]) -> bool:
    """
    Update an existing advisor by name.
    """
    try:
        advisors = kb.get("advisors", []) or []
        found = False
        for i, advisor in enumerate(advisors):
            if advisor.get("name") == advisor_name:
                # Preserve reviews
                updated_advisor["reviews"] = advisor.get("reviews", [])
                advisors[i] = updated_advisor
                found = True
                break
        if found:
            kb["advisors"] = advisors
            save_knowledge_base(kb_path, kb)
            return True
        return False
    except Exception as e:
        print(f"[knowledge_loader] update_advisor failed: {e}")
        return False


def update_practice(kb_path: str, kb: Dict[str, Any], practice_name: str, updated_practice: Dict[str, Any]) -> bool:
    """
    Update an existing practice resource by name.
    """
    try:
        practices = kb.get("practice", []) or []
        found = False
        for i, practice in enumerate(practices):
            if practice.get("name") == practice_name:
                practices[i] = updated_practice
                found = True
                break
        if found:
            kb["practice"] = practices
            save_knowledge_base(kb_path, kb)
            return True
        return False
    except Exception as e:
        print(f"[knowledge_loader] update_practice failed: {e}")
        return False
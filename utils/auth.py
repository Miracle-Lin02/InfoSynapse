# -*- coding: utf-8 -*-
"""
utils/auth.py - User registration and login with secure password hashing.

使用 PBKDF2-HMAC-SHA256 进行密码哈希，带随机盐和多次迭代。
支持 PostgreSQL 数据库存储或 JSON 文件存储（根据 DB_TYPE 配置）。

存储格式（data/users.json 或 PostgreSQL users 表）：
[
  {
    "username": "user1",
    "display_name": "用户1",
    "salt": "<hex>",
    "pw_hash": "<hex>",
    "role": "user",
    "created_at": "ISO timestamp"
  }
]
"""
import os
import json
import hashlib
import hmac
import binascii
import secrets
from datetime import datetime
from typing import Optional, Dict, Any, List

USERS_PATH = "data/users.json"
PBKDF2_ROUNDS = 100_000


def _get_db_store():
    """获取数据库存储实例"""
    try:
        from utils.database import get_data_store, is_using_database
        if is_using_database():
            return get_data_store()
    except ImportError:
        pass
    return None


def _ensure_data_dir():
    """确保 data 目录存在。"""
    os.makedirs("data", exist_ok=True)


def _ensure_users_file():
    """确保 users.json 存在。"""
    _ensure_data_dir()
    if not os.path.exists(USERS_PATH):
        with open(USERS_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_users() -> List[Dict[str, Any]]:
    """加载所有用户数据。"""
    # 优先从数据库加载
    db_store = _get_db_store()
    if db_store:
        try:
            return db_store.get_all_users()
        except Exception as e:
            print(f"[auth] 从数据库加载用户失败，回退到 JSON: {e}")
    
    # 从 JSON 文件加载
    _ensure_users_file()
    try:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[auth] 加载用户数据失败: {e}")
        return []


def save_users(users: List[Dict[str, Any]]):
    """保存用户数据，带备份。"""
    _ensure_users_file()
    # 备份
    if os.path.exists(USERS_PATH):
        backup_path = USERS_PATH + ".backup"
        try:
            with open(USERS_PATH, "r", encoding="utf-8") as src:
                with open(backup_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
        except Exception:
            pass
    # 写入（原子操作）
    tmp_path = USERS_PATH + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, USERS_PATH)
    except Exception as e:
        print(f"[auth] 保存用户数据失败: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _hash_password(password: str, salt: bytes) -> str:
    """使用 PBKDF2-HMAC-SHA256 计算密码哈希。"""
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return binascii.hexlify(dk).decode("ascii")


def _gen_salt() -> bytes:
    """生成随机盐（16字节）。"""
    return secrets.token_bytes(16)


def find_user(username: str) -> Optional[Dict[str, Any]]:
    """通过用户名查找用户。"""
    # 优先从数据库查找
    db_store = _get_db_store()
    if db_store:
        try:
            user = db_store.get_user(username)
            if user:
                return user
        except Exception as e:
            print(f"[auth] 从数据库查找用户失败，回退到 JSON: {e}")
    
    # 从 JSON 文件查找
    users = load_users()
    for u in users:
        if u.get("username") == username:
            return u
    return None


def register_user(username: str, password: str, display_name: str = "", role: str = "user", admin_pass: str = "") -> Dict[str, Any]:
    """
    注册新用户。
    
    参数：
        username: 用户名（必须唯一）
        password: 密码（必须非空）
        display_name: 显示名（默认为用户名）
        role: "user" 或 "admin"
        admin_pass: 管理员口令（若 role=='admin' 则需提供）
    
    返回：
        {"success": bool, "msg": str}
    """
    # 基础验证
    if not username or not username.strip():
        return {"success": False, "msg": "用户名不能为空"}
    if not password or not password.strip():
        return {"success": False, "msg": "密码不能为空"}
    
    username = username.strip()
    password = password.strip()
    
    # 检查用户名是否已存在
    if find_user(username):
        return {"success": False, "msg": "用户名已存在"}
    
    # 若注册为管理员，需验证管理员口令
    env_admin = os.getenv("ADMIN_PASS", "") or ""
    if role == "admin":
        if not admin_pass or admin_pass != env_admin:
            return {"success": False, "msg": "管理员口令不正确或未提供"}
    
    # 生成盐和哈希
    salt = _gen_salt()
    pw_hash = _hash_password(password, salt)
    
    # 创建用户记录
    new_user = {
        "username": username,
        "display_name": display_name or username,
        "salt": binascii.hexlify(salt).decode("ascii"),
        "pw_hash": pw_hash,
        "role": role,
        "created_at": datetime.utcnow().isoformat(timespec="seconds")
    }
    
    # 优先保存到数据库
    db_store = _get_db_store()
    if db_store:
        try:
            if db_store.add_user(new_user):
                print(f"[auth] 用户注册成功（数据库）: {username} (role: {role})")
                return {"success": True, "msg": "注册成功，请登录"}
            else:
                return {"success": False, "msg": "注册失败，请重试"}
        except Exception as e:
            print(f"[auth] 保存用户到数据库失败: {e}")
    
    # 回退到 JSON 文件
    users = load_users()
    users.append(new_user)
    save_users(users)
    
    print(f"[auth] 用户注册成功: {username} (role: {role})")
    return {"success": True, "msg": "注册成功，请登录"}


def verify_password(username: str, password: str) -> Dict[str, Any]:
    """
    验证用户登录。
    
    返回：
        {"success": bool, "msg": str, "user": optional user info dict}
    """
    if not username or not password:
        return {"success": False, "msg": "用户名或密码不能为空"}
    
    user = find_user(username.strip())
    if not user:
        return {"success": False, "msg": "用户不存在"}
    
    # 提取盐和哈希
    try:
        salt_hex = user.get("salt", "")
        expected_hash = user.get("pw_hash", "")
        
        if not salt_hex or not expected_hash:
            return {"success": False, "msg": "用户数据损坏"}
        
        salt = binascii.unhexlify(salt_hex)
        got_hash = _hash_password(password.strip(), salt)
        
        # 使用恒时比较防止时序攻击
        if hmac.compare_digest(got_hash, expected_hash):
            user_info = {
                "username": user.get("username"),
                "display_name": user.get("display_name"),
                "role": user.get("role", "user")
            }
            print(f"[auth] 用户登录成功: {username}")
            return {"success": True, "msg": "登录成功", "user": user_info}
        else:
            print(f"[auth] 用户登录失败（密码错误）: {username}")
            return {"success": False, "msg": "密码错误"}
    
    except Exception as e:
        print(f"[auth] 密码验证异常: {e}")
        return {"success": False, "msg": "验证过程出错"}


def list_users() -> List[Dict[str, Any]]:
    """列出所有用户（不包含密码哈希）。"""
    users = load_users()
    return [
        {
            "username": u.get("username"),
            "display_name": u.get("display_name"),
            "role": u.get("role", "user"),
            "created_at": u.get("created_at")
        }
        for u in users
    ]
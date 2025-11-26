#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/migrate_to_postgresql.py

将现有 JSON 数据迁移到 PostgreSQL 数据库。

使用方法:
1. 确保已安装 psycopg2: pip install psycopg2-binary
2. 设置环境变量:
   - DATABASE_URL: PostgreSQL 连接字符串
   - 或分别设置: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
3. 运行: python scripts/migrate_to_postgresql.py

示例:
    export DATABASE_URL="postgresql://user:password@localhost:5432/infosynapse"
    python scripts/migrate_to_postgresql.py
"""

import os
import sys
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import PostgreSQLStore, PSYCOPG2_AVAILABLE


def load_json_data(json_path: str) -> dict:
    """加载 JSON 数据文件"""
    if not os.path.exists(json_path):
        print(f"[迁移] JSON 文件不存在: {json_path}")
        return {}
    
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_json_list(json_path: str) -> list:
    """加载 JSON 列表文件"""
    if not os.path.exists(json_path):
        print(f"[迁移] JSON 文件不存在: {json_path}")
        return []
    
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def migrate_courses(store: PostgreSQLStore, courses_data: dict):
    """迁移课程数据"""
    total = 0
    success = 0
    
    for major, courses in courses_data.items():
        for course in courses:
            total += 1
            if store.add_course(major, course):
                success += 1
            else:
                print(f"  [跳过] 课程已存在或添加失败: {course.get('code')} - {course.get('name')}")
    
    print(f"[迁移] 课程: {success}/{total} 条成功")


def migrate_advisors(store: PostgreSQLStore, advisors_data: list):
    """迁移导师数据"""
    total = len(advisors_data)
    success = 0
    
    for advisor in advisors_data:
        if store.add_advisor(advisor):
            success += 1
        else:
            print(f"  [跳过] 导师已存在或添加失败: {advisor.get('name')}")
    
    print(f"[迁移] 导师: {success}/{total} 条成功")


def migrate_practices(store: PostgreSQLStore, practices_data: list):
    """迁移校内实践数据"""
    total = len(practices_data)
    success = 0
    
    for practice in practices_data:
        if store.add_practice(practice):
            success += 1
        else:
            print(f"  [跳过] 校内实践已存在或添加失败: {practice.get('name')}")
    
    print(f"[迁移] 校内实践: {success}/{total} 条成功")


def migrate_alumni(store: PostgreSQLStore, alumni_data: list):
    """迁移校友案例数据"""
    total = len(alumni_data)
    success = 0
    
    for alumni in alumni_data:
        if store.add_alumni(alumni):
            success += 1
        else:
            print(f"  [跳过] 校友案例已存在或添加失败: {alumni.get('title')}")
    
    print(f"[迁移] 校友案例: {success}/{total} 条成功")


def migrate_jds(store: PostgreSQLStore, jds_data: list):
    """迁移职位描述数据"""
    total = len(jds_data)
    success = 0
    
    for jd in jds_data:
        if store.add_jd(jd):
            success += 1
        else:
            print(f"  [跳过] 职位描述添加失败: {jd.get('company')} - {jd.get('position')}")
    
    print(f"[迁移] 职位描述: {success}/{total} 条成功")


def migrate_users(store: PostgreSQLStore, users_data: list):
    """迁移用户数据"""
    total = len(users_data)
    success = 0
    
    for user in users_data:
        if store.add_user(user):
            success += 1
        else:
            print(f"  [跳过] 用户已存在或添加失败: {user.get('username')}")
    
    print(f"[迁移] 用户: {success}/{total} 条成功")


def migrate_user_profiles(store: PostgreSQLStore, profiles_data: dict):
    """迁移用户档案数据"""
    total = len(profiles_data)
    success = 0
    
    for username, profile in profiles_data.items():
        if store.save_user_profile(username, profile):
            success += 1
        else:
            print(f"  [跳过] 用户档案保存失败: {username}")
    
    print(f"[迁移] 用户档案: {success}/{total} 条成功")


def migrate_community(store: PostgreSQLStore, community_data: dict):
    """迁移社区帖子数据"""
    threads = community_data.get("threads", [])
    total = len(threads)
    success = 0
    
    for thread in threads:
        if store.create_thread(thread):
            success += 1
        else:
            print(f"  [跳过] 帖子已存在或添加失败: {thread.get('title')}")
    
    print(f"[迁移] 社区帖子: {success}/{total} 条成功")


def migrate_career_feedback(store: PostgreSQLStore, feedback_data: dict):
    """迁移职业反馈数据"""
    total = len(feedback_data)
    success = 0
    
    for career_name, counts in feedback_data.items():
        if store.set_career_feedback(career_name, counts.get('like', 0), counts.get('dislike', 0)):
            success += 1
        else:
            print(f"  [跳过] 职业反馈保存失败: {career_name}")
    
    print(f"[迁移] 职业反馈: {success}/{total} 条成功")


def main():
    print("=" * 60)
    print("InfoSynapse 数据迁移工具 - JSON → PostgreSQL")
    print("=" * 60)
    
    # 检查 psycopg2 是否可用
    if not PSYCOPG2_AVAILABLE:
        print("\n[错误] psycopg2 未安装!")
        print("请运行: pip install psycopg2-binary")
        sys.exit(1)
    
    # 检查环境变量
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "infosynapse")
        db_user = os.getenv("DB_USER", "postgres")
        print(f"\n[配置] 数据库连接: {db_user}@{db_host}:{db_port}/{db_name}")
    else:
        # 隐藏密码
        safe_url = database_url.split("@")[-1] if "@" in database_url else database_url
        print(f"\n[配置] 数据库连接: ...@{safe_url}")
    
    # 数据文件路径
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data"
    )
    
    json_path = os.path.join(data_dir, "hdu_knowledge_base.json")
    users_path = os.path.join(data_dir, "users.json")
    profiles_path = os.path.join(data_dir, "user_profiles.json")
    community_path = os.path.join(data_dir, "community.json")
    career_feedback_path = os.path.join(data_dir, "career_feedback.json")
    
    print(f"[配置] 知识库 JSON 文件: {json_path}")
    print(f"[配置] 用户 JSON 文件: {users_path}")
    print(f"[配置] 用户档案 JSON 文件: {profiles_path}")
    print(f"[配置] 社区帖子 JSON 文件: {community_path}")
    print(f"[配置] 职业反馈 JSON 文件: {career_feedback_path}")
    
    # 加载 JSON 数据
    print("\n[步骤 1/10] 加载知识库 JSON 数据...")
    kb_data = load_json_data(json_path)
    if not kb_data:
        print("[警告] 知识库 JSON 数据为空或不存在")
        kb_data = {}
    
    print(f"  - 课程专业数: {len(kb_data.get('courses', {}))}")
    print(f"  - 导师数: {len(kb_data.get('advisors', []))}")
    print(f"  - 校内实践数: {len(kb_data.get('practice', []))}")
    print(f"  - 校友案例数: {len(kb_data.get('alumni', []))}")
    print(f"  - 职位描述数: {len(kb_data.get('jds', []))}")
    
    print("\n[步骤 2/10] 加载用户数据...")
    users_data = load_json_list(users_path)
    profiles_data = load_json_data(profiles_path)
    print(f"  - 用户数: {len(users_data)}")
    print(f"  - 用户档案数: {len(profiles_data)}")
    
    print("\n[步骤 3/10] 加载社区和反馈数据...")
    community_data = load_json_data(community_path)
    career_feedback_data = load_json_data(career_feedback_path)
    print(f"  - 社区帖子数: {len(community_data.get('threads', []))}")
    print(f"  - 职业反馈数: {len(career_feedback_data)}")
    
    # 初始化数据库连接
    print("\n[步骤 4/10] 连接 PostgreSQL 并初始化表结构...")
    try:
        store = PostgreSQLStore()
        print("  - 数据库连接成功")
        print("  - 表结构初始化完成")
    except Exception as e:
        print(f"[错误] 数据库连接失败: {e}")
        sys.exit(1)
    
    # 迁移数据
    print("\n[步骤 5/10] 迁移课程数据...")
    migrate_courses(store, kb_data.get('courses', {}))
    
    print("\n[步骤 6/10] 迁移导师数据...")
    migrate_advisors(store, kb_data.get('advisors', []))
    
    print("\n[步骤 7/10] 迁移校内实践数据...")
    migrate_practices(store, kb_data.get('practice', []))
    
    print("\n[步骤 8/10] 迁移校友案例和职位描述...")
    migrate_alumni(store, kb_data.get('alumni', []))
    migrate_jds(store, kb_data.get('jds', []))
    
    print("\n[步骤 9/10] 迁移用户数据...")
    if users_data:
        migrate_users(store, users_data)
    else:
        print("  [跳过] 没有用户数据需要迁移")
    
    if profiles_data:
        migrate_user_profiles(store, profiles_data)
    else:
        print("  [跳过] 没有用户档案需要迁移")
    
    print("\n[步骤 10/10] 迁移社区和反馈数据...")
    if community_data and community_data.get('threads'):
        migrate_community(store, community_data)
    else:
        print("  [跳过] 没有社区帖子需要迁移")
    
    if career_feedback_data:
        migrate_career_feedback(store, career_feedback_data)
    else:
        print("  [跳过] 没有职业反馈需要迁移")
    
    # 关闭连接
    store.close()
    
    print("\n" + "=" * 60)
    print("迁移完成!")
    print("=" * 60)
    print("\n后续步骤:")
    print("1. 设置环境变量启用数据库模式:")
    print('   export DB_TYPE="postgresql"')
    print("\n2. 重启应用:")
    print("   streamlit run infosynapse.py")
    print("\n3. 验证数据是否正确显示")
    print("\n已迁移的数据类型:")
    print("  - 知识库（课程、导师、实践、校友案例、JD）")
    print("  - 用户账户和档案")
    print("  - 社区帖子和回复")
    print("  - 职业反馈（点赞/点踩）")


if __name__ == "__main__":
    main()

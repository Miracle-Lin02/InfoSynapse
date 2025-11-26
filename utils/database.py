# -*- coding: utf-8 -*-
"""
utils/database.py

数据库抽象层，支持 PostgreSQL 和 JSON 文件存储的切换。
通过环境变量或 Streamlit secrets 中的 DB_TYPE 控制使用哪种存储方式：
- DB_TYPE=postgresql: 使用 PostgreSQL 数据库
- DB_TYPE=json (默认): 使用 JSON 文件存储

PostgreSQL 配置（按优先级）：
1. 环境变量 DATABASE_URL
2. Streamlit secrets 中的 DATABASE_URL
3. 分别配置: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""

import os
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional

# 尝试导入 Streamlit secrets
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

# 尝试导入 psycopg2，如果不存在则标记为不可用
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


def _get_secret(key: str, default: str = "") -> str:
    """
    从环境变量或 Streamlit secrets 中获取配置值。
    优先级: 环境变量 > Streamlit secrets > 默认值
    """
    # 首先检查环境变量
    env_value = os.getenv(key)
    if env_value:
        return env_value
    
    # 然后检查 Streamlit secrets
    if STREAMLIT_AVAILABLE:
        try:
            if hasattr(st, 'secrets') and key in st.secrets:
                return str(st.secrets[key])
        except Exception:
            pass
    
    return default


def _now_iso() -> str:
    """返回当前时间的 ISO 格式字符串"""
    return datetime.now().isoformat(timespec="seconds")


class DataStore(ABC):
    """数据存储抽象基类"""
    
    @abstractmethod
    def get_courses(self, major: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """获取课程数据，如果指定 major 则只返回该专业的课程"""
        pass
    
    @abstractmethod
    def add_course(self, major: str, course: Dict[str, Any]) -> bool:
        """添加课程"""
        pass
    
    @abstractmethod
    def update_course(self, major: str, course_code: str, course: Dict[str, Any]) -> bool:
        """更新课程"""
        pass
    
    @abstractmethod
    def delete_course(self, major: str, course_code: str) -> bool:
        """删除课程"""
        pass
    
    @abstractmethod
    def get_advisors(self, research_area: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取导师数据"""
        pass
    
    @abstractmethod
    def add_advisor(self, advisor: Dict[str, Any]) -> bool:
        """添加导师"""
        pass
    
    @abstractmethod
    def update_advisor(self, name: str, advisor: Dict[str, Any]) -> bool:
        """更新导师"""
        pass
    
    @abstractmethod
    def delete_advisor(self, name: str) -> bool:
        """删除导师"""
        pass
    
    @abstractmethod
    def get_practices(self) -> List[Dict[str, Any]]:
        """获取校内实践数据"""
        pass
    
    @abstractmethod
    def add_practice(self, practice: Dict[str, Any]) -> bool:
        """添加校内实践"""
        pass
    
    @abstractmethod
    def delete_practice(self, name: str) -> bool:
        """删除校内实践"""
        pass
    
    @abstractmethod
    def get_alumni(self) -> List[Dict[str, Any]]:
        """获取校友案例"""
        pass
    
    @abstractmethod
    def add_alumni(self, alumni: Dict[str, Any]) -> bool:
        """添加校友案例"""
        pass
    
    @abstractmethod
    def delete_alumni(self, case_id: str) -> bool:
        """删除校友案例"""
        pass
    
    @abstractmethod
    def get_all_data(self) -> Dict[str, Any]:
        """获取所有数据（兼容现有 knowledge_base 格式）"""
        pass


class PostgreSQLStore(DataStore):
    """PostgreSQL 数据存储实现"""
    
    def __init__(self, connection_string: Optional[str] = None):
        if not PSYCOPG2_AVAILABLE:
            raise ImportError("psycopg2 未安装。请运行: pip install psycopg2-binary")
        
        self.connection_string = connection_string or self._build_connection_string()
        self.conn = None
        self._connect()
        self._init_tables()
    
    def _build_connection_string(self) -> str:
        """从环境变量或 Streamlit secrets 构建连接字符串"""
        # 优先使用 DATABASE_URL
        database_url = _get_secret("DATABASE_URL")
        if database_url:
            return database_url
        
        # 否则从单独的配置项构建
        host = _get_secret("DB_HOST", "localhost")
        port = _get_secret("DB_PORT", "5432")
        dbname = _get_secret("DB_NAME", "infosynapse")
        user = _get_secret("DB_USER", "postgres")
        password = _get_secret("DB_PASSWORD", "")
        
        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    
    def _connect(self):
        """建立数据库连接"""
        try:
            # 添加连接超时和 keepalive 参数以提高稳定性
            self.conn = psycopg2.connect(
                self.connection_string,
                connect_timeout=10,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5
            )
            self.conn.autocommit = False
        except Exception as e:
            print(f"[database] PostgreSQL 连接失败: {e}")
            raise
    
    def _ensure_connection(self):
        """确保数据库连接有效，自动重连"""
        try:
            if self.conn is None or self.conn.closed:
                self._connect()
                return
            
            # 测试连接是否仍然有效
            try:
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")
            except Exception:
                # 连接已断开，尝试重连
                try:
                    self.conn.close()
                except Exception:
                    pass
                self._connect()
        except Exception as e:
            print(f"[database] 重新连接失败: {e}")
            raise
    
    def _init_tables(self):
        """初始化数据库表结构"""
        self._ensure_connection()
        
        create_tables_sql = """
        -- 课程表
        CREATE TABLE IF NOT EXISTS courses (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            major VARCHAR(100) NOT NULL,
            level VARCHAR(50),
            prereq TEXT,
            link TEXT,
            outline TEXT,
            ideological BOOLEAN DEFAULT FALSE,
            reviews JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(code, major)
        );
        
        -- 导师表
        CREATE TABLE IF NOT EXISTS advisors (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            department VARCHAR(255),
            research TEXT,
            homepage TEXT,
            national_projects BOOLEAN DEFAULT FALSE,
            national_projects_info TEXT,
            reviews JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 校内实践表
        CREATE TABLE IF NOT EXISTS practices (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            type VARCHAR(100),
            description TEXT,
            link TEXT,
            social_value BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 校友案例表
        CREATE TABLE IF NOT EXISTS alumni (
            id VARCHAR(50) PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            field VARCHAR(100),
            name VARCHAR(255),
            year VARCHAR(50),
            major VARCHAR(100),
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 职位描述表
        CREATE TABLE IF NOT EXISTS jds (
            id SERIAL PRIMARY KEY,
            company VARCHAR(255),
            position VARCHAR(255),
            jd TEXT,
            skills JSONB DEFAULT '[]'::jsonb,
            link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 待审核评价表
        CREATE TABLE IF NOT EXISTS pending_reviews (
            id VARCHAR(50) PRIMARY KEY,
            target_type VARCHAR(50) NOT NULL,
            target_id VARCHAR(255) NOT NULL,
            reviewer VARCHAR(255),
            rating INTEGER,
            comment TEXT,
            status VARCHAR(50) DEFAULT 'pending',
            submitted_via VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 审核日志表
        CREATE TABLE IF NOT EXISTS moderation_log (
            id SERIAL PRIMARY KEY,
            pending_id VARCHAR(50),
            action VARCHAR(50),
            reason TEXT,
            admin_user VARCHAR(255),
            item JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 用户表
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE,
            display_name VARCHAR(255),
            salt VARCHAR(64) NOT NULL,
            pw_hash VARCHAR(128) NOT NULL,
            role VARCHAR(50) DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 用户档案表
        CREATE TABLE IF NOT EXISTS user_profiles (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE REFERENCES users(username) ON DELETE CASCADE,
            bio TEXT,
            major VARCHAR(100),
            stage VARCHAR(50),
            target_career VARCHAR(255),
            target_direction VARCHAR(255),
            interests JSONB DEFAULT '[]'::jsonb,
            skills JSONB DEFAULT '[]'::jsonb,
            starred_repos JSONB DEFAULT '[]'::jsonb,
            finished_repos JSONB DEFAULT '[]'::jsonb,
            learning_plan JSONB DEFAULT '[]'::jsonb,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 社区帖子表（主题）
        CREATE TABLE IF NOT EXISTS community_threads (
            id VARCHAR(50) PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            created_by VARCHAR(255),
            created_by_name VARCHAR(255),
            category VARCHAR(100) DEFAULT '其他',
            likes JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 社区帖子回复表
        CREATE TABLE IF NOT EXISTS community_posts (
            id VARCHAR(50) PRIMARY KEY,
            thread_id VARCHAR(50) REFERENCES community_threads(id) ON DELETE CASCADE,
            author VARCHAR(255),
            author_name VARCHAR(255),
            content TEXT,
            likes JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 用户通知表
        CREATE TABLE IF NOT EXISTS notifications (
            id VARCHAR(50) PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            notification_type VARCHAR(50),
            title VARCHAR(500),
            message TEXT,
            link TEXT,
            metadata JSONB DEFAULT '{}'::jsonb,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 用户活动表（浏览历史和收藏）
        CREATE TABLE IF NOT EXISTS user_activity (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            activity_type VARCHAR(50) NOT NULL,
            item_type VARCHAR(50),
            item_id VARCHAR(255),
            item_name VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username, activity_type, item_type, item_id)
        );
        
        -- AI 对话历史表
        CREATE TABLE IF NOT EXISTS ai_conversations (
            id VARCHAR(50) PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            conversation_type VARCHAR(50),
            title VARCHAR(500),
            messages JSONB DEFAULT '[]'::jsonb,
            context JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 用户反馈表（职业反馈）
        CREATE TABLE IF NOT EXISTS user_feedback (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            feedback_type VARCHAR(50) NOT NULL,
            target_name VARCHAR(255),
            rating INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username, feedback_type, target_name)
        );
        
        -- 职业反馈聚合表
        CREATE TABLE IF NOT EXISTS career_feedback (
            career_name VARCHAR(255) PRIMARY KEY,
            like_count INTEGER DEFAULT 0,
            dislike_count INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 智能提醒表
        CREATE TABLE IF NOT EXISTS user_reminders (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            reminder_type VARCHAR(50),
            message TEXT,
            is_dismissed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            dismissed_at TIMESTAMP
        );
        
        -- 提醒配置表
        CREATE TABLE IF NOT EXISTS reminder_config (
            username VARCHAR(255) PRIMARY KEY,
            frequency VARCHAR(50) DEFAULT 'weekly',
            enabled_types JSONB DEFAULT '["course", "practice", "career"]'::jsonb,
            last_check TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 创建索引
        CREATE INDEX IF NOT EXISTS idx_courses_major ON courses(major);
        CREATE INDEX IF NOT EXISTS idx_advisors_department ON advisors(department);
        CREATE INDEX IF NOT EXISTS idx_practices_type ON practices(type);
        CREATE INDEX IF NOT EXISTS idx_alumni_field ON alumni(field);
        CREATE INDEX IF NOT EXISTS idx_pending_reviews_status ON pending_reviews(status);
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_user_profiles_username ON user_profiles(username);
        CREATE INDEX IF NOT EXISTS idx_community_threads_category ON community_threads(category);
        CREATE INDEX IF NOT EXISTS idx_community_posts_thread_id ON community_posts(thread_id);
        CREATE INDEX IF NOT EXISTS idx_notifications_username ON notifications(username);
        CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read);
        CREATE INDEX IF NOT EXISTS idx_user_activity_username ON user_activity(username);
        CREATE INDEX IF NOT EXISTS idx_ai_conversations_username ON ai_conversations(username);
        CREATE INDEX IF NOT EXISTS idx_user_feedback_username ON user_feedback(username);
        CREATE INDEX IF NOT EXISTS idx_user_reminders_username ON user_reminders(username);
        """
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(create_tables_sql)
            self.conn.commit()
            print("[database] PostgreSQL 表初始化成功")
        except Exception as e:
            self.conn.rollback()
            print(f"[database] 表初始化失败: {e}")
            raise
    
    def get_courses(self, major: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """获取课程数据"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                if major:
                    cur.execute("SELECT * FROM courses WHERE major = %s ORDER BY code", (major,))
                else:
                    cur.execute("SELECT * FROM courses ORDER BY major, code")
                
                rows = cur.fetchall()
                
                # 按专业分组
                courses_by_major = {}
                for row in rows:
                    m = row['major']
                    if m not in courses_by_major:
                        courses_by_major[m] = []
                    course_dict = {
                        'code': row['code'],
                        'name': row['name'],
                        'level': row['level'],
                        'prereq': row['prereq'],
                        'link': row['link'],
                        'outline': row['outline'],
                        'ideological': row['ideological'],
                        'reviews': row['reviews'] or []
                    }
                    courses_by_major[m].append(course_dict)
                
                return courses_by_major
        except Exception as e:
            print(f"[database] get_courses 失败: {e}")
            return {}
    
    def add_course(self, major: str, course: Dict[str, Any]) -> bool:
        """添加课程"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO courses (code, name, major, level, prereq, link, outline, ideological, reviews)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (code, major) DO NOTHING
                """, (
                    course.get('code'),
                    course.get('name'),
                    major,
                    course.get('level'),
                    course.get('prereq'),
                    course.get('link'),
                    course.get('outline'),
                    course.get('ideological', False),
                    json.dumps(course.get('reviews', []))
                ))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] add_course 失败: {e}")
            return False
    
    def update_course(self, major: str, course_code: str, course: Dict[str, Any]) -> bool:
        """更新课程"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE courses SET
                        name = %s,
                        level = %s,
                        prereq = %s,
                        link = %s,
                        outline = %s,
                        ideological = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE code = %s AND major = %s
                """, (
                    course.get('name'),
                    course.get('level'),
                    course.get('prereq'),
                    course.get('link'),
                    course.get('outline'),
                    course.get('ideological', False),
                    course_code,
                    major
                ))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] update_course 失败: {e}")
            return False
    
    def delete_course(self, major: str, course_code: str) -> bool:
        """删除课程"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM courses WHERE code = %s AND major = %s", (course_code, major))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] delete_course 失败: {e}")
            return False
    
    def get_advisors(self, research_area: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取导师数据"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                if research_area:
                    search = f"%{research_area.lower()}%"
                    cur.execute("""
                        SELECT * FROM advisors 
                        WHERE LOWER(research) LIKE %s 
                           OR LOWER(department) LIKE %s 
                           OR LOWER(name) LIKE %s
                        ORDER BY name
                    """, (search, search, search))
                else:
                    cur.execute("SELECT * FROM advisors ORDER BY name")
                
                rows = cur.fetchall()
                return [
                    {
                        'name': row['name'],
                        'department': row['department'],
                        'research': row['research'],
                        'homepage': row['homepage'],
                        'national_projects': row['national_projects'],
                        'national_projects_info': row['national_projects_info'],
                        'reviews': row['reviews'] or []
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"[database] get_advisors 失败: {e}")
            return []
    
    def add_advisor(self, advisor: Dict[str, Any]) -> bool:
        """添加导师"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO advisors (name, department, research, homepage, national_projects, national_projects_info, reviews)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                """, (
                    advisor.get('name'),
                    advisor.get('department'),
                    advisor.get('research'),
                    advisor.get('homepage'),
                    advisor.get('national_projects', False),
                    advisor.get('national_projects_info'),
                    json.dumps(advisor.get('reviews', []))
                ))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] add_advisor 失败: {e}")
            return False
    
    def update_advisor(self, name: str, advisor: Dict[str, Any]) -> bool:
        """更新导师"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE advisors SET
                        department = %s,
                        research = %s,
                        homepage = %s,
                        national_projects = %s,
                        national_projects_info = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE name = %s
                """, (
                    advisor.get('department'),
                    advisor.get('research'),
                    advisor.get('homepage'),
                    advisor.get('national_projects', False),
                    advisor.get('national_projects_info'),
                    name
                ))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] update_advisor 失败: {e}")
            return False
    
    def delete_advisor(self, name: str) -> bool:
        """删除导师"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM advisors WHERE name = %s", (name,))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] delete_advisor 失败: {e}")
            return False
    
    def get_practices(self) -> List[Dict[str, Any]]:
        """获取校内实践数据"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM practices ORDER BY name")
                rows = cur.fetchall()
                return [
                    {
                        'name': row['name'],
                        'type': row['type'],
                        'desc': row['description'],
                        'link': row['link'],
                        'social_value': row['social_value']
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"[database] get_practices 失败: {e}")
            return []
    
    def add_practice(self, practice: Dict[str, Any]) -> bool:
        """添加校内实践"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO practices (name, type, description, link, social_value)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                """, (
                    practice.get('name'),
                    practice.get('type'),
                    practice.get('desc'),
                    practice.get('link'),
                    practice.get('social_value', False)
                ))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] add_practice 失败: {e}")
            return False
    
    def delete_practice(self, name: str) -> bool:
        """删除校内实践"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM practices WHERE name = %s", (name,))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] delete_practice 失败: {e}")
            return False
    
    def update_practice(self, name: str, practice: Dict[str, Any]) -> bool:
        """更新校内实践"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE practices SET
                        name = %s,
                        type = %s,
                        description = %s,
                        link = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE name = %s
                """, (
                    practice.get('name'),
                    practice.get('type'),
                    practice.get('desc'),
                    practice.get('link'),
                    name
                ))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] update_practice 失败: {e}")
            return False
    
    def get_alumni(self) -> List[Dict[str, Any]]:
        """获取校友案例"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM alumni ORDER BY created_at DESC")
                rows = cur.fetchall()
                return [
                    {
                        'id': row['id'],
                        'title': row['title'],
                        'field': row['field'],
                        'name': row['name'],
                        'year': row['year'],
                        'major': row['major'],
                        'content': row['content']
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"[database] get_alumni 失败: {e}")
            return []
    
    def add_alumni(self, alumni: Dict[str, Any]) -> bool:
        """添加校友案例"""
        self._ensure_connection()
        
        alumni_id = alumni.get('id') or str(uuid.uuid4())
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO alumni (id, title, field, name, year, major, content)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (
                    alumni_id,
                    alumni.get('title'),
                    alumni.get('field'),
                    alumni.get('name'),
                    alumni.get('year'),
                    alumni.get('major'),
                    alumni.get('content')
                ))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] add_alumni 失败: {e}")
            return False
    
    def delete_alumni(self, case_id: str) -> bool:
        """删除校友案例"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM alumni WHERE id = %s", (case_id,))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] delete_alumni 失败: {e}")
            return False
    
    def update_alumni(self, case_id: str, alumni: Dict[str, Any]) -> bool:
        """更新校友案例"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE alumni SET
                        title = %s,
                        field = %s,
                        name = %s,
                        year = %s,
                        major = %s,
                        content = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (
                    alumni.get('title'),
                    alumni.get('field'),
                    alumni.get('name'),
                    alumni.get('year'),
                    alumni.get('major'),
                    alumni.get('content'),
                    case_id
                ))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] update_alumni 失败: {e}")
            return False
    
    def add_jd(self, jd: Dict[str, Any]) -> bool:
        """添加职位描述"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO jds (company, position, jd, skills, link)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    jd.get('company'),
                    jd.get('position'),
                    jd.get('jd'),
                    json.dumps(jd.get('skills', [])),
                    jd.get('link')
                ))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] add_jd 失败: {e}")
            return False
    
    def update_jd(self, company: str, position: str, jd: Dict[str, Any]) -> bool:
        """更新职位描述"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE jds SET
                        company = %s,
                        position = %s,
                        jd = %s,
                        skills = %s,
                        link = %s
                    WHERE company = %s AND position = %s
                """, (
                    jd.get('company'),
                    jd.get('position'),
                    jd.get('jd'),
                    json.dumps(jd.get('skills', [])),
                    jd.get('link'),
                    company,
                    position
                ))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] update_jd 失败: {e}")
            return False
    
    def delete_jd(self, company: str, position: str) -> bool:
        """删除职位描述"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM jds WHERE company = %s AND position = %s", (company, position))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] delete_jd 失败: {e}")
            return False
    
    def get_all_data(self) -> Dict[str, Any]:
        """获取所有数据（兼容现有 knowledge_base 格式）"""
        return {
            'courses': self.get_courses(),
            'advisors': self.get_advisors(),
            'practice': self.get_practices(),
            'alumni': self.get_alumni(),
            'jds': self._get_jds(),
            'templates': {},
            'pending_reviews': self._get_pending_reviews(),
            'moderation_log': self._get_moderation_log()
        }
    
    def _get_jds(self) -> List[Dict[str, Any]]:
        """获取职位描述"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM jds ORDER BY id")
                rows = cur.fetchall()
                return [
                    {
                        'company': row['company'],
                        'position': row['position'],
                        'jd': row['jd'],
                        'skills': row['skills'] or [],
                        'link': row['link']
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"[database] _get_jds 失败: {e}")
            return []
    
    def _get_pending_reviews(self) -> List[Dict[str, Any]]:
        """获取待审核评价"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM pending_reviews WHERE status = 'pending' ORDER BY created_at DESC")
                rows = cur.fetchall()
                return [
                    {
                        'id': row['id'],
                        'target_type': row['target_type'],
                        'target_id': row['target_id'],
                        'reviewer': row['reviewer'],
                        'rating': row['rating'],
                        'comment': row['comment'],
                        'time': row['created_at'].isoformat() if row['created_at'] else None,
                        'status': row['status'],
                        'submitted_via': row['submitted_via']
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"[database] _get_pending_reviews 失败: {e}")
            return []
    
    def _get_moderation_log(self) -> List[Dict[str, Any]]:
        """获取审核日志"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM moderation_log ORDER BY created_at DESC LIMIT 100")
                rows = cur.fetchall()
                return [
                    {
                        'pending_id': row['pending_id'],
                        'action': row['action'],
                        'reason': row['reason'],
                        'time': row['created_at'].isoformat() if row['created_at'] else None,
                        'item': row['item'],
                        'admin_user': row['admin_user']
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"[database] _get_moderation_log 失败: {e}")
            return []
    
    # ========== 用户管理方法 ==========
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """获取单个用户"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                row = cur.fetchone()
                if row:
                    return {
                        'username': row['username'],
                        'display_name': row['display_name'],
                        'salt': row['salt'],
                        'pw_hash': row['pw_hash'],
                        'role': row['role'],
                        'created_at': row['created_at'].isoformat() if row['created_at'] else None
                    }
                return None
        except Exception as e:
            print(f"[database] get_user 失败: {e}")
            return None
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """获取所有用户"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users ORDER BY created_at DESC")
                rows = cur.fetchall()
                return [
                    {
                        'username': row['username'],
                        'display_name': row['display_name'],
                        'salt': row['salt'],
                        'pw_hash': row['pw_hash'],
                        'role': row['role'],
                        'created_at': row['created_at'].isoformat() if row['created_at'] else None
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"[database] get_all_users 失败: {e}")
            return []
    
    def add_user(self, user: Dict[str, Any]) -> bool:
        """添加用户"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (username, display_name, salt, pw_hash, role)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                """, (
                    user.get('username'),
                    user.get('display_name'),
                    user.get('salt'),
                    user.get('pw_hash'),
                    user.get('role', 'user')
                ))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] add_user 失败: {e}")
            return False
    
    def update_user(self, username: str, user: Dict[str, Any]) -> bool:
        """更新用户"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE users SET
                        display_name = %s,
                        salt = %s,
                        pw_hash = %s,
                        role = %s
                    WHERE username = %s
                """, (
                    user.get('display_name'),
                    user.get('salt'),
                    user.get('pw_hash'),
                    user.get('role', 'user'),
                    username
                ))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] update_user 失败: {e}")
            return False
    
    def delete_user(self, username: str) -> bool:
        """删除用户"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM users WHERE username = %s", (username,))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] delete_user 失败: {e}")
            return False
    
    # ========== 用户档案方法 ==========
    
    def get_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """获取用户档案"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM user_profiles WHERE username = %s", (username,))
                row = cur.fetchone()
                if row:
                    return {
                        'username': row['username'],
                        'bio': row['bio'] or '',
                        'major': row['major'] or '',
                        'stage': row['stage'] or '',
                        'target_career': row['target_career'] or '',
                        'target_direction': row['target_direction'] or '',
                        'interests': row['interests'] or [],
                        'skills': row['skills'] or [],
                        'starred_repos': row['starred_repos'] or [],
                        'finished_repos': row['finished_repos'] or [],
                        'learning_plan': row['learning_plan'] or [],
                        'updated_at': row['updated_at'].strftime("%Y-%m-%d %H:%M:%S") if row['updated_at'] else ''
                    }
                return None
        except Exception as e:
            print(f"[database] get_user_profile 失败: {e}")
            return None
    
    def get_all_user_profiles(self) -> Dict[str, Dict[str, Any]]:
        """获取所有用户档案"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM user_profiles ORDER BY updated_at DESC")
                rows = cur.fetchall()
                profiles = {}
                for row in rows:
                    profiles[row['username']] = {
                        'bio': row['bio'] or '',
                        'major': row['major'] or '',
                        'stage': row['stage'] or '',
                        'target_career': row['target_career'] or '',
                        'target_direction': row['target_direction'] or '',
                        'interests': row['interests'] or [],
                        'skills': row['skills'] or [],
                        'starred_repos': row['starred_repos'] or [],
                        'finished_repos': row['finished_repos'] or [],
                        'learning_plan': row['learning_plan'] or [],
                        'updated_at': row['updated_at'].strftime("%Y-%m-%d %H:%M:%S") if row['updated_at'] else ''
                    }
                return profiles
        except Exception as e:
            print(f"[database] get_all_user_profiles 失败: {e}")
            return {}
    
    def save_user_profile(self, username: str, profile: Dict[str, Any]) -> bool:
        """保存用户档案（插入或更新）"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_profiles (username, bio, major, stage, target_career, target_direction, interests, skills, starred_repos, finished_repos, learning_plan, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (username) DO UPDATE SET
                        bio = EXCLUDED.bio,
                        major = EXCLUDED.major,
                        stage = EXCLUDED.stage,
                        target_career = EXCLUDED.target_career,
                        target_direction = EXCLUDED.target_direction,
                        interests = EXCLUDED.interests,
                        skills = EXCLUDED.skills,
                        starred_repos = EXCLUDED.starred_repos,
                        finished_repos = EXCLUDED.finished_repos,
                        learning_plan = EXCLUDED.learning_plan,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    username,
                    profile.get('bio', ''),
                    profile.get('major', ''),
                    profile.get('stage', ''),
                    profile.get('target_career', ''),
                    profile.get('target_direction', ''),
                    json.dumps(profile.get('interests', [])),
                    json.dumps(profile.get('skills', [])),
                    json.dumps(profile.get('starred_repos', [])),
                    json.dumps(profile.get('finished_repos', [])),
                    json.dumps(profile.get('learning_plan', []))
                ))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] save_user_profile 失败: {e}")
            return False
    
    def delete_user_profile(self, username: str) -> bool:
        """删除用户档案"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM user_profiles WHERE username = %s", (username,))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] delete_user_profile 失败: {e}")
            return False
    
    # ========== 社区帖子方法 ==========
    
    def get_all_threads(self) -> List[Dict[str, Any]]:
        """获取所有帖子（包含回复）"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 获取所有主题
                cur.execute("SELECT * FROM community_threads ORDER BY created_at DESC")
                threads = cur.fetchall()
                
                result = []
                for thread in threads:
                    # 获取该主题的所有回复
                    cur.execute("SELECT * FROM community_posts WHERE thread_id = %s ORDER BY created_at", (thread['id'],))
                    posts = cur.fetchall()
                    
                    result.append({
                        'id': thread['id'],
                        'title': thread['title'],
                        'created_by': thread['created_by'],
                        'created_by_name': thread['created_by_name'],
                        'created_at': thread['created_at'].isoformat() if thread['created_at'] else None,
                        'category': thread['category'] or '其他',
                        'likes': thread['likes'] or [],
                        'posts': [
                            {
                                'id': p['id'],
                                'author': p['author'],
                                'author_name': p['author_name'],
                                'content': p['content'],
                                'time': p['created_at'].isoformat() if p['created_at'] else None,
                                'likes': p['likes'] or []
                            }
                            for p in posts
                        ]
                    })
                
                return result
        except Exception as e:
            print(f"[database] get_all_threads 失败: {e}")
            return []
    
    def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """获取单个帖子"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM community_threads WHERE id = %s", (thread_id,))
                thread = cur.fetchone()
                if not thread:
                    return None
                
                cur.execute("SELECT * FROM community_posts WHERE thread_id = %s ORDER BY created_at", (thread_id,))
                posts = cur.fetchall()
                
                return {
                    'id': thread['id'],
                    'title': thread['title'],
                    'created_by': thread['created_by'],
                    'created_by_name': thread['created_by_name'],
                    'created_at': thread['created_at'].isoformat() if thread['created_at'] else None,
                    'category': thread['category'] or '其他',
                    'likes': thread['likes'] or [],
                    'posts': [
                        {
                            'id': p['id'],
                            'author': p['author'],
                            'author_name': p['author_name'],
                            'content': p['content'],
                            'time': p['created_at'].isoformat() if p['created_at'] else None,
                            'likes': p['likes'] or []
                        }
                        for p in posts
                    ]
                }
        except Exception as e:
            print(f"[database] get_thread 失败: {e}")
            return None
    
    def create_thread(self, thread: Dict[str, Any]) -> bool:
        """创建帖子"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO community_threads (id, title, created_by, created_by_name, category, likes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    thread.get('id'),
                    thread.get('title'),
                    thread.get('created_by'),
                    thread.get('created_by_name'),
                    thread.get('category', '其他'),
                    json.dumps(thread.get('likes', []))
                ))
                
                # 添加初始帖子
                for post in thread.get('posts', []):
                    cur.execute("""
                        INSERT INTO community_posts (id, thread_id, author, author_name, content, likes)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        post.get('id'),
                        thread.get('id'),
                        post.get('author'),
                        post.get('author_name'),
                        post.get('content'),
                        json.dumps(post.get('likes', []))
                    ))
            
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] create_thread 失败: {e}")
            return False
    
    def add_post_to_thread(self, thread_id: str, post: Dict[str, Any]) -> bool:
        """添加回复到帖子"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO community_posts (id, thread_id, author, author_name, content, likes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    post.get('id'),
                    thread_id,
                    post.get('author'),
                    post.get('author_name'),
                    post.get('content'),
                    json.dumps(post.get('likes', []))
                ))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] add_post_to_thread 失败: {e}")
            return False
    
    def delete_thread(self, thread_id: str) -> bool:
        """删除帖子"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM community_threads WHERE id = %s", (thread_id,))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] delete_thread 失败: {e}")
            return False
    
    def delete_post(self, post_id: str) -> bool:
        """删除回复"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM community_posts WHERE id = %s", (post_id,))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] delete_post 失败: {e}")
            return False
    
    def update_thread_likes(self, thread_id: str, likes: List[str]) -> bool:
        """更新帖子点赞"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("UPDATE community_threads SET likes = %s WHERE id = %s", 
                           (json.dumps(likes), thread_id))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] update_thread_likes 失败: {e}")
            return False
    
    def update_post_likes(self, post_id: str, likes: List[str]) -> bool:
        """更新回复点赞"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("UPDATE community_posts SET likes = %s WHERE id = %s", 
                           (json.dumps(likes), post_id))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] update_post_likes 失败: {e}")
            return False
    
    # ========== 通知方法 ==========
    
    def get_notifications(self, username: str, unread_only: bool = False, limit: int = None) -> List[Dict[str, Any]]:
        """获取用户通知"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                sql = "SELECT * FROM notifications WHERE username = %s"
                params = [username]
                
                if unread_only:
                    sql += " AND is_read = FALSE"
                
                sql += " ORDER BY created_at DESC"
                
                if limit:
                    sql += " LIMIT %s"
                    params.append(limit)
                
                cur.execute(sql, params)
                rows = cur.fetchall()
                
                return [
                    {
                        'id': row['id'],
                        'type': row['notification_type'],
                        'title': row['title'],
                        'message': row['message'],
                        'link': row['link'],
                        'metadata': row['metadata'] or {},
                        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                        'read': row['is_read']
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"[database] get_notifications 失败: {e}")
            return []
    
    def add_notification(self, username: str, notification: Dict[str, Any]) -> bool:
        """添加通知"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO notifications (id, username, notification_type, title, message, link, metadata, is_read)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE)
                """, (
                    notification.get('id'),
                    username,
                    notification.get('type'),
                    notification.get('title'),
                    notification.get('message'),
                    notification.get('link', ''),
                    json.dumps(notification.get('metadata', {}))
                ))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] add_notification 失败: {e}")
            return False
    
    def mark_notification_read(self, notification_id: str = None, username: str = None) -> bool:
        """标记通知已读"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                if notification_id:
                    cur.execute("UPDATE notifications SET is_read = TRUE WHERE id = %s", (notification_id,))
                elif username:
                    cur.execute("UPDATE notifications SET is_read = TRUE WHERE username = %s", (username,))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] mark_notification_read 失败: {e}")
            return False
    
    def clear_notifications(self, username: str) -> bool:
        """清空用户通知"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM notifications WHERE username = %s", (username,))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] clear_notifications 失败: {e}")
            return False
    
    # ========== 用户活动方法 ==========
    
    def get_user_activity(self, username: str) -> Dict[str, List[Dict[str, Any]]]:
        """获取用户活动（浏览历史和收藏）"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM user_activity WHERE username = %s ORDER BY created_at DESC
                """, (username,))
                rows = cur.fetchall()
                
                history = []
                bookmarks = []
                
                for row in rows:
                    item = {
                        'type': row['item_type'],
                        'id': row['item_id'],
                        'name': row['item_name'],
                        'timestamp': row['created_at'].isoformat() if row['created_at'] else None
                    }
                    if row['activity_type'] == 'history':
                        history.append(item)
                    elif row['activity_type'] == 'bookmark':
                        bookmarks.append(item)
                
                return {'history': history, 'bookmarks': bookmarks}
        except Exception as e:
            print(f"[database] get_user_activity 失败: {e}")
            return {'history': [], 'bookmarks': []}
    
    def add_user_activity(self, username: str, activity_type: str, item_type: str, item_id: str, item_name: str) -> bool:
        """添加用户活动"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_activity (username, activity_type, item_type, item_id, item_name)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (username, activity_type, item_type, item_id) 
                    DO UPDATE SET item_name = EXCLUDED.item_name, created_at = CURRENT_TIMESTAMP
                """, (username, activity_type, item_type, item_id, item_name))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] add_user_activity 失败: {e}")
            return False
    
    def remove_user_activity(self, username: str, activity_type: str, item_type: str, item_id: str) -> bool:
        """删除用户活动"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM user_activity 
                    WHERE username = %s AND activity_type = %s AND item_type = %s AND item_id = %s
                """, (username, activity_type, item_type, item_id))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] remove_user_activity 失败: {e}")
            return False
    
    # ========== AI 对话历史方法 ==========
    
    def get_ai_conversations(self, username: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户 AI 对话历史"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM ai_conversations WHERE username = %s 
                    ORDER BY created_at DESC LIMIT %s
                """, (username, limit))
                rows = cur.fetchall()
                
                return [
                    {
                        'id': row['id'],
                        'type': row['conversation_type'],
                        'title': row['title'],
                        'messages': row['messages'] or [],
                        'context': row['context'] or {},
                        'timestamp': row['created_at'].isoformat() if row['created_at'] else None
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"[database] get_ai_conversations 失败: {e}")
            return []
    
    def save_ai_conversation(self, username: str, conversation: Dict[str, Any]) -> bool:
        """保存 AI 对话"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ai_conversations (id, username, conversation_type, title, messages, context)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        messages = EXCLUDED.messages,
                        context = EXCLUDED.context
                """, (
                    conversation.get('id'),
                    username,
                    conversation.get('type'),
                    conversation.get('title'),
                    json.dumps(conversation.get('messages', [])),
                    json.dumps(conversation.get('context', {}))
                ))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] save_ai_conversation 失败: {e}")
            return False
    
    def delete_ai_conversation(self, conversation_id: str) -> bool:
        """删除 AI 对话"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM ai_conversations WHERE id = %s", (conversation_id,))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] delete_ai_conversation 失败: {e}")
            return False
    
    def clear_ai_conversations(self, username: str) -> bool:
        """清空用户 AI 对话"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM ai_conversations WHERE username = %s", (username,))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] clear_ai_conversations 失败: {e}")
            return False
    
    # ========== 职业反馈方法 ==========
    
    def get_career_feedback(self) -> Dict[str, Dict[str, int]]:
        """获取所有职业反馈"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM career_feedback")
                rows = cur.fetchall()
                
                return {
                    row['career_name']: {
                        'like': row['like_count'],
                        'dislike': row['dislike_count']
                    }
                    for row in rows
                }
        except Exception as e:
            print(f"[database] get_career_feedback 失败: {e}")
            return {}
    
    def update_career_feedback(self, career_name: str, like_delta: int = 0, dislike_delta: int = 0) -> bool:
        """更新职业反馈"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO career_feedback (career_name, like_count, dislike_count)
                    VALUES (%s, GREATEST(0, %s), GREATEST(0, %s))
                    ON CONFLICT (career_name) DO UPDATE SET
                        like_count = GREATEST(0, career_feedback.like_count + %s),
                        dislike_count = GREATEST(0, career_feedback.dislike_count + %s),
                        updated_at = CURRENT_TIMESTAMP
                """, (career_name, max(0, like_delta), max(0, dislike_delta), like_delta, dislike_delta))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] update_career_feedback 失败: {e}")
            return False
    
    def set_career_feedback(self, career_name: str, like_count: int, dislike_count: int) -> bool:
        """设置职业反馈"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO career_feedback (career_name, like_count, dislike_count)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (career_name) DO UPDATE SET
                        like_count = EXCLUDED.like_count,
                        dislike_count = EXCLUDED.dislike_count,
                        updated_at = CURRENT_TIMESTAMP
                """, (career_name, like_count, dislike_count))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] set_career_feedback 失败: {e}")
            return False
    
    # ========== 用户反馈方法 ==========
    
    def get_user_feedback(self, username: str) -> Dict[str, Any]:
        """获取用户反馈数据"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM user_feedback WHERE username = %s", (username,))
                rows = cur.fetchall()
                
                career_likes = []
                career_dislikes = []
                course_ratings = {}
                advisor_ratings = {}
                practice_ratings = {}
                
                for row in rows:
                    if row['feedback_type'] == 'career_like':
                        career_likes.append(row['target_name'])
                    elif row['feedback_type'] == 'career_dislike':
                        career_dislikes.append(row['target_name'])
                    elif row['feedback_type'] == 'course_rating':
                        course_ratings[row['target_name']] = row['rating']
                    elif row['feedback_type'] == 'advisor_rating':
                        advisor_ratings[row['target_name']] = row['rating']
                    elif row['feedback_type'] == 'practice_rating':
                        practice_ratings[row['target_name']] = row['rating']
                
                return {
                    'career_likes': career_likes,
                    'career_dislikes': career_dislikes,
                    'course_ratings': course_ratings,
                    'advisor_ratings': advisor_ratings,
                    'practice_ratings': practice_ratings
                }
        except Exception as e:
            print(f"[database] get_user_feedback 失败: {e}")
            return {
                'career_likes': [],
                'career_dislikes': [],
                'course_ratings': {},
                'advisor_ratings': {},
                'practice_ratings': {}
            }
    
    def save_user_feedback(self, username: str, feedback_type: str, target_name: str, rating: int = None) -> bool:
        """保存用户反馈"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_feedback (username, feedback_type, target_name, rating)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username, feedback_type, target_name) DO UPDATE SET
                        rating = EXCLUDED.rating,
                        created_at = CURRENT_TIMESTAMP
                """, (username, feedback_type, target_name, rating))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] save_user_feedback 失败: {e}")
            return False
    
    def remove_user_feedback(self, username: str, feedback_type: str, target_name: str) -> bool:
        """删除用户反馈"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM user_feedback 
                    WHERE username = %s AND feedback_type = %s AND target_name = %s
                """, (username, feedback_type, target_name))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            print(f"[database] remove_user_feedback 失败: {e}")
            return False
    
    # ========== 提醒配置方法 ==========
    
    def get_reminder_config(self, username: str) -> Dict[str, Any]:
        """获取用户提醒配置"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM reminder_config WHERE username = %s", (username,))
                row = cur.fetchone()
                
                if row:
                    return {
                        'frequency': row['frequency'] or 'weekly',
                        'enabled_types': row['enabled_types'] or ['course', 'practice', 'career'],
                        'last_check': row['last_check'].isoformat() if row['last_check'] else None
                    }
                
                return {
                    'frequency': 'weekly',
                    'enabled_types': ['course', 'practice', 'career'],
                    'last_check': None
                }
        except Exception as e:
            print(f"[database] get_reminder_config 失败: {e}")
            return {
                'frequency': 'weekly',
                'enabled_types': ['course', 'practice', 'career'],
                'last_check': None
            }
    
    def save_reminder_config(self, username: str, config: Dict[str, Any]) -> bool:
        """保存用户提醒配置"""
        self._ensure_connection()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO reminder_config (username, frequency, enabled_types, last_check)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username) DO UPDATE SET
                        frequency = EXCLUDED.frequency,
                        enabled_types = EXCLUDED.enabled_types,
                        last_check = EXCLUDED.last_check,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    username,
                    config.get('frequency', 'weekly'),
                    json.dumps(config.get('enabled_types', ['course', 'practice', 'career'])),
                    config.get('last_check')
                ))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"[database] save_reminder_config 失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.conn and not self.conn.closed:
            self.conn.close()


# 全局数据存储实例
_data_store: Optional[DataStore] = None


def get_data_store() -> Optional[DataStore]:
    """
    获取数据存储实例。
    根据 DB_TYPE 配置决定使用哪种存储方式。
    配置来源优先级: 环境变量 > Streamlit secrets > 默认值(json)
    
    Returns:
        DataStore 实例，如果使用 JSON 模式则返回 None
    """
    global _data_store
    
    db_type = _get_secret("DB_TYPE", "json").lower()
    
    if db_type == "postgresql":
        if _data_store is None:
            try:
                _data_store = PostgreSQLStore()
                print("[database] 使用 PostgreSQL 数据存储")
            except Exception as e:
                print(f"[database] PostgreSQL 初始化失败，回退到 JSON: {e}")
                return None
        return _data_store
    
    # 默认返回 None，表示使用 JSON 文件存储
    return None


def is_using_database() -> bool:
    """检查是否正在使用数据库存储"""
    db_type = _get_secret("DB_TYPE", "json").lower()
    return db_type == "postgresql" and PSYCOPG2_AVAILABLE

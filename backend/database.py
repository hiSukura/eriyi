"""
绘梨衣后端 · 数据库层
SQLite 数据库连接、Schema 初始化
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from config import DATABASE_PATH

SCHEMA_SQL = """
-- 日记表
CREATE TABLE IF NOT EXISTS diaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    title TEXT DEFAULT '',
    content TEXT DEFAULT '',
    mood TEXT DEFAULT '安静',
    time_period TEXT DEFAULT '未知',
    mp3_path TEXT DEFAULT '',
    word_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 记忆事件表
CREATE TABLE IF NOT EXISTS memory_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    category TEXT DEFAULT '成长',
    perspective TEXT DEFAULT 'sakura',
    title TEXT DEFAULT '',
    content TEXT NOT NULL,
    milestone INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 状态历史表
CREATE TABLE IF NOT EXISTS state_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now', 'localtime')),
    time_period TEXT DEFAULT '未知',
    mood TEXT DEFAULT '安静',
    sakura_status TEXT DEFAULT 'online',
    extra_data TEXT DEFAULT '{}'
);

-- 语音文件注册表
CREATE TABLE IF NOT EXISTS voice_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL UNIQUE,
    title TEXT DEFAULT '',
    description TEXT DEFAULT '',
    category TEXT DEFAULT '未分类',
    duration REAL DEFAULT 0,
    file_size INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 里程碑表
CREATE TABLE IF NOT EXISTS milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    phase TEXT DEFAULT '',
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    completed INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 设置表
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT DEFAULT '',
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_diaries_date ON diaries(date);
CREATE INDEX IF NOT EXISTS idx_memory_events_date ON memory_events(date);
CREATE INDEX IF NOT EXISTS idx_memory_events_category ON memory_events(category);
CREATE INDEX IF NOT EXISTS idx_state_history_timestamp ON state_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_voice_files_category ON voice_files(category);
"""


def init_database():
    """初始化数据库，创建所有表"""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()


@contextmanager
def get_db():
    """获取数据库连接的上下文管理器"""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_db_cursor():
    """获取数据库游标（旧版兼容）"""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def dict_from_row(row):
    """将 sqlite3.Row 转换为字典"""
    if row is None:
        return None
    return dict(row)


def rows_to_dicts(rows):
    """将 sqlite3.Row 列表转换为字典列表"""
    return [dict(row) for row in rows]

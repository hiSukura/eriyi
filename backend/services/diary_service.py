"""
日记服务层
"""
import os
from datetime import datetime
from pathlib import Path

from database import get_db, dict_from_row, rows_to_dicts
from config import DIARY_DIR


def get_all_diaries(limit: int = 30, offset: int = 0) -> list[dict]:
    """获取日记列表（按日期倒序）"""
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM diaries ORDER BY date DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        return rows_to_dicts(rows)


def get_diary_by_date(date_str: str) -> dict | None:
    """获取指定日期的日记"""
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM diaries WHERE date = ?",
            (date_str,)
        ).fetchone()
        return dict_from_row(row)


def get_today_diary() -> dict | None:
    """获取今天的日记"""
    today = datetime.now().strftime("%Y-%m-%d")
    return get_diary_by_date(today)


def upsert_diary(data: dict) -> dict:
    """创建或更新日记"""
    with get_db() as db:
        existing = db.execute(
            "SELECT id FROM diaries WHERE date = ?",
            (data["date"],)
        ).fetchone()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        word_count = len(data.get("content", ""))

        diary_data = (
            data.get("title", ""),
            data.get("content", ""),
            data.get("mood", "安静"),
            data.get("time_period", "未知"),
            data.get("mp3_path", ""),
            word_count,
        )

        if existing:
            db.execute(
                """UPDATE diaries 
                   SET title=?, content=?, mood=?, time_period=?, mp3_path=?, word_count=?, updated_at=?
                   WHERE date=?""",
                (*diary_data, now, data["date"])
            )
        else:
            db.execute(
                """INSERT INTO diaries (title, content, mood, time_period, mp3_path, word_count, date)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (*diary_data, data["date"])
            )

        db.commit()

        row = db.execute(
            "SELECT * FROM diaries WHERE date = ?",
            (data["date"],)
        ).fetchone()
        return dict_from_row(row)


def delete_diary(date_str: str) -> bool:
    """删除指定日期的日记"""
    with get_db() as db:
        cursor = db.execute("DELETE FROM diaries WHERE date = ?", (date_str,))
        db.commit()
        return cursor.rowcount > 0


def get_diary_count() -> int:
    """获取日记总数"""
    with get_db() as db:
        row = db.execute("SELECT COUNT(*) as cnt FROM diaries").fetchone()
        return row["cnt"]


def sync_diary_files_to_db():
    """从文件系统扫描日记目录，同步到数据库"""
    if not DIARY_DIR.exists():
        return 0

    count = 0
    for md_file in DIARY_DIR.glob("*.md"):
        date_str = md_file.stem
        content = md_file.read_text(encoding="utf-8")
        mp3_file = DIARY_DIR / f"{date_str}.mp3"

        # 从内容中提取标题（第一行 # 开头）
        lines = content.strip().split("\n")
        title = ""
        mood = "安静"
        time_period = "未知"
        for line in lines[:10]:
            if line.startswith("# "):
                title = line[2:].strip()
            if "心情" in line and "：" in line:
                mood = line.split("：")[-1].strip()
            if "时间" in line and "：" in line:
                time_period = line.split("：")[-1].strip()

        upsert_diary({
            "date": date_str,
            "title": title or f"绘梨衣日记 · {date_str}",
            "content": content,
            "mood": mood,
            "time_period": time_period,
            "mp3_path": str(mp3_file) if mp3_file.exists() else "",
        })
        count += 1

    return count


# ═══════════════════════════════════════════════════
# 日记v2.0 · 时刻（Moments）
# ═══════════════════════════════════════════════════

def add_moment(date_str: str, content: str, mood: str = "安静",
               time_period: str = "未知") -> dict:
    """添加一个日记时刻"""
    with get_db() as db:
        cursor = db.execute(
            """INSERT INTO diary_moments (date, timestamp, time_period, mood, content)
               VALUES (?, datetime('now', 'localtime'), ?, ?, ?)""",
            (date_str, time_period, mood, content),
        )
        db.commit()

        row = db.execute(
            "SELECT * FROM diary_moments WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return dict_from_row(row)


def get_today_moments() -> list[dict]:
    """获取今天的所有时刻"""
    today = datetime.now().strftime("%Y-%m-%d")
    with get_db() as db:
        rows = db.execute(
            """SELECT * FROM diary_moments
               WHERE date = ? ORDER BY timestamp ASC""",
            (today,),
        ).fetchall()
        return rows_to_dicts(rows)


def get_moments_by_date(date_str: str) -> list[dict]:
    """获取指定日期的所有时刻"""
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM diary_moments WHERE date = ? ORDER BY timestamp ASC",
            (date_str,),
        ).fetchall()
        return rows_to_dicts(rows)


def get_moment_count(date_str: str = None) -> int:
    """获取时刻数量"""
    with get_db() as db:
        if date_str:
            row = db.execute(
                "SELECT COUNT(*) as cnt FROM diary_moments WHERE date = ?",
                (date_str,),
            ).fetchone()
        else:
            row = db.execute(
                "SELECT COUNT(*) as cnt FROM diary_moments"
            ).fetchone()
        return row["cnt"] if row else 0

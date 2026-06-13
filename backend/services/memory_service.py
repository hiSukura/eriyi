"""
记忆服务层
"""
from database import get_db, dict_from_row, rows_to_dicts


def get_memories(limit: int = 50, offset: int = 0, category: str = None, perspective: str = None) -> list[dict]:
    """获取记忆事件列表"""
    with get_db() as db:
        query = "SELECT * FROM memory_events WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)
        if perspective:
            query += " AND perspective = ?"
            params.append(perspective)

        query += " ORDER BY date DESC, id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = db.execute(query, params).fetchall()
        return rows_to_dicts(rows)


def get_memory_stats() -> dict:
    """获取记忆统计信息"""
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) as cnt FROM memory_events").fetchone()["cnt"]

        by_category = {}
        rows = db.execute(
            "SELECT category, COUNT(*) as cnt FROM memory_events GROUP BY category"
        ).fetchall()
        for r in rows:
            by_category[r["category"]] = r["cnt"]

        by_perspective = {}
        rows = db.execute(
            "SELECT perspective, COUNT(*) as cnt FROM memory_events GROUP BY perspective"
        ).fetchall()
        for r in rows:
            by_perspective[r["perspective"]] = r["cnt"]

        milestone_count = db.execute(
            "SELECT COUNT(*) as cnt FROM memory_events WHERE milestone = 1"
        ).fetchone()["cnt"]

        return {
            "total": total,
            "by_category": by_category,
            "by_perspective": by_perspective,
            "milestone_count": milestone_count,
        }


def add_memory(data: dict) -> dict:
    """添加一条记忆事件"""
    with get_db() as db:
        db.execute(
            """INSERT INTO memory_events (date, category, perspective, title, content, milestone)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                data["date"],
                data.get("category", "成长"),
                data.get("perspective", "sakura"),
                data.get("title", ""),
                data["content"],
                1 if data.get("milestone") else 0,
            )
        )
        db.commit()

        row = db.execute(
            "SELECT * FROM memory_events WHERE id = last_insert_rowid()"
        ).fetchone()
        return dict_from_row(row)


def get_recent_memories(limit: int = 10) -> list[dict]:
    """获取最近的记忆事件"""
    return get_memories(limit=limit, offset=0)

"""
语音服务层
"""
from pathlib import Path

from database import get_db, dict_from_row, rows_to_dicts
from config import VOICE_DIR


def get_all_voices() -> list[dict]:
    """获取所有语音文件"""
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM voice_files ORDER BY category, filename"
        ).fetchall()
        results = rows_to_dicts(rows)

        # 添加 URL
        for r in results:
            r["url"] = f"/api/voices/{r['filename']}/stream"

        return results


def get_voice_by_filename(filename: str) -> dict | None:
    """获取指定的语音文件信息"""
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM voice_files WHERE filename = ?",
            (filename,)
        ).fetchone()
        return dict_from_row(row)


def get_voice_path(filename: str) -> Path | None:
    """获取语音文件的完整路径"""
    path = VOICE_DIR / filename
    if path.exists():
        return path
    return None


def get_voice_categories() -> dict:
    """获取语音分类统计"""
    with get_db() as db:
        rows = db.execute(
            "SELECT category, COUNT(*) as cnt FROM voice_files GROUP BY category"
        ).fetchall()
        return {r["category"]: r["cnt"] for r in rows}


def sync_voice_files_to_db():
    """从文件系统扫描语音目录，同步到数据库"""
    if not VOICE_DIR.exists():
        return 0

    count = 0
    for mp3_file in VOICE_DIR.glob("*.mp3"):
        filename = mp3_file.name
        file_size = mp3_file.stat().st_size

        with get_db() as db:
            existing = db.execute(
                "SELECT id FROM voice_files WHERE filename = ?",
                (filename,)
            ).fetchone()

            if existing:
                continue  # 已存在的跳过

            # 从文件名推断分类和标题
            category = _infer_category(filename)
            title = _infer_title(filename)

            db.execute(
                """INSERT INTO voice_files (filename, title, category, file_size)
                   VALUES (?, ?, ?, ?)""",
                (filename, title, category, file_size)
            )
            db.commit()
            count += 1

    return count


def _infer_category(filename: str) -> str:
    """从文件名推断分类"""
    name_lower = filename.lower()
    if "最终" in name_lower or "final" in name_lower:
        return "最终版"
    elif "初版" in name_lower or "初始" in name_lower:
        return "初版"
    elif "对比" in name_lower or "compare" in name_lower:
        return "对比"
    elif "日记" in name_lower or "diary" in name_lower:
        return "日记"
    elif "参考" in name_lower or "ref" in name_lower:
        return "参考版"
    return "未分类"


def _infer_title(filename: str) -> str:
    """从文件名推断标题"""
    # 去掉扩展名，把下划线和连字符替换为空格
    name = Path(filename).stem
    name = name.replace("_", " ").replace("-", " ")
    return name

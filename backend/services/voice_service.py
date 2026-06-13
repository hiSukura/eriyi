"""
语音服务层 · v2.0 — 含念白分句数据
"""
import json
from pathlib import Path

from database import get_db, dict_from_row, rows_to_dicts
from config import VOICE_DIR, VOICE_CLONE_DIR


def get_all_voices() -> list[dict]:
    """获取所有语音文件（含念白）"""
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM voice_files ORDER BY category, filename"
        ).fetchall()
        results = rows_to_dicts(rows)

        for r in results:
            r["url"] = f"/api/voices/{r['filename']}/stream"

        return results


def get_voice_by_filename(filename: str) -> dict | None:
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM voice_files WHERE filename = ?", (filename,)
        ).fetchone()
        return dict_from_row(row)


def get_voice_path(filename: str) -> Path | None:
    # 先查 MP3, 再查 念白 WAV
    path = VOICE_DIR / filename
    if path.exists():
        return path
    path = VOICE_DIR / "念白_分句" / "sentences" / filename
    if path.exists():
        return path
    return None


def get_voice_categories() -> dict:
    with get_db() as db:
        rows = db.execute(
            "SELECT category, COUNT(*) as cnt FROM voice_files GROUP BY category"
        ).fetchall()
        return {r["category"]: r["cnt"] for r in rows}


def get_narration_sentences() -> list[dict]:
    """获取念白分句数据（从 sentence_meta.json + 数据库）"""
    meta_path = VOICE_DIR / "念白_分句" / "sentence_meta.json"
    sentences = []
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        for s in meta.get("sentences", []):
            sentences.append({
                "index": s["index"],
                "filename": s["filename"],
                "duration_sec": s["duration_sec"],
                "start_sec": s["start_sec"],
                "end_sec": s["end_sec"],
                "url": f"/api/voices/narration/{s['filename']}",
            })
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return sentences


def sync_voice_files_to_db():
    """扫描语音目录 + 念白目录，同步到数据库"""
    count = 0

    # MP3 文件
    if VOICE_DIR.exists():
        for mp3_file in VOICE_DIR.glob("*.mp3"):
            if _sync_single_file(mp3_file, "mp3"):
                count += 1

    # 念白 WAV 文件
    narration_dir = VOICE_DIR / "念白_分句" / "sentences"
    if narration_dir.exists():
        for wav_file in narration_dir.glob("*.wav"):
            if _sync_single_file(wav_file, "narration"):
                count += 1

    return count


def _sync_single_file(fpath: Path, ftype: str) -> bool:
    """同步单个文件到数据库"""
    filename = fpath.name
    file_size = fpath.stat().st_size

    with get_db() as db:
        existing = db.execute(
            "SELECT id FROM voice_files WHERE filename = ?", (filename,)
        ).fetchone()
        if existing:
            return False

        if ftype == "narration":
            category = "念白"
            title = f"分句 {fpath.stem}"
        else:
            category = _infer_category(filename)
            title = _infer_title(filename)

        db.execute(
            """INSERT INTO voice_files (filename, title, category, file_size)
               VALUES (?, ?, ?, ?)""",
            (filename, title, category, file_size),
        )
        db.commit()
        return True


def _infer_category(filename: str) -> str:
    name_lower = filename.lower()
    if "最终" in name_lower or "final" in name_lower: return "最终版"
    elif "初版" in name_lower or "初始" in name_lower: return "初版"
    elif "对比" in name_lower or "compare" in name_lower: return "对比"
    elif "日记" in name_lower or "diary" in name_lower: return "日记"
    elif "参考" in name_lower or "ref" in name_lower: return "参考版"
    return "未分类"


def _infer_title(filename: str) -> str:
    name = Path(filename).stem
    return name.replace("_", " ").replace("-", " ")

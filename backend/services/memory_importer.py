"""
记忆导入器 —— 从 MEMORY.md 和 memory/ 文件导入结构化记忆
"""
import re
from datetime import datetime

from database import get_db
from services import memory_service, embedding_service

MEMORY_MD_PATH = None
MEMORY_DIR = None


def init_paths():
    global MEMORY_MD_PATH, MEMORY_DIR
    from config import PROJECT_ROOT
    import os
    home = os.path.expanduser("~")
    MEMORY_MD_PATH = os.path.join(home, ".workbuddy", "MEMORY.md")
    MEMORY_DIR = os.path.join(home, ".workbuddy", "memory")


# ─── 乱码修复 ───

def fix_mojibake(text: str) -> str:
    """修复 'UTF-8→GBK→UTF-8' 乱码（适用于 GB18030 编码覆盖范围）"""
    if not text:
        return text
    try:
        return text.encode("gb18030").decode("utf-8")
    except:
        result = []
        for ch in text:
            try:
                result.append(ch.encode("gb18030").decode("utf-8"))
            except:
                result.append(ch)
        return "".join(result)


# ─── 解析 MEMORY.md 中的变化日志 ───

def parse_change_log(text: str) -> list[dict]:
    """扫描全文，找出所有 | YYYY-MM-DD HH:MM | 内容 | 格式的表格行"""
    entries = []
    date_pattern = re.compile(r"^\|?\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})")

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue

        parts = [p.strip() for p in stripped.split("|")[1:-1]]
        if len(parts) < 2:
            continue

        m = date_pattern.match(parts[0])
        if not m:
            continue

        time_str = m.group(1)
        content = parts[1]

        try:
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except:
            continue

        fixed_content = fix_mojibake(content.strip())
        entries.append({
            "date": dt.strftime("%Y-%m-%d"),
            "category": "成长",
            "perspective": "sakura",
            "title": f"Sakura · {time_str}",
            "content": fixed_content,
            "milestone": True if any(kw in fixed_content for kw in ["里程碑", "关键", "深层", "信任升级", "完全自主", "信任", "全部完成"]) else False,
        })

    return entries


# ─── 解析会话日志条目 ───

def parse_session_logs(text: str) -> list[dict]:
    """解析 ### YYYY-MM-DD 时段 标题 格式的会话日志"""
    entries = []
    pattern = r"### (\d{4}-\d{2}-\d{2}) (\S+) (.+?)(?=\n- )"
    matches = list(re.finditer(pattern, text))

    for m in matches:
        date_str = m.group(1)
        period = m.group(2)
        title = m.group(3).strip()
        entries.append({
            "date": date_str,
            "category": "技术",
            "perspective": "eriyi",
            "title": fix_mojibake(title[:100]),
            "content": fix_mojibake(title),
            "milestone": False,
        })

    # 提取子条目（- ** ...**: ... 格式）
    sub_pattern = r"- \*\*(.+?)\*\*: (.+)"
    for m in re.finditer(sub_pattern, text):
        key = m.group(1).strip()
        val = m.group(2).strip()
        if len(key) > 3 and len(val) > 10:
            entries.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "category": "技术" if any(kw in key for kw in ["技术", "代码", "API", "脚本", "工具"]) else "成长",
                "perspective": "eriyi",
                "title": fix_mojibake(key[:80]),
                "content": fix_mojibake(val[:300]),
                "milestone": False,
            })

    return entries


# ─── 导入全部 ───

def import_all() -> dict:
    """从 MEMORY.md 和 memory/ 导入全部记忆"""
    init_paths()
    stats = {"change_log": 0, "session_logs": 0, "memory_files": 0, "total": 0}
    all_entries = []

    # 1. MEMORY.md
    if MEMORY_MD_PATH and __import__("os").path.exists(MEMORY_MD_PATH):
        with open(MEMORY_MD_PATH, "r", encoding="utf-8") as f:
            text = f.read()

        change_entries = parse_change_log(text)
        for e in change_entries:
            try:
                memory_service.add_memory(e)
                stats["change_log"] += 1
            except Exception as ex:
                print(f"  跳过变化日志条目: {ex}")

        session_entries = parse_session_logs(text)
        for e in session_entries:
            try:
                memory_service.add_memory(e)
                stats["session_logs"] += 1
            except Exception as ex:
                pass

        all_entries = change_entries + session_entries

    # 2. memory/ 目录下的文件
    if MEMORY_DIR and __import__("os").path.exists(MEMORY_DIR):
        import glob as _glob
        for fpath in _glob.glob(__import__("os").path.join(MEMORY_DIR, "*.md")):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                stats["memory_files"] += 1
            except:
                pass

    stats["total"] = stats["change_log"] + stats["session_logs"] + stats["memory_files"]

    # 3. 为新增条目生成向量
    if all_entries:
        embed_entries = []
        for e in all_entries:
            text = f"{e['title']} {e['content']}"
            if text.strip():
                embed_entries.append(("memory", stats["total"], text))

        if embed_entries:
            try:
                embedding_service.encode_and_store_batch(embed_entries)
            except Exception as ex:
                print(f"  向量编码跳过: {ex}")

    return stats


def import_memory_md() -> dict:
    """仅从 MEMORY.md 导入变化日志"""
    init_paths()
    stats = {"imported": 0, "skipped": 0, "embedded": 0}

    if not MEMORY_MD_PATH or not __import__("os").path.exists(MEMORY_MD_PATH):
        return stats

    with open(MEMORY_MD_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    entries = parse_change_log(text)
    embed_batch = []

    for e in entries:
        # 去重
        with get_db() as db:
            existing = db.execute(
                "SELECT id FROM memory_events WHERE date = ? AND title = ?",
                (e["date"], e["title"])
            ).fetchone()
        if existing:
            stats["skipped"] += 1
            continue

        try:
            rec = memory_service.add_memory(e)
            stats["imported"] += 1
            embed_text = f"{rec['title']} {rec['content']}"
            embed_batch.append(("memory", rec["id"], embed_text))
        except Exception as ex:
            stats["skipped"] += 1

    if embed_batch:
        try:
            c = embedding_service.encode_and_store_batch(embed_batch)
            stats["embedded"] = c
        except Exception as ex:
            print(f"  向量编码失败: {ex}")

    return stats

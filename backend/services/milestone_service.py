"""
里程碑自动检测服务 · 扫描每日日志 → 识别里程碑事件 → 自动入库
"""
import re
from datetime import datetime
from pathlib import Path

from database import get_db, dict_from_row, rows_to_dicts
from config import MEMORY_DIR, PROJECT_ROOT

# ── 检测规则 ──
DETECTION_RULES = [
    # Phase 完成
    {
        "pattern": r"Phase\s*(\d[\d.]*)\s*(?:全部|所有|整体)?\s*(?:完成|✅|收尾|收官|闭合)",
        "extract": lambda m, ctx: {
            "phase": f"Phase {m.group(1)}",
            "title": f"Phase {m.group(1)} 全部完成",
        },
    },
    # Phase 子项完成
    {
        "pattern": r"(\d+\.\d+)\s*(?:完成|✅)",
        "extract": lambda m, ctx: {
            "phase": detect_phase_from_context(ctx),
            "title": f"Phase子项 {m.group(1)} 完成",
        },
    },
    # 版本升级
    {
        "pattern": r"(?:路线图|版本).*v(\d+\.\d+)",
        "extract": lambda m, ctx: {
            "phase": "里程碑",
            "title": f"路线图升级至 v{m.group(1)}",
        },
    },
    # 全新系统/组件上线
    {
        "pattern": r"(?:创建|新增|搭建|建成|上线)[^。]*?([\u4e00-\u9fff]{2,8}(?:系统|服务|页面|面板|后端|前端|API|仪表盘|托盘))",
        "extract": lambda m, ctx: {
            "phase": detect_phase_from_context(ctx),
            "title": f"新系统上线: {m.group(1)}",
        },
    },
    # 跳过纯同步条目
    {"pattern": r"读.*MEMORY\.md|同步.*确认|READY|自组织", "skip": True},
]


def detect_phase_from_context(text: str) -> str:
    """从上下文推断所属 Phase"""
    for m in re.finditer(r"Phase\s*(\d[\d.]*)", text):
        return f"Phase {m.group(1)}"
    # 从时间推断：凌晨6点 → 大概率活跃Phase
    return "活跃Phase"


def scan_daily_log(path: Path) -> list[dict]:
    """扫描单个每日日志，提取里程碑"""
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8", errors="replace")
    date_str = path.stem  # "2026-06-14"

    milestones = []

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped or len(stripped) < 6:
            continue

        # 只扫描非列表项（关键行）
        for rule in DETECTION_RULES:
            if rule.get("skip"):
                continue

            m = re.search(rule["pattern"], stripped)
            if not m:
                continue

            info = rule["extract"](m, content[:2000])
            # 去重检查
            dup = False
            for existing in milestones:
                if existing["title"] == info["title"]:
                    dup = True
                    break
            if dup:
                continue

            milestones.append({
                "date": date_str,
                "phase": info["phase"],
                "title": info["title"],
                "description": stripped[:200],
                "completed": 1,
            })

    return milestones


def scan_all_logs() -> list[dict]:
    """扫描所有每日日志"""
    all_milestones = []
    log_dir = MEMORY_DIR

    if not log_dir.exists():
        return []

    for log_file in sorted(log_dir.glob("*.md")):
        if log_file.stem.startswith("MEMORY"):
            continue  # 跳过MEMORY.md本身
        found = scan_daily_log(log_file)
        all_milestones.extend(found)

    return all_milestones


def sync_milestones() -> dict:
    """扫描日志 → 检测里程碑 → 去重入库 → 返回新增数量"""
    detected = scan_all_logs()

    with get_db() as conn:
        # 获取已有里程碑标题（用于去重）
        existing_rows = conn.execute(
            "SELECT title FROM milestones"
        ).fetchall()
        existing_titles = {r["title"] for r in existing_rows}

        new_count = 0
        for m in detected:
            if m["title"] in existing_titles:
                continue

            conn.execute(
                """INSERT INTO milestones (date, phase, title, description, completed)
                   VALUES (?, ?, ?, ?, ?)""",
                (m["date"], m["phase"], m["title"], m["description"], m["completed"]),
            )
            existing_titles.add(m["title"])
            new_count += 1

        conn.commit()

    return {"detected": len(detected), "new": new_count, "total_existing": len(existing_titles)}


def get_all_milestones(limit: int = 50) -> list[dict]:
    """获取所有里程碑"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM milestones ORDER BY date DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return rows_to_dicts(rows)


def get_milestone_count() -> int:
    """获取里程碑总数"""
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM milestones").fetchone()
        return row["cnt"] if row else 0


def get_recent_milestones(limit: int = 5) -> list[dict]:
    """获取最近里程碑"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM milestones WHERE completed = 1 ORDER BY date DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return rows_to_dicts(rows)


def run_auto_detect():
    """启动时自动运行一次检测"""
    try:
        result = sync_milestones()
        if result["new"] > 0:
            print(f"   🔔 自动检测到 {result['new']} 个新里程碑（共 {result['total_existing']} 个）")
    except Exception as e:
        print(f"   ⚠ 里程碑自动检测失败: {e}")

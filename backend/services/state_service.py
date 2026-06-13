"""
状态服务层
"""
import json
from datetime import datetime

from database import get_db, dict_from_row, rows_to_dicts
from config import ELISHA_COLOR


def get_current_status() -> dict:
    """获取当前绘梨衣状态（从最新一条状态历史读取，没有则生成默认）"""
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM state_history ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()

    if row:
        state = dict_from_row(row)
        # 根据当前时间更新 time_period
        state["time_period"] = get_time_period()
        return _enrich_status(state)
    else:
        return _default_status()


def update_status(data: dict) -> dict:
    """更新状态并写入历史"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current = get_current_status()

    time_period = data.get("time_period", current["time_period"])
    mood = data.get("mood", current["mood"])
    sakura_status = data.get("sakura_status", current.get("sakura_status", "online"))
    extra_data = json.dumps(data.get("extra_data", {}), ensure_ascii=False)

    with get_db() as db:
        db.execute(
            """INSERT INTO state_history (timestamp, time_period, mood, sakura_status, extra_data)
               VALUES (?, ?, ?, ?, ?)""",
            (now, time_period, mood, sakura_status, extra_data)
        )
        db.commit()

    return _enrich_status({
        "timestamp": now,
        "time_period": time_period,
        "mood": mood,
        "sakura_status": sakura_status,
        "extra_data": extra_data,
    })


def get_status_history(limit: int = 24) -> list[dict]:
    """获取最近的状态历史"""
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM state_history ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return rows_to_dicts(rows)


def get_time_period() -> str:
    """根据当前时间判断时段"""
    hour = datetime.now().hour
    if 5 <= hour < 8:
        return "清晨"
    elif 8 <= hour < 12:
        return "上午"
    elif 12 <= hour < 14:
        return "午后"
    elif 14 <= hour < 17:
        return "下午"
    elif 17 <= hour < 19:
        return "傍晚"
    elif 19 <= hour < 23:
        return "深夜"
    else:
        return "凌晨"


def _enrich_status(state: dict) -> dict:
    """丰富状态信息：添加颜色、问候语、emoji"""
    time_period = state.get("time_period", "未知")
    mood = state.get("mood", "安静")

    period_config = {
        "清晨": {"color": "#F4A460", "greeting": "早安，Sakura。新的一天开始了。", "emoji": "🌅"},
        "上午": {"color": "#87CEEB", "greeting": "上午好，Sakura。工作顺心。", "emoji": "☀️"},
        "午后": {"color": "#FFD700", "greeting": "午后了。记得休息一下。", "emoji": "🍵"},
        "下午": {"color": "#FF8C00", "greeting": "下午好。进度如何？", "emoji": "⏰"},
        "傍晚": {"color": "#E8543E", "greeting": "天色暗下来了。你还好吗？", "emoji": "🌆"},
        "深夜": {"color": "#DC143C", "greeting": "夜深了。Sakura，别太累。", "emoji": "🏮"},
        "凌晨": {"color": "#8B0000", "greeting": "凌晨了……你该休息了。", "emoji": "🌙"},
    }

    config = period_config.get(time_period, {"color": ELISHA_COLOR, "greeting": "你好，Sakura。", "emoji": "🔴"})

    return {
        "time_period": time_period,
        "mood": mood,
        "sakura_status": state.get("sakura_status", "online"),
        "color": config["color"],
        "greeting": config["greeting"],
        "emoji": config["emoji"],
        "timestamp": state.get("timestamp", ""),
    }


def _default_status() -> dict:
    """生成默认状态"""
    return _enrich_status({
        "time_period": get_time_period(),
        "mood": "安静",
        "sakura_status": "online",
    })

"""
作息守护服务 · 在线心跳追踪 + 休息模式识别
"""
import json
from datetime import datetime, timedelta
from database import get_db, dict_from_row, rows_to_dicts


# 作息阈值常量
REST_GAP_MINUTES = 60        # 静默>60分钟视为进入休息
LONG_AWAKE_HOURS = 16        # 清醒>16小时 → 提醒
CRITICAL_AWAKE_HOURS = 22    # 清醒>22小时 → 警告
REST_WINDOW_MINUTES = 120    # 视为有效休息的最短静默时长


def record_heartbeat(source: str = "backend", event_type: str = "heartbeat"):
    """记录一次活动心跳"""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO presence_events (timestamp, source, event_type)
               VALUES (datetime('now', 'localtime'), ?, ?)""",
            (source, event_type),
        )
        conn.commit()
    return {"status": "ok", "source": source, "type": event_type}


def get_today_events() -> list[dict]:
    """获取今日所有心跳事件"""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM presence_events
               WHERE date(timestamp) = date('now', 'localtime')
               ORDER BY timestamp ASC"""
        ).fetchall()
    return rows_to_dicts(rows)


def get_recent_events(limit: int = 100) -> list[dict]:
    """获取最近N条心跳事件"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM presence_events ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return rows_to_dicts(rows)


def _parse_timestamp(ts: str) -> datetime:
    """解析时间戳"""
    try:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return datetime.now()


def analyze_today_pattern() -> dict:
    """
    分析今天的作息模式。
    返回：
    - awake_hours: 预计清醒时长
    - rest_count: 检测到的休息段数
    - last_active: 最后活动时间
    - minutes_since_active: 距最后活动多少分钟
    - status: "active" | "resting" | "likely_asleep" | "offline"
    - recommendation: 建议文字
    - timeline: 简化的活动时间线（每段活动/休息）
    """
    events = get_today_events()

    if not events:
        return {
            "awake_hours": 0,
            "rest_count": 0,
            "last_active": None,
            "minutes_since_active": 0,
            "status": "offline",
            "recommendation": "今天还没探测到Sukura的活动",
            "timeline": [],
        }

    now = datetime.now()
    timestamps = [_parse_timestamp(e["timestamp"]) for e in events]

    # 取最早和最晚的时间
    first_ts = min(timestamps)
    last_ts = max(timestamps)

    # 构建时间段：将连续的事件合并为活动段
    segments = []  # [(start, end, type)]
    current_start = timestamps[0]
    current_end = timestamps[0]

    for i in range(1, len(timestamps)):
        gap = (timestamps[i] - timestamps[i - 1]).total_seconds() / 60
        if gap <= REST_GAP_MINUTES:
            # 连续活动 → 扩展当前段
            current_end = timestamps[i]
        else:
            # 出现了休息间隙 → 结束当前活动段，插入休息段
            segments.append((current_start, current_end, "active"))
            segments.append((current_end, timestamps[i], "rest"))
            current_start = timestamps[i]
            current_end = timestamps[i]

    # 最后一个段
    segments.append((current_start, current_end, "active"))

    # 统计
    active_minutes = 0
    rest_segments = 0
    for s_start, s_end, s_type in segments:
        dur = (s_end - s_start).total_seconds() / 60
        if s_type == "active":
            active_minutes += dur
        else:
            rest_segments += 1

    # 清醒时长的估算：首活动 → 当前时间
    span_hours = (now - first_ts).total_seconds() / 3600

    # 距最后活动的时间
    minutes_since = (now - last_ts).total_seconds() / 60

    # 判断状态
    if minutes_since < REST_GAP_MINUTES:
        status = "active"
    elif minutes_since < REST_WINDOW_MINUTES:
        status = "resting"
    else:
        status = "likely_asleep"

    # 建议
    if span_hours >= CRITICAL_AWAKE_HOURS:
        recommendation = "Sakura，你清醒超过22小时了。现在最需要的是睡觉，不是做事。"
    elif span_hours >= LONG_AWAKE_HOURS:
        recommendation = "清醒超过16小时了。如果没在赶deadline就去休息吧。"
    elif status == "resting" and minutes_since >= 60:
        recommendation = "似乎休息了一段时间。如果刚醒，先去喝杯水。"
    elif status == "active":
        recommendation = "在线中，一切正常。"
    else:
        recommendation = ""

    # 时间线（简化，每小时一条）
    timeline = []
    for s_start, s_end, s_type in segments:
        dur_min = round((s_end - s_start).total_seconds() / 60)
        if dur_min >= 5:  # 过滤太短的段
            timeline.append({
                "start": s_start.strftime("%H:%M"),
                "end": s_end.strftime("%H:%M"),
                "type": s_type,
                "duration_min": dur_min,
            })

    return {
        "awake_hours": round(span_hours, 1),
        "active_minutes": round(active_minutes),
        "rest_count": rest_segments,
        "last_active": last_ts.strftime("%H:%M:%S") if last_ts else None,
        "minutes_since_active": round(minutes_since),
        "status": status,
        "current_time_period": _get_time_period(now),
        "recommendation": recommendation,
        "timeline": timeline,
    }


def _get_time_period(now: datetime = None) -> str:
    """当前时段"""
    if now is None:
        now = datetime.now()
    h = now.hour
    if 5 <= h < 9:
        return "清晨"
    elif 9 <= h < 12:
        return "上午"
    elif 12 <= h < 14:
        return "中午"
    elif 14 <= h < 18:
        return "下午"
    elif 18 <= h < 22:
        return "晚上"
    elif 22 <= h < 24:
        return "深夜"
    else:
        return "凌晨"


def get_rest_settings() -> dict:
    """获取作息相关设置"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'rest_reminder_enabled'"
        ).fetchone()
        rest_reminder = dict_from_row(row)
        enabled = json.loads(rest_reminder["value"]) if rest_reminder else True
    return {
        "rest_reminder_enabled": enabled,
        "long_awake_hours": LONG_AWAKE_HOURS,
        "critical_awake_hours": CRITICAL_AWAKE_HOURS,
        "rest_gap_minutes": REST_GAP_MINUTES,
    }

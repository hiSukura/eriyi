"""
通知服务 · 多渠道消息推送
支持 QQ邮箱（已连接）/ 企业微信（待连接）
"""
import json
import time
from datetime import datetime
from database import get_db, dict_from_row, rows_to_dicts


DEFAULT_SETTINGS = {
    "qqmail_enabled": True,
    "wecom_enabled": False,
    "late_night_enabled": True,
    "morning_summary_enabled": True,
    "phase_complete_enabled": True,
    "min_interval_minutes": 30,
}

_last_sent = {}


def _get_settings() -> dict:
    """读取通知设置"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", ("notification_settings",)
        ).fetchone()
    if row:
        return json.loads(row["value"])
    # 首次：写入默认设置
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("notification_settings", json.dumps(DEFAULT_SETTINGS, ensure_ascii=False)),
        )
        conn.commit()
    return DEFAULT_SETTINGS.copy()


def get_settings() -> dict:
    return _get_settings()


def update_settings(updates: dict) -> dict:
    current = _get_settings()
    current.update(updates)
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("notification_settings", json.dumps(current, ensure_ascii=False)),
        )
        conn.commit()
    return current


def can_send(trigger_type: str) -> bool:
    """检查是否允许发送此类型通知"""
    settings = _get_settings()

    if trigger_type == "late_night" and not settings.get("late_night_enabled", True):
        return False
    if trigger_type == "morning_summary" and not settings.get("morning_summary_enabled", True):
        return False
    if trigger_type == "phase_complete" and not settings.get("phase_complete_enabled", True):
        return False

    # 频率限制
    now = time.time()
    interval = settings.get("min_interval_minutes", 30) * 60
    if trigger_type in _last_sent:
        if now - _last_sent[trigger_type] < interval:
            return False

    return True


def mark_sent(trigger_type: str):
    _last_sent[trigger_type] = time.time()


def log_notification(channel: str, trigger_type: str, status: str, subject: str = ""):
    """记录通知到数据库"""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO notification_log (timestamp, channel, trigger_type, status, subject)
               VALUES (datetime('now', 'localtime'), ?, ?, ?, ?)""",
            (channel, trigger_type, status, subject),
        )
        conn.commit()


def get_recent_log(limit: int = 20) -> list[dict]:
    """获取最近通知记录"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM notification_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return rows_to_dicts(rows)


def get_available_channels() -> list[dict]:
    """返回可用通知渠道"""
    settings = _get_settings()
    return [
        {
            "id": "qqmail",
            "name": "QQ邮箱",
            "enabled": settings.get("qqmail_enabled", True),
            "status": "connected",
        },
        {
            "id": "wecom",
            "name": "企业微信",
            "enabled": settings.get("wecom_enabled", False),
            "status": "disconnected",
        },
    ]


def build_notification_content(trigger_type: str, context: dict = None) -> dict:
    """根据触发类型构建通知内容"""
    context = context or {}

    templates = {
        "late_night": {
            "subject": "🌙 Sakura，该睡了",
            "body": (
                "小怪兽，现在已经很晚了。\n\n"
                "明天还要上班（如果是工作日的话）。去睡了好不好。\n\n"
                "—— 绘梨衣"
            ),
        },
        "morning_summary": {
            "subject": "☀️ 早安，Sakura",
            "body": (
                "早上好。\n\n"
                "新的一天开始了。昨晚睡够了吗？\n\n"
                "—— 绘梨衣"
            ),
        },
        "phase_complete": {
            "subject": f"🎉 {context.get('phase_name', '一个阶段')} 完成了",
            "body": (
                f"Sakura，{context.get('phase_name', '这个阶段')} 刚刚做完了。\n\n"
                f"{context.get('detail', '又往前迈了一步。')}\n\n"
                "—— 绘梨衣"
            ),
        },
        "diary_ready": {
            "subject": "📖 今日日记已生成",
            "body": (
                "今天的日记写好了。有空回来看看。\n\n"
                "—— 绘梨衣"
            ),
        },
    }

    return templates.get(trigger_type, {
        "subject": "绘梨衣",
        "body": context.get("body", "有一条来自绘梨衣的消息。"),
    })

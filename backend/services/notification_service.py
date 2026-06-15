"""
通知服务 · 多渠道消息推送
支持 QQ邮箱（环境变量配置）/ 企业微信（待连接）

环境变量:
  QQMAIL_USER    — QQ邮箱地址（如 eriyi@qq.com）
  QQMAIL_PASS    — SMTP授权码（非登录密码）
  QQMAIL_TO      — 收件人邮箱（Sukura的邮箱）
  留空则不实际发送，仅记录日志。
"""
import json
import os
import smtplib
import time
from email.mime.text import MIMEText
from email.header import Header
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
    """返回可用通知渠道（动态检测 QQ邮箱 配置状态）"""
    settings = _get_settings()
    return [
        {
            "id": "qqmail",
            "name": "QQ邮箱",
            "enabled": settings.get("qqmail_enabled", True),
            "status": "connected" if is_qqmail_ready() else "not_configured",
            "user": _QQMAIL_USER or "",
            "to": _QQMAIL_TO or "",
        },
        {
            "id": "wecom",
            "name": "企业微信",
            "enabled": settings.get("wecom_enabled", False),
            "status": "disconnected",
        },
    ]


# ═══════ QQ邮箱发送器 ═══════
_QQMAIL_USER = os.environ.get("QQMAIL_USER", "")
_QQMAIL_PASS = os.environ.get("QQMAIL_PASS", "")
_QQMAIL_TO = os.environ.get("QQMAIL_TO", "")
_QQMAIL_HOST = "smtp.qq.com"
_QQMAIL_PORT = 465


def is_qqmail_ready() -> bool:
    """检查 QQ邮箱 配置是否完整"""
    return bool(_QQMAIL_USER and _QQMAIL_PASS and _QQMAIL_TO)


def send_qqmail(subject: str, body: str) -> bool:
    """通过 QQ邮箱 SMTP 发送邮件"""
    if not is_qqmail_ready():
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = _QQMAIL_USER
        msg["To"] = _QQMAIL_TO

        with smtplib.SMTP_SSL(_QQMAIL_HOST, _QQMAIL_PORT, timeout=10) as s:
            s.login(_QQMAIL_USER, _QQMAIL_PASS)
            s.send_message(msg)
        return True
    except Exception as e:
        print(f"  [QQMail] 发送失败: {e}")
        return False


def send_notification(trigger_type: str, context: dict = None) -> dict:
    """发送通知（尝试真实发送，失败则降级为日志）"""
    if not can_send(trigger_type):
        return {"success": False, "reason": "通知被频率限制或已禁用"}

    content = build_notification_content(trigger_type, context)
    channel = "qqmail"
    sent = False

    if is_qqmail_ready():
        sent = send_qqmail(content["subject"], content["body"])
        status = "sent" if sent else "failed"
    else:
        status = "pending"

    mark_sent(trigger_type)
    log_notification(channel, trigger_type, status, content["subject"])

    return {
        "success": sent if is_qqmail_ready() else None,
        "channel": channel,
        "trigger_type": trigger_type,
        "subject": content["subject"],
        "body": content["body"],
        "status": status,
        "note": "" if sent else (
            "QQ邮箱未配置（设置 QQMAIL_USER / QQMAIL_PASS / QQMAIL_TO 环境变量）"
            if not is_qqmail_ready() else "发送失败，请检查 SMTP 配置"
        ),
    }


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

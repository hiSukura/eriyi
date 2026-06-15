"""
通知路由 · 通知设置 + 发送 + 日志
"""
from fastapi import APIRouter
from pydantic import BaseModel
from services.notification_service import (
    get_settings,
    update_settings,
    get_recent_log,
    get_available_channels,
    send_notification,
)

router = APIRouter(prefix="/api/notification", tags=["notification"])


class SettingsUpdate(BaseModel):
    qqmail_enabled: bool | None = None
    wecom_enabled: bool | None = None
    late_night_enabled: bool | None = None
    morning_summary_enabled: bool | None = None
    phase_complete_enabled: bool | None = None
    min_interval_minutes: int | None = None


class SendRequest(BaseModel):
    trigger_type: str
    channel: str = "qqmail"


@router.get("/settings")
def api_get_settings():
    """获取通知设置"""
    return get_settings()


@router.post("/settings")
def api_update_settings(body: SettingsUpdate):
    """更新通知设置"""
    updates = {k: v for k, v in body.dict().items() if v is not None}
    return update_settings(updates)


@router.get("/channels")
def api_get_channels():
    """获取可用通知渠道"""
    return get_available_channels()


@router.get("/log")
def api_get_log(limit: int = 20):
    """获取最近通知日志"""
    return get_recent_log(limit)


@router.post("/send")
def api_send(body: SendRequest):
    """触发通知（QQ邮箱已配置则真实发送，否则仅记录日志）"""
    return send_notification(body.trigger_type)

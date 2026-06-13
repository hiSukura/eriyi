"""
作息守护 API 路由 · 在线心跳 + 休息模式查询
"""
from fastapi import APIRouter

from services import presence_service

router = APIRouter(prefix="/api/presence", tags=["作息守护"])


@router.post("/heartbeat")
async def heartbeat(source: str = "backend", event_type: str = "heartbeat"):
    """记录一次活动心跳（桌面客户端/仪表盘定期调用）"""
    return presence_service.record_heartbeat(source=source, event_type=event_type)


@router.get("/today")
async def today_pattern():
    """获取今日作息模式分析"""
    return presence_service.analyze_today_pattern()


@router.get("/events")
async def recent_events(limit: int = 50):
    """获取最近心跳事件"""
    events = presence_service.get_recent_events(limit=limit)
    return {"count": len(events), "events": events}


@router.get("/settings")
async def rest_settings():
    """获取作息相关设置"""
    return presence_service.get_rest_settings()

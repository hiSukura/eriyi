"""
状态 API 路由
"""
from fastapi import APIRouter

from services import state_service

router = APIRouter(prefix="/api/status", tags=["状态"])


@router.get("")
async def current_status():
    """获取当前绘梨衣状态"""
    return state_service.get_current_status()


@router.post("")
async def update_status(data: dict):
    """更新绘梨衣状态"""
    return state_service.update_status(data)


@router.get("/history")
async def status_history(limit: int = 24):
    """获取状态历史"""
    return state_service.get_status_history(limit=limit)


@router.get("/time-period")
async def current_time_period():
    """获取当前时段信息"""
    return {
        "time_period": state_service.get_time_period(),
    }

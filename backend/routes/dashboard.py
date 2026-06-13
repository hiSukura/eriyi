"""
仪表盘 API 路由 —— 聚合首页所需的所有数据
"""
from fastapi import APIRouter

from services import state_service, diary_service, memory_service, voice_service

router = APIRouter(prefix="/api/dashboard", tags=["仪表盘"])


@router.get("")
async def dashboard_data():
    """返回仪表盘首页所需的聚合数据"""
    # 当前状态
    status = state_service.get_current_status()

    # 今日日记
    today = diary_service.get_today_diary()

    # 最近日记列表（前7篇）
    recent_diaries = diary_service.get_all_diaries(limit=7)

    # 最近记忆
    recent_memories = memory_service.get_recent_memories(limit=8)

    # 记忆统计
    mem_stats = memory_service.get_memory_stats()

    # 语音分类
    voice_categories = voice_service.get_voice_categories()

    # 整体统计
    stats = {
        "diary_count": diary_service.get_diary_count(),
        "voice_count": sum(voice_categories.values()) if voice_categories else 0,
        "memory_count": mem_stats["total"],
        "milestone_count": mem_stats.get("milestone_count", 0),
    }

    return {
        "status": status,
        "today_diary": today,
        "recent_diaries": recent_diaries,
        "recent_memories": recent_memories,
        "voice_categories": voice_categories,
        "stats": stats,
    }

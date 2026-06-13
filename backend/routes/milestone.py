"""
里程碑路由 · 自动检测 + 查询
"""
from fastapi import APIRouter
from services.milestone_service import (
    sync_milestones,
    get_all_milestones,
    get_recent_milestones,
    get_milestone_count,
)

router = APIRouter(prefix="/api/milestones", tags=["milestones"])


@router.post("/detect")
def api_detect():
    """扫描并记录新里程碑"""
    return sync_milestones()


@router.post("/sync")
def api_sync():
    """同步里程碑"""
    return sync_milestones()


@router.get("")
def api_list(limit: int = 30):
    """获取里程碑列表"""
    return get_all_milestones(limit)


@router.get("/recent")
def api_recent(limit: int = 5):
    """最近里程碑"""
    return get_recent_milestones(limit)


@router.get("/stats")
def api_stats():
    """里程碑统计"""
    return {"total": get_milestone_count()}

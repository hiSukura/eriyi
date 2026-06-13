"""
记忆 API 路由
"""
from fastapi import APIRouter, HTTPException, Query

from services import memory_service

router = APIRouter(prefix="/api/memories", tags=["记忆"])


@router.get("")
async def list_memories(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    category: str = Query(default=None),
    perspective: str = Query(default=None),
):
    """获取记忆事件列表"""
    memories = memory_service.get_memories(
        limit=limit, offset=offset, category=category, perspective=perspective
    )
    return {"count": len(memories), "items": memories}


@router.get("/stats")
async def memory_stats():
    """获取记忆统计信息"""
    return memory_service.get_memory_stats()


@router.get("/recent")
async def recent_memories(limit: int = Query(default=10, le=50)):
    """获取最近的记忆"""
    return memory_service.get_recent_memories(limit=limit)


@router.post("")
async def add_memory(data: dict):
    """添加一条记忆事件"""
    if "content" not in data:
        raise HTTPException(status_code=400, detail="缺少 content 字段")
    if "date" not in data:
        from datetime import datetime
        data["date"] = datetime.now().strftime("%Y-%m-%d")
    return memory_service.add_memory(data)

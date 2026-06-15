"""
语义搜索 API 路由
"""
from fastapi import APIRouter, Query

from services import embedding_service

router = APIRouter(prefix="/api/search", tags=["搜索"])


@router.get("")
async def search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    type: str | None = Query(None, alias="type", description="限制范围: diary/memory/milestone"),
    top_k: int = Query(5, ge=1, le=50),
    min_score: float = Query(0.3, ge=0.0, le=1.0),
):
    """语义搜索日记/记忆/里程碑"""
    if not embedding_service.is_available():
        return {"results": [], "error": "嵌入模型未加载"}

    results = embedding_service.semantic_search(
        query=q,
        entity_type=type,
        top_k=top_k,
        min_score=min_score,
    )
    return {"query": q, "count": len(results), "results": results}


@router.get("/stats")
async def search_stats():
    """嵌入服务状态"""
    return embedding_service.get_stats()


@router.post("/rebuild")
async def rebuild_embeddings(force: bool = False):
    """重新编码所有数据"""
    stats = embedding_service.rebuild_all(force=force)
    return {"message": "重建完成", "stats": stats}

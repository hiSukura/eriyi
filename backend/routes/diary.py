"""
日记 API 路由
"""
from fastapi import APIRouter, HTTPException, Query

from services import diary_service

router = APIRouter(prefix="/api/diaries", tags=["日记"])


@router.get("")
async def list_diaries(
    limit: int = Query(default=30, le=100),
    offset: int = Query(default=0, ge=0)
):
    """获取日记列表"""
    diaries = diary_service.get_all_diaries(limit=limit, offset=offset)
    return {
        "count": len(diaries),
        "total": diary_service.get_diary_count(),
        "items": diaries,
    }


@router.get("/today")
async def today_diary():
    """获取今日日记"""
    diary = diary_service.get_today_diary()
    if not diary:
        return {"exists": False, "diary": None}
    return {"exists": True, "diary": diary}


@router.get("/{date}")
async def get_diary(date: str):
    """获取指定日期的日记"""
    diary = diary_service.get_diary_by_date(date)
    if not diary:
        raise HTTPException(status_code=404, detail=f"日记 {date} 不存在")
    return diary


@router.post("")
async def create_or_update_diary(data: dict):
    """创建或更新日记"""
    if "date" not in data:
        raise HTTPException(status_code=400, detail="缺少 date 字段")
    diary = diary_service.upsert_diary(data)
    return diary


@router.delete("/{date}")
async def delete_diary(date: str):
    """删除日记"""
    success = diary_service.delete_diary(date)
    if not success:
        raise HTTPException(status_code=404, detail=f"日记 {date} 不存在")
    return {"message": f"日记 {date} 已删除"}


@router.post("/sync")
async def sync_diaries():
    """从文件系统同步日记到数据库"""
    count = diary_service.sync_diary_files_to_db()
    return {"message": f"已同步 {count} 篇日记"}

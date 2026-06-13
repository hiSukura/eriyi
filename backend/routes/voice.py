"""
语音 API 路由
"""
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from services import voice_service

router = APIRouter(prefix="/api/voices", tags=["语音"])


@router.get("")
async def list_voices():
    """获取语音文件列表"""
    voices = voice_service.get_all_voices()
    categories = voice_service.get_voice_categories()
    return {
        "count": len(voices),
        "categories": categories,
        "items": voices,
    }


@router.get("/{filename}")
async def get_voice_info(filename: str):
    """获取语音文件信息"""
    voice = voice_service.get_voice_by_filename(filename)
    if not voice:
        raise HTTPException(status_code=404, detail=f"语音文件 {filename} 不存在")
    return voice


@router.get("/{filename}/stream")
async def stream_voice(filename: str):
    """流式传输语音文件"""
    path = voice_service.get_voice_path(filename)
    if not path:
        raise HTTPException(status_code=404, detail=f"语音文件 {filename} 不存在")

    # 获取文件大小用于 Content-Length
    file_size = path.stat().st_size

    return FileResponse(
        path=str(path),
        media_type="audio/mpeg",
        headers={
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=86400",
        }
    )


@router.post("/sync")
async def sync_voices():
    """从文件系统同步语音到数据库"""
    count = voice_service.sync_voice_files_to_db()
    return {"message": f"已同步 {count} 个语音文件"}

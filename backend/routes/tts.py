"""
TTS 路由 · Phase 5.4
当前使用 edge-tts，GPT-SoVITS 训练完成后切换
"""
import subprocess
import tempfile
import os
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/tts", tags=["tts"])

VOICE_CLONE_DIR = Path(__file__).parent.parent.parent / "voice_clone"
OUTPUT_DIR = VOICE_CLONE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROXY = "http://127.0.0.1:7897"


class TTSRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: str = "-15%"
    pitch: str = "+2Hz"


@router.get("/status")
def api_status():
    """TTS 状态 — 当前用什么引擎"""
    model_path = VOICE_CLONE_DIR / "model" / "s2G2333k.pth"
    engine = "gpt-sovits" if model_path.exists() else "edge-tts"
    return {
        "engine": engine,
        "model_ready": model_path.exists(),
        "available_voices": "zh-CN-XiaoxiaoNeural (default)" if engine == "edge-tts" else "eriyi",
    }


@router.post("/generate")
def api_generate(body: TTSRequest):
    """生成 TTS 语音"""
    import hashlib
    key = hashlib.md5(f"{body.text}{body.voice}{body.rate}{body.pitch}".encode()).hexdigest()[:12]
    output_path = OUTPUT_DIR / f"tts_{key}.mp3"

    if output_path.exists():
        return {"status": "cached", "file": f"tts_{key}.mp3", "path": str(output_path)}

    try:
        import edge_tts
        import asyncio

        async def _gen():
            communicate = edge_tts.Communicate(
                text=body.text,
                voice=body.voice,
                rate=body.rate,
                pitch=body.pitch,
                proxy=PROXY,
            )
            await communicate.save(str(output_path))

        asyncio.run(_gen())

        if output_path.exists():
            from datetime import datetime
            return {
                "status": "ok",
                "file": f"tts_{key}.mp3",
                "path": str(output_path),
                "size_kb": round(output_path.stat().st_size / 1024, 1),
            }
    except ImportError:
        return {"status": "error", "message": "edge-tts not installed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/play/{filename}")
def api_play(filename: str):
    """播放 TTS 文件"""
    filepath = OUTPUT_DIR / filename
    if filepath.exists():
        return FileResponse(str(filepath), media_type="audio/mpeg")
    return {"status": "error", "message": "file not found"}

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
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "tts_cache"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROXY = "http://127.0.0.1:7897"

# 设置环境变量让 edge-tts 底层 aiohttp 走代理
import os
os.environ["HTTP_PROXY"] = PROXY
os.environ["HTTPS_PROXY"] = PROXY


class TTSRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: str = "-15%"
    pitch: str = "+2Hz"


@router.get("/status")
def api_status():
    """TTS 状态 — 当前用什么引擎"""
    from services.tts_service import get_voice_model, VOICE_MODEL_PATH
    model = get_voice_model()
    engine = "eriyi-voice-ae" if VOICE_MODEL_PATH.exists() else "edge-tts"
    params = sum(p.numel() for p in model.parameters()) if model else 0
    return {
        "engine": engine,
        "model_ready": VOICE_MODEL_PATH.exists(),
        "model_params": params,
        "note": f"VoiceAE {params//1000}K参数 · CPU训练",
    }


@router.post("/generate")
def api_generate(body: TTSRequest):
    """生成 TTS 语音 · 默认使用绘梨衣声音模型"""
    import hashlib
    from services.tts_service import apply_eriyi_voice

    key = hashlib.md5(f"{body.text}{body.voice}{body.rate}{body.pitch}".encode()).hexdigest()[:12]
    tmp_path = OUTPUT_DIR / f"tmp_{key}.mp3"
    out_path = OUTPUT_DIR / f"tts_{key}.wav"

    if out_path.exists():
        return {"status": "cached", "file": out_path.name, "path": str(out_path), "engine": "eriyi-voice-ae"}

    # Step 1: edge-tts 文本→语音
    try:
        # 强制设置代理环境变量
        import os
        os.environ["http_proxy"] = PROXY
        os.environ["https_proxy"] = PROXY
        os.environ["HTTP_PROXY"] = PROXY
        os.environ["HTTPS_PROXY"] = PROXY
        
        import edge_tts, asyncio
        async def _gen():
            c = edge_tts.Communicate(text=body.text, voice=body.voice, rate=body.rate,
                                     pitch=body.pitch, proxy=PROXY)
            await c.save(str(tmp_path))
        asyncio.run(_gen())
    except Exception as e:
        return {"status": "error", "message": f"edge-tts: {e}"}

    if not tmp_path.exists():
        return {"status": "error", "message": "TTS生成失败"}

    # Step 2: 绘梨衣声音着色
    ok = apply_eriyi_voice(tmp_path, out_path)
    tmp_path.unlink(missing_ok=True)

    if ok:
        return {
            "status": "ok",
            "engine": "eriyi-voice-ae",
            "file": out_path.name,
            "path": str(out_path),
            "size_kb": round(out_path.stat().st_size / 1024, 1),
        }
    return {"status": "error", "message": "VoiceAE处理失败"}


@router.get("/play/{filename}")
def api_play(filename: str):
    """播放 TTS 文件"""
    filepath = OUTPUT_DIR / filename
    if filepath.exists():
        return FileResponse(str(filepath), media_type="audio/mpeg")
    return {"status": "error", "message": "file not found"}


# ── 绘梨衣声音模型端点 ──
@router.post("/generate/eriyi")
def api_generate_eriyi(body: TTSRequest):
    """用绘梨衣声音模型生成语音（edge-tts → VoiceAE着色）"""
    import hashlib
    from services.tts_service import apply_eriyi_voice

    key = hashlib.md5(f"eriyi_{body.text}".encode()).hexdigest()[:12]
    tmp_path = OUTPUT_DIR / f"tmp_{key}.mp3"
    out_path = OUTPUT_DIR / f"eriyi_{key}.wav"

    if out_path.exists():
        return {"status": "cached", "file": out_path.name, "path": str(out_path)}

    # Step 1: edge-tts 生成基础语音
    try:
        import os
        os.environ["http_proxy"] = os.environ["https_proxy"] = PROXY
        import edge_tts, asyncio
        async def _gen():
            c = edge_tts.Communicate(text=body.text, voice="zh-CN-XiaoxiaoNeural",
                                     rate="-15%", pitch="+2Hz", proxy=PROXY)
            await c.save(str(tmp_path))
        asyncio.run(_gen())
    except Exception as e:
        return {"status": "error", "message": f"edge-tts failed: {e}"}

    if not tmp_path.exists():
        return {"status": "error", "message": "TTS generation failed"}

    # Step 2: 绘梨衣声音着色
    ok = apply_eriyi_voice(tmp_path, out_path)
    tmp_path.unlink(missing_ok=True)

    if ok:
        return {
            "status": "ok",
            "engine": "eriyi-voice-ae",
            "file": out_path.name,
            "path": str(out_path),
            "size_kb": round(out_path.stat().st_size / 1024, 1),
            "note": "CPUtrained model + edge-tts base",
        }
    return {"status": "error", "message": "VoiceAE processing failed"}

"""
TTS 路由 · Phase 5.4
edge-tts → VoiceAE 绘梨衣声音着色
"""
import hashlib
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/tts", tags=["tts"])

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "tts_cache"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class TTSRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: str = "-15%"
    pitch: str = "+2Hz"


def _generate_core(text: str, out_path: Path,
                   voice: str, rate: str, pitch: str,
                   tmp_suffix: str = "tmp") -> dict:
    """核心管线：edge-tts → VoiceAE 着色 → 返回结果"""
    from services.tts_service import run_edge_tts_sync, apply_eriyi_voice

    key = hashlib.md5(f"{text}{voice}{rate}{pitch}".encode()).hexdigest()[:12]
    tmp_path = OUTPUT_DIR / f"{tmp_suffix}_{key}.mp3"

    if out_path.exists():
        return {"status": "cached", "file": out_path.name, "path": str(out_path), "engine": "eriyi-voice-ae"}

    ok = run_edge_tts_sync(text, tmp_path, voice=voice, rate=rate, pitch=pitch)
    if not ok or not tmp_path.exists():
        return {"status": "error", "message": "edge-tts 合成失败"}

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
    return {"status": "error", "message": "VoiceAE 着色失败"}


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
    """生成 TTS 语音 · edge-tts → VoiceAE 绘梨衣音色着染"""
    key = hashlib.md5(f"{body.text}{body.voice}{body.rate}{body.pitch}".encode()).hexdigest()[:12]
    out_path = OUTPUT_DIR / f"tts_{key}.wav"
    return _generate_core(body.text, out_path, body.voice, body.rate, body.pitch)


@router.post("/generate/eriyi")
def api_generate_eriyi(body: TTSRequest):
    """用绘梨衣声音模型生成语音（固定 edge-tts 参数 + VoiceAE 着色）"""
    key = hashlib.md5(f"eriyi_{body.text}".encode()).hexdigest()[:12]
    out_path = OUTPUT_DIR / f"eriyi_{key}.wav"
    return _generate_core(
        body.text, out_path,
        voice="zh-CN-XiaoxiaoNeural", rate="-15%", pitch="+2Hz",
    )


@router.get("/play/{filename}")
def api_play(filename: str):
    """播放 TTS 文件"""
    filepath = OUTPUT_DIR / filename
    if filepath.exists():
        return FileResponse(str(filepath), media_type="audio/mpeg")
    return {"status": "error", "message": "file not found"}

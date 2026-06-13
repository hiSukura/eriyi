"""
TTS 引擎服务 · edge-tts 回退 + GPT-SoVITS 预留
当前用 edge-tts (XiaoXiao) 提供即时TTS，训练完成后切换到克隆声音。
"""
import asyncio
import subprocess
import sys
import hashlib
from pathlib import Path

from config import VOICE_CLONE_DIR

TTS_CACHE_DIR = VOICE_CLONE_DIR / "output"
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# edge-tts 配置
EDGE_VOICE = "zh-CN-XiaoxiaoNeural"
EDGE_RATE = "-15%"
EDGE_PITCH = "+2Hz"
PROXY = "http://127.0.0.1:7897"


async def generate_edge_tts(text: str, output_path: Path) -> bool:
    """使用 edge-tts 生成语音 MP3"""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(
            text=text, voice=EDGE_VOICE,
            rate=EDGE_RATE, pitch=EDGE_PITCH,
            proxy=PROXY,
        )
        await communicate.save(str(output_path))
        return output_path.exists()
    except ImportError:
        print("  [TTS] edge-tts 未安装，尝试 pip install edge-tts")
        return False
    except Exception as e:
        print(f"  [TTS] edge-tts 错误: {e}")
        return False


def generate_tts_sync(text: str, output_path: Path = None) -> dict:
    """同步生成 TTS（在 uvicorn 外使用）"""
    if output_path is None:
        text_hash = hashlib.md5(text.encode()).hexdigest()[:10]
        output_path = TTS_CACHE_DIR / f"tts_{text_hash}.mp3"

    if output_path.exists():
        return _cached_result(text, output_path)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ok = loop.run_until_complete(generate_edge_tts(text, output_path))
        loop.close()
    except Exception as e:
        print(f"  [TTS] 同步生成失败: {e}")
        ok = False

    return _make_result(text, output_path, ok)


async def generate_tts_async(text: str, output_path: Path = None) -> dict:
    """异步生成 TTS（在 FastAPI 内使用）"""
    if output_path is None:
        text_hash = hashlib.md5(text.encode()).hexdigest()[:10]
        output_path = TTS_CACHE_DIR / f"tts_{text_hash}.mp3"

    if output_path.exists():
        return _cached_result(text, output_path)

    try:
        ok = await generate_edge_tts(text, output_path)
    except Exception as e:
        print(f"  [TTS] 异步生成失败: {e}")
        ok = False

    return _make_result(text, output_path, ok)


def _cached_result(text: str, path: Path) -> dict:
    return {
        "status": "cached",
        "text": text,
        "file": path.name,
        "path": str(path),
        "size_kb": round(path.stat().st_size / 1024, 1),
    }


def _make_result(text: str, path: Path, ok: bool) -> dict:
    if ok:
        return _cached_result(text, path)
    return {"status": "failed", "text": text, "error": "TTS生成失败"}


def diary_to_plaintext(md_text: str) -> str:
    """Markdown → 纯朗读文本"""
    import re
    lines = []
    for line in md_text.split("\n"):
        line = line.strip()
        if not line or line == "---":
            continue
        line = re.sub(r"^#+\s+", "", line)
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        line = re.sub(r"\*(.+?)\*", r"\1", line)
        line = line.replace("🔴", "").replace("*", "")
        if line:
            lines.append(line)
    return "\n".join(lines)

"""
TTS 引擎服务 · edge-tts + CPU训练的绘梨衣声音模型
"""
import asyncio
import hashlib
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import soundfile as sf

from config import BACKEND_DIR

TTS_CACHE_DIR = BACKEND_DIR / "data" / "tts_cache"
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# edge-tts 配置
EDGE_VOICE = "zh-CN-XiaoxiaoNeural"
EDGE_RATE = "-15%"
EDGE_PITCH = "+2Hz"
PROXY = "http://127.0.0.1:7897"

# 绘梨衣声音模型路径（独立于gitignored GPT-SoVITS目录）
VOICE_MODEL_DIR = BACKEND_DIR / "models"
VOICE_MODEL_DIR.mkdir(parents=True, exist_ok=True)
VOICE_MODEL_PATH = VOICE_MODEL_DIR / "eriyi_voice.pth"
SR = 22050
N_FFT = 512
HOP = 256
N_FREQ = N_FFT // 2 + 1


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


# ═══════ 绘梨衣声音模型 V1（已训练权重兼容）═══════
class _ResBlock(nn.Module):
    def __init__(self, ch):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(ch, ch, 3, padding=1), nn.BatchNorm1d(ch), nn.ReLU(),
            nn.Conv1d(ch, ch, 3, padding=1), nn.BatchNorm1d(ch),
        )
    def forward(self, x):
        return torch.relu(x + self.conv(x))


class VoiceAE(nn.Module):
    """
    VoiceAE V1 — 3级残差编解码器 ~440K参数
    编码: 257→256→128→64→32  (3次下采样)
    解码: 64→64→128→256→257  (3次上采样)
    """
    def __init__(self):
        super().__init__()
        self.enc_in = nn.Conv1d(N_FREQ, 256, 7, padding=3)
        self.enc_res1 = _ResBlock(256)
        self.enc_down1 = nn.Conv1d(256, 128, 4, stride=2, padding=1)
        self.enc_res2a = _ResBlock(128)
        self.enc_res2b = _ResBlock(128)
        self.enc_down2 = nn.Conv1d(128, 64, 4, stride=2, padding=1)
        self.enc_res3a = _ResBlock(64)
        self.enc_res3b = _ResBlock(64)
        self.enc_down3 = nn.Conv1d(64, 32, 4, stride=2, padding=1)
        self.enc_res4 = _ResBlock(32)
        self.latent = nn.Linear(32, 64)
        self.dec_up1 = nn.ConvTranspose1d(64, 64, 4, stride=2, padding=1)
        self.dec_res1a = _ResBlock(64)
        self.dec_res1b = _ResBlock(64)
        self.dec_up2 = nn.ConvTranspose1d(64, 128, 4, stride=2, padding=1)
        self.dec_res2a = _ResBlock(128)
        self.dec_res2b = _ResBlock(128)
        self.dec_up3 = nn.ConvTranspose1d(128, 256, 4, stride=2, padding=1)
        self.dec_res3 = _ResBlock(256)
        self.dec_out = nn.Conv1d(256, N_FREQ, 7, padding=3)

    def forward(self, x):
        b, f, t_in = x.shape
        pad = (8 - t_in % 8) % 8
        if pad:
            x = torch.nn.functional.pad(x, (0, pad))
        h = torch.relu(self.enc_in(x))
        h = self.enc_res1(h)
        h = torch.relu(self.enc_down1(h))
        h = self.enc_res2a(h)
        h = self.enc_res2b(h)
        h = torch.relu(self.enc_down2(h))
        h = self.enc_res3a(h)
        h = self.enc_res3b(h)
        h = torch.relu(self.enc_down3(h))
        h = self.enc_res4(h)
        z = h.mean(dim=2)
        z = self.latent(z)
        t = h.shape[2]
        z = z.unsqueeze(-1).repeat(1, 1, t)
        h = torch.relu(self.dec_up1(z))
        h = self.dec_res1a(h)
        h = self.dec_res1b(h)
        h = torch.relu(self.dec_up2(h))
        h = self.dec_res2a(h)
        h = self.dec_res2b(h)
        h = torch.relu(self.dec_up3(h))
        h = self.dec_res3(h)
        out = self.dec_out(h)
        return out[:, :, :t_in]


_voice_model = None


def get_voice_model() -> VoiceAE | None:
    """加载绘梨衣声音模型（单例）"""
    global _voice_model
    if _voice_model is None and VOICE_MODEL_PATH.exists():
        _voice_model = VoiceAE()
        _voice_model.load_state_dict(torch.load(VOICE_MODEL_PATH, map_location="cpu", weights_only=True))
        _voice_model.eval()
    return _voice_model


def apply_eriyi_voice(input_wav_path: Path, output_wav_path: Path) -> bool:
    """用绘梨衣的声学模型处理音频，赋予绘梨衣的音色特征"""
    try:
        model = get_voice_model()
        if model is None:
            return False

        import librosa
        y, _ = librosa.load(str(input_wav_path), sr=SR)
        y_tensor = torch.from_numpy(y).float()

        spec = torch.stft(y_tensor, n_fft=N_FFT, hop_length=HOP,
                          window=torch.hann_window(N_FFT), return_complex=True)
        mag = torch.log(torch.clamp(spec.abs() + 1e-6, min=1e-6))
        original_phase = spec.angle()
        mag_input = mag.unsqueeze(0)

        with torch.no_grad():
            gen_mag = model(mag_input).squeeze(0)

        # 高质量混合：模型频谱80% + 原始频谱20% (保持清晰度)
        gen_linear = torch.exp(gen_mag) - 1e-6
        orig_linear = torch.exp(mag) - 1e-6
        blended_mag = 0.8 * gen_linear + 0.2 * orig_linear

        # 用原始相位（不是随机！）保证语音清晰
        spec_complex = blended_mag * torch.exp(1j * original_phase)

        # 迭代Griffin-Lim微调
        window = torch.hann_window(N_FFT)
        for _ in range(10):
            wav_est = torch.istft(spec_complex, n_fft=N_FFT, hop_length=HOP,
                                  window=window, length=len(y_tensor))
            spec_est = torch.stft(wav_est, n_fft=N_FFT, hop_length=HOP,
                                 window=window, return_complex=True)
            spec_complex = blended_mag * torch.exp(1j * spec_est.angle())

        wav = torch.istft(spec_complex, n_fft=N_FFT, hop_length=HOP,
                          window=window, length=len(y_tensor))
        sf.write(str(output_wav_path), wav.numpy(), SR)
        return True
    except Exception as e:
        print(f"  [VoiceAE] 处理失败: {e}")
        return False

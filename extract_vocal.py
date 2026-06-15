"""
提取念白人声 + 按句子切割 — 绘梨衣语音素材预处理工具

功能:
  1. 从歌曲中提取念白部分（人声增强）
  2. 基于能量检测按句子切分，输出独立短音频片段
  3. 生成 sentence_meta.json 记录每句的起止时间

依赖: miniaudio, numpy, scipy
用法: python extract_vocal.py
"""

import json
import os
import sys
from pathlib import Path

import miniaudio
import numpy as np
from scipy import signal
from scipy.io import wavfile

# ── 路径配置 ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
SONG_PATH = PROJECT_ROOT / "语音" / "最后的旅行_参考音频.mp3"
OUT_DIR = PROJECT_ROOT / "语音" / "念白_分句"
NARRATION_WAV = OUT_DIR / "念白_完整.wav"
SENTENCE_DIR = OUT_DIR / "sentences"
META_PATH = OUT_DIR / "sentence_meta.json"

# ── 音频参数 ─────────────────────────────────────────────
NARRATION_START_SEC = 0.0     # 念白开始时间
NARRATION_END_SEC = 38.0      # 念白结束时间（留余量）

# ── 人声增强参数 ─────────────────────────────────────────
BANDPASS_LOW = 100            # 高通截止 Hz（女声基频以上）
BANDPASS_HIGH = 8000           # 低通截止 Hz（保留齿音/气息）
BUTTER_ORDER = 4
COMPRESS_THRESHOLD = 0.15     # 压缩阈值（相对峰值）
COMPRESS_RATIO = 0.7          # 压缩比

# ── 分句参数 ─────────────────────────────────────────────
SILENCE_THRESHOLD_RATIO = 0.02    # 低于峰值 2% 视为静音
MIN_SILENCE_MS = 300              # 句间静音最短时长
MIN_SENTENCE_MS = 400             # 最短句子（过滤杂音）
PAD_MS = 50                       # 首尾微留白（避免切太紧）


def load_audio(path: Path):
    """加载 MP3，返回 (samples_mono_f32, sample_rate)
    使用 raw bytes + miniaudio.decode() 解码，避免中文路径兼容问题。
    """
    raw = path.read_bytes()

    # 解码为 float32（不指定 nchannels/sample_rate，让 miniaudio 自动检测）
    decoded = miniaudio.decode(
        raw,
        output_format=miniaudio.SampleFormat.FLOAT32,
    )
    samples = np.array(decoded.samples, dtype=np.float32)
    nch = decoded.nchannels
    sr = decoded.sample_rate

    if nch == 1:
        mono = samples
    else:
        mono = samples.reshape(-1, nch)[:, 0].copy()

    return mono, sr


def enhance_vocal(mono: np.ndarray, sr: int) -> np.ndarray:
    """人声增强：带通滤波 + 软压缩 + 归一化"""
    nyq = sr / 2
    b, a = signal.butter(BUTTER_ORDER, [BANDPASS_LOW / nyq, BANDPASS_HIGH / nyq], btype="band")
    filtered = signal.filtfilt(b, a, mono)

    # 软压缩
    threshold = COMPRESS_THRESHOLD
    ratio = COMPRESS_RATIO
    mask = np.abs(filtered) > threshold
    compressed = filtered.copy()
    compressed[mask] = np.sign(filtered[mask]) * (
        threshold + (np.abs(filtered[mask]) - threshold) * ratio
    )

    # 归一化
    peak = np.max(np.abs(compressed))
    if peak > 0:
        compressed = compressed / peak * 0.95

    return compressed


def find_sentence_boundaries(samples: np.ndarray, sr: int) -> list[tuple[int, int]]:
    """
    基于能量检测的句子边界识别。
    返回 [(start_sample, end_sample), ...] 列表。
    """
    # 短时能量（每 10ms 一帧）
    frame_len = int(0.01 * sr)  # 10ms
    n_frames = len(samples) // frame_len

    energies = np.array([
        np.sqrt(np.mean(samples[i * frame_len : (i + 1) * frame_len] ** 2))
        for i in range(n_frames)
    ])

    # 动态阈值
    peak_energy = np.max(energies) if np.max(energies) > 0 else 1.0
    silence_thresh = SILENCE_THRESHOLD_RATIO * peak_energy

    # 帧级 VAD
    is_speech = energies > silence_thresh

    # 合并短间隔（句内停顿容限: 200ms）
    min_speech_frames = max(1, int(MIN_SENTENCE_MS / 10))
    min_silence_frames = max(1, int(MIN_SILENCE_MS / 10))
    merge_gap_frames = max(1, int(200 / 10))  # 句内可容忍的短暂停顿

    # 找连续语音段
    segments = []
    in_speech = False
    seg_start = 0
    silence_count = 0

    for i in range(len(is_speech)):
        if is_speech[i]:
            if not in_speech:
                # 检查是否和前一段的间隔足够大
                if segments and (i - segments[-1][1]) < min_silence_frames:
                    # 间隔太短，合并到上一段
                    segments[-1] = (segments[-1][0], i + 1)
                else:
                    seg_start = i
                in_speech = True
                silence_count = 0
            else:
                silence_count = 0
        else:
            if in_speech:
                silence_count += 1
                if silence_count >= min_silence_frames:
                    # 静音够长，结束当前段
                    seg_end = i - silence_count + 1
                    if seg_end - seg_start >= min_speech_frames:
                        segments.append((seg_start, seg_end))
                    in_speech = False
                    silence_count = 0
            # 不在语音中也累计 silence_count 用于后面的合并判断
    # 收尾
    if in_speech:
        seg_end = len(is_speech)
        if seg_end - seg_start >= min_speech_frames:
            segments.append((seg_start, seg_end))

    # 帧索引 → 采样索引
    pad_samples = int(PAD_MS / 1000 * sr)
    sample_boundaries = []
    for f_start, f_end in segments:
        s_start = max(0, f_start * frame_len - pad_samples)
        s_end = min(len(samples), f_end * frame_len + pad_samples)
        sample_boundaries.append((s_start, s_end))

    return sample_boundaries


def save_wav(path: Path, samples: np.ndarray, sr: int):
    """保存 float32 → int16 WAV"""
    peak = np.max(np.abs(samples))
    if peak > 0:
        samples = samples / peak * 0.95
    wav_int16 = (samples * 32767).astype(np.int16)
    wavfile.write(str(path), sr, wav_int16)


def main():
    print("=== 绘梨衣 念白提取 + 分句切割 ===\n")

    # ── 1. 加载 ──
    print("[1/6] 加载参考音频...")
    mono, sr = load_audio(SONG_PATH)
    total_sec = len(mono) / sr
    print(f"  采样率: {sr}Hz, 总时长: {total_sec:.1f}s")

    # ── 2. 提取念白区间 ──
    print(f"[2/6] 截取念白区间 ({NARRATION_START_SEC}s - {NARRATION_END_SEC}s)...")
    start_idx = int(NARRATION_START_SEC * sr)
    end_idx = int(NARRATION_END_SEC * sr)
    narration = mono[start_idx:end_idx].copy()
    narration_sec = len(narration) / sr
    print(f"  念白长度: {narration_sec:.1f}s")

    # ── 3. 人声增强 ──
    print("[3/6] 人声增强（带通滤波 + 压缩）...")
    enhanced = enhance_vocal(narration, sr)
    print(f"  峰值: {np.max(np.abs(enhanced)):.3f}")

    # ── 4. 保存完整念白 ──
    print("[4/6] 保存完整念白 WAV...")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    save_wav(NARRATION_WAV, enhanced, sr)
    wav_size = NARRATION_WAV.stat().st_size
    print(f"  保存: {NARRATION_WAV.name} ({wav_size / 1024:.1f} KB)")

    # ── 5. 分句切割 ──
    print("[5/6] 基于能量检测分句...")
    boundaries = find_sentence_boundaries(enhanced, sr)
    print(f"  检测到 {len(boundaries)} 个句子段落")

    SENTENCE_DIR.mkdir(parents=True, exist_ok=True)

    sentences_meta = []
    for i, (s_start, s_end) in enumerate(boundaries):
        sentence_samples = enhanced[s_start:s_end]
        duration_sec = len(sentence_samples) / sr
        filename = f"sentence_{i + 1:02d}.wav"
        filepath = SENTENCE_DIR / filename
        save_wav(filepath, sentence_samples, sr)

        sentences_meta.append({
            "index": i + 1,
            "filename": filename,
            "start_sample": int(s_start),
            "end_sample": int(s_end),
            "duration_sec": round(duration_sec, 2),
            "start_sec": round(s_start / sr, 2),
            "end_sec": round(s_end / sr, 2),
        })

    # ── 6. 写元数据 ──
    print("[6/6] 写分句元数据...")
    meta = {
        "source": str(SONG_PATH),
        "sample_rate": sr,
        "total_sentences": len(boundaries),
        "narration_duration_sec": round(narration_sec, 2),
        "parameters": {
            "silence_threshold_ratio": SILENCE_THRESHOLD_RATIO,
            "min_silence_ms": MIN_SILENCE_MS,
            "min_sentence_ms": MIN_SENTENCE_MS,
            "pad_ms": PAD_MS,
        },
        "sentences": sentences_meta,
    }
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  保存: {META_PATH.name}")

    # ── 汇总 ──
    print(f"\n=== 完成 ===")
    print(f"完整念白: {NARRATION_WAV}")
    print(f"分句目录: {SENTENCE_DIR}/ ({len(boundaries)} 个句子)")
    print(f"元数据:   {META_PATH}")
    print()

    # 打印每句信息
    for s in sentences_meta:
        print(f"  第{s['index']:2d}句  {s['duration_sec']:5.2f}s  [{s['start_sec']:6.2f}s - {s['end_sec']:6.2f}s]  → {s['filename']}")

    print()
    print("句子片段可用于:")
    print("  · GPT-SoVITS 逐句训练")
    print("  · 语音馆逐句试听")
    print("  · 绘梨衣对话片段拼接")
    return 0


if __name__ == "__main__":
    sys.exit(main())

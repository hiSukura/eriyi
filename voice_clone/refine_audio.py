"""
Phase 5.1 · 念白素材精处理

处理内容:
  1. 44100Hz → 22050Hz 重采样（GPT-SoVITS 标准）
  2. 峰值归一化到 -3dBFS
  3. 首尾静音修剪（阈值 -40dB，前后各保留 50ms 过渡）
  4. 质量验证报告

依赖: scipy, numpy
运行: python refine_audio.py
"""
import json
import shutil
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy import signal

# ── 路径 ───────────────────────────────
BASE = Path(__file__).parent
SRC_DIR = BASE / "data"
OUT_DIR = BASE / "data" / "processed"
META_PATH = SRC_DIR / "sentence_meta.json"
OUT_DIR.mkdir(exist_ok=True)

# ── 参数 ───────────────────────────────
TARGET_SR = 22050
PEAK_DB = -3.0          # 峰值归一化目标 (dBFS)
SILENCE_THRESH_DB = -40  # 静音阈值
TRIM_PAD_MS = 50         # 修剪后保留的过渡

# ── 工具函数 ───────────────────────────
def load_wav(path: Path):
    sr, data = wavfile.read(path)
    if data.dtype != np.float32:
        data = data.astype(np.float32) / np.iinfo(data.dtype).max
    return sr, data

def save_wav(path: Path, sr: int, data: np.ndarray):
    data = np.clip(data, -1.0, 1.0)
    wavfile.write(path, sr, (data * 32767).astype(np.int16))

def rms_db(data: np.ndarray) -> float:
    """RMS 电平 (dBFS)"""
    rms = np.sqrt(np.mean(data**2))
    if rms < 1e-10:
        return -100
    return 20 * np.log10(rms)

def peak_db(data: np.ndarray) -> float:
    peak = np.max(np.abs(data))
    if peak < 1e-10:
        return -100
    return 20 * np.log10(peak)

def normalize_peak(data: np.ndarray, target_db: float) -> np.ndarray:
    """峰值归一化"""
    current = peak_db(data)
    gain = 10**((target_db - current) / 20)
    return data * gain

def trim_silence(data: np.ndarray, sr: int, thresh_db: float, pad_ms: int):
    """修剪首尾静音"""
    thresh_linear = 10 ** (thresh_db / 20)
    pad_samples = int(pad_ms / 1000 * sr)

    # 找第一个超过阈值的样本
    above = np.abs(data) > thresh_linear
    if not np.any(above):
        return data  # 全静音，不修剪

    start = max(0, np.argmax(above) - pad_samples)
    end = min(len(data), len(data) - np.argmax(above[::-1]) + pad_samples)
    return data[start:end]

def audio_stats(data: np.ndarray, sr: int) -> dict:
    return {
        "duration_sec": round(len(data) / sr, 2),
        "sample_rate": sr,
        "samples": len(data),
        "peak_db": round(peak_db(data), 1),
        "rms_db": round(rms_db(data), 1),
    }


# ── 主流程 ─────────────────────────────
def main():
    report = {"source": "最后的旅行 — 夏螟虫虫 念白", "target_sr": TARGET_SR,
              "target_peak_db": PEAK_DB, "files": []}

    wav_files = sorted(SRC_DIR.glob("sentence_0[1-6].wav"))
    if not wav_files:
        print("❌ 未找到 sentence_01~06.wav")

    for wf in wav_files:
        name = wf.stem
        print(f"\n{'='*50}")
        print(f"  {name}")

        # 1. 加载
        sr, data = load_wav(wf)
        before = audio_stats(data, sr)
        print(f"  原始: {before['duration_sec']}s @ {sr}Hz, peak={before['peak_db']}dB, rms={before['rms_db']}dB")

        # 2. 重采样
        if sr != TARGET_SR:
            new_len = int(len(data) * TARGET_SR / sr)
            data = signal.resample(data, new_len)
            sr = TARGET_SR
            print(f"  重采样 → {sr}Hz ({len(data)} samples)")

        # 3. 修剪静音
        data_trimmed = trim_silence(data, sr, SILENCE_THRESH_DB, TRIM_PAD_MS)
        trimmed_len = len(data_trimmed) / sr
        if len(data_trimmed) != len(data):
            print(f"  修剪静音: {len(data)/sr:.2f}s → {trimmed_len:.2f}s")
        data = data_trimmed

        # 4. 峰值归一化
        data = normalize_peak(data, PEAK_DB)

        # 5. 保存
        out_path = OUT_DIR / f"{name}_22050.wav"
        save_wav(out_path, sr, data)

        after = audio_stats(np.array(data), sr)
        print(f"  处理后: {after['duration_sec']}s @ {after['sample_rate']}Hz, peak={after['peak_db']}dB, rms={after['rms_db']}dB")

        # 转换为 Python 原生类型（避免 JSON 序列化问题）
        clean_after = {k: (float(v) if isinstance(v, (np.floating, np.float32, np.float64)) else v)
                       for k, v in after.items()}

        report["files"].append({
            "name": name,
            "path": str(out_path.relative_to(BASE)),
            "before": {k: (float(v) if isinstance(v, (np.floating, np.float32, np.float64)) else v) for k, v in before.items()},
            "after": clean_after,
        })

        # 复制对应文本标注
        txt_src = SRC_DIR / f"{name}.txt"
        if txt_src.exists():
            shutil.copy(txt_src, OUT_DIR / f"{name}.txt")

    # ── 生成 GPT-SoVITS list.txt ───────
    list_lines = []
    for f in report["files"]:
        name = f["name"]
        txt_path = OUT_DIR / f"{name}.txt"
        text = txt_path.read_text(encoding="utf-8").strip() if txt_path.exists() else ""
        list_lines.append(f"processed/{name}_22050.wav|eriyi|ZH|{text}")

    list_path = OUT_DIR / "list.txt"
    list_path.write_text("\n".join(list_lines), encoding="utf-8")
    print(f"\n  ✅ list.txt ({len(list_lines)} entries)")

    # ── 汇总报告 ───────────────────────
    total_before = sum(f["before"]["duration_sec"] for f in report["files"])
    total_after = sum(f["after"]["duration_sec"] for f in report["files"])
    report["total_before_sec"] = round(total_before, 1)
    report["total_after_sec"] = round(total_after, 1)
    report["total_files"] = len(report["files"])

    report_path = OUT_DIR / "refine_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*50}")
    print(f"  总计: {len(report['files'])} 文件")
    print(f"  总时长: {total_before}s → {total_after}s")
    print(f"  输出目录: {OUT_DIR}")
    print(f"  报告: {report_path}")
    print(f"\n  下一步:")
    print(f"    python setup_gpt_sovits.py install  (克隆GPT-SoVITS)")
    print(f"    python setup_gpt_sovits.py train    (训练模型)")


if __name__ == "__main__":
    main()

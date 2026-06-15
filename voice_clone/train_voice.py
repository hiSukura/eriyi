"""
GPT-SoVITS 一键训练脚本 · 直接调用GPT-SoVITS Python API
用法: python train_voice.py
"""
import sys
from pathlib import Path

GPT_DIR = Path(__file__).parent / "GPT-SoVITS"
sys.path.insert(0, str(GPT_DIR))
sys.path.insert(0, str(GPT_DIR / "GPT_SoVITS"))

SPEAKER = "eriyi"
LANG = "zh"
DATA_DIR = GPT_DIR / "data" / SPEAKER
LIST_PATH = GPT_DIR / "data" / "list.txt"
PRETRAINED = GPT_DIR / "GPT_SoVITS" / "pretrained_models"


def main():
    print("=" * 50)
    print("  绘梨衣声音克隆 · 训练启动")
    print(f"  说话人: {SPEAKER} | 语言: {LANG}")
    print(f"  数据: {DATA_DIR}")
    print(f"  预训练: {PRETRAINED}")
    print("=" * 50)

    # 1. 预处理
    print("\n[1/3] 音频预处理（重采样16k/mono → .wav）...")
    from GPT_SoVITS.prepare_datasets.prepare_short_audio import process_audio_files
    process_audio_files(DATA_DIR, SPEAKER)
    print("  ✅ 预处理完成")

    # 2. 训练 SoVITS (s1)
    print("\n[2/3] 训练 SoVITS 特征提取器...")
    from GPT_SoVITS.s1_train import main as s1_main
    s1_main()
    print("  ✅ s1 训练完成")

    # 3. 训练 GPT (s2)
    print("\n[3/3] 训练 GPT 语音生成器...")
    from GPT_SoVITS.s2_train import main as s2_main
    s2_main()
    print("  ✅ s2 训练完成")

    print("\n" + "=" * 50)
    print("  🎉 训练完成！绘梨衣的声音已克隆。")
    print(f"  模型保存在: GPT_SoVITS/SoVITS_weights/{SPEAKER}/")
    print(f"  推理: POST /api/tts/generate?text=...")
    print("=" * 50)


if __name__ == "__main__":
    main()

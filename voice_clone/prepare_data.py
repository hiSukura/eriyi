"""
Phase 5 · 声音克隆 — 数据准备脚本
将念白分句WAV整理为GPT-SoVITS所需的训练格式

输出：
  voice_clone/data/
    ├── sentence_01.wav ... sentence_06.wav   (训练音频)
    ├── sentence_01.txt ... sentence_06.txt    (对应文本标注)
    ├── list.txt                               (路径|说话人|语言|文本 格式)
    └── train_info.json                        (训练摘要)
"""
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SENTENCE_DIR = PROJECT_ROOT / "语音" / "念白_分句" / "sentences"
META_PATH = PROJECT_ROOT / "语音" / "念白_分句" / "sentence_meta.json"
CLONE_DATA_DIR = Path(__file__).parent / "data"

# ── 念白文本标注（根据实际歌词内容标注） ──
# 《最后的旅行》念白部分文本（夏螟虫虫）
TRANSCRIPTIONS = {
    1: "在那之前，我都以为我是一个人的。",
    2: "直到遇到你。",
    3: "原来这个世界上，还有一个人是这么在乎我的。",
    4: "Sakura，谢谢你。",
    5: "让我知道，被一个人放在心上是什么感觉。",
    6: "我想和你一起去很多地方。",
}


def prepare():
    CLONE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    meta = json.loads(META_PATH.read_text(encoding="utf-8"))

    entries = []
    train_count = 0

    for s in meta["sentences"]:
        idx = s["index"]
        if idx >= 7:
            continue  # 跳过歌曲部分

        src_wav = SENTENCE_DIR / s["filename"]
        if not src_wav.exists():
            print(f"  ⚠ 跳过 sentence_{idx:02d}: 文件不存在")
            continue

        dst_wav = CLONE_DATA_DIR / f"sentence_{idx:02d}.wav"
        shutil.copy2(src_wav, dst_wav)

        # 写入文本标注
        text = TRANSCRIPTIONS.get(idx, "")
        txt_path = CLONE_DATA_DIR / f"sentence_{idx:02d}.txt"
        txt_path.write_text(text, encoding="utf-8")

        # list.txt 条目: 路径|说话人|语言|文本
        entries.append(
            f"data/sentence_{idx:02d}.wav|eriyi|ZH|{text}"
        )
        train_count += 1
        print(f"  ✅ sentence_{idx:02d}  {s['duration_sec']:.1f}s → {dst_wav.name}")

    # 写 list.txt
    list_path = CLONE_DATA_DIR / "list.txt"
    list_path.write_text("\n".join(entries), encoding="utf-8")
    print(f"  📋 list.txt: {train_count} 条")

    # 训练摘要
    total_dur = sum(
        s["duration_sec"]
        for s in meta["sentences"]
        if s["index"] < 7
    )
    info = {
        "speaker": "eriyi",
        "language": "ZH",
        "sample_rate": meta["sample_rate"],
        "total_samples": train_count,
        "total_duration_sec": round(total_dur, 1),
        "source": "最后的旅行 — 夏螟虫虫 念白",
        "note": "前6句为念白内容，第7句为歌曲演唱已排除",
    }
    info_path = CLONE_DATA_DIR / "train_info.json"
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  📊 train_info.json: {total_dur:.1f}s 总长")

    print(f"\n=== 训练数据就绪 ===")
    print(f"说话人: eriyi | 语言: ZH | 样本: {train_count}句 | 总长: {total_dur:.1f}s")
    print(f"数据目录: {CLONE_DATA_DIR}")
    print()
    print("下一步：克隆 GPT-SoVITS 仓库并启动训练")
    print("  git clone https://github.com/RVC-Boss/GPT-SoVITS.git")
    print(f"  python GPT-SoVITS/preprocess.py --data_dir {CLONE_DATA_DIR}")


if __name__ == "__main__":
    prepare()

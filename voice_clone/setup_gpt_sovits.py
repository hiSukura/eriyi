"""
Phase 5.2/5.3/5.4 · GPT-SoVITS 环境搭建 + 训练 + 集成
RTX 2070 8GB · Windows 10 · Python 3.10
"""

import os
import sys
import subprocess
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
VOICE_CLONE_DIR = Path(__file__).parent
DATA_DIR = VOICE_CLONE_DIR / "data"
GPT_SOVITS_DIR = Path.home() / "GPT-SoVITS"

CUDA_REQUIRED = "11.8"
PYTORCH_VERSION = "2.1.0"
PYTHON_MINOR = "3.10"


def check_env():
    """环境检查"""
    print("=" * 50)
    print("  GPT-SoVITS 环境检查")
    print("=" * 50)
    results = {}

    # GPU
    try:
        import torch
        cuda_ok = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if cuda_ok else "N/A"
        vram = torch.cuda.get_device_properties(0).total_mem / 1024**3 if cuda_ok else 0
        results["gpu"] = f"{gpu_name} ({vram:.1f}GB)" if cuda_ok else "NO GPU"
        print(f"  GPU: {results['gpu']}")
    except ImportError:
        results["gpu"] = "PyTorch not installed"
        print(f"  GPU: {results['gpu']}")

    # Python
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    results["python"] = py_ver
    print(f"  Python: {py_ver}")

    # 音频数据
    list_file = DATA_DIR / "list.txt"
    if list_file.exists():
        n = len(list_file.read_text(encoding="utf-8").strip().split("\n"))
        results["data"] = f"{n} sentences"
        print(f"  Data: {n} narration sentences ready")
    else:
        results["data"] = "missing"
        print(f"  Data: NOT FOUND — run prepare_data.py first")

    # Disk
    try:
        import shutil
        free = shutil.disk_usage(str(PROJECT_ROOT)).free / 1024**3
        results["disk"] = f"{free:.1f}GB free"
        print(f"  Disk: {free:.1f}GB free")
    except:
        pass

    print()
    return results


def install_deps():
    """安装 GPT-SoVITS 依赖"""
    print("安装 GPT-SoVITS 依赖...")
    # This would be executed by the user when ready
    cmds = [
        f'conda create -n gpt_sovits python={PYTHON_MINOR} -y',
        'conda activate gpt_sovits',
        f'pip install torch=={PYTORCH_VERSION}+cu{CUDA_REQUIRED.replace(".", "")} '
        '--index-url https://download.pytorch.org/whl/cu118',
        'pip install -r requirements.txt',
    ]
    print("\n".join(f"  > {c}" for c in cmds))
    return cmds


def generate_config():
    """生成训练配置"""
    config = {
        "speaker": "eriyi",
        "language": "ZH",
        "data_dir": str(DATA_DIR),
        "text_file": str(DATA_DIR / "list.txt"),
        "output_dir": str(VOICE_CLONE_DIR / "output"),
        "model_dir": str(VOICE_CLONE_DIR / "model"),
        "batch_size": 8,
        "epochs": 50,
        "learning_rate": 1e-4,
        "sample_rate": 44100,
        "hop_length": 512,
        "win_length": 2048,
        "n_fft": 2048,
        "note": "6句念白 / 12.8秒 / RTX 2070 8GB 可训练",
    }
    config_path = VOICE_CLONE_DIR / "train_config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"训练配置已生成: {config_path}")
    return config


if __name__ == "__main__":
    results = check_env()
    generate_config()
    print()
    print("下一步（手动执行）：")
    print("  1. conda create -n gpt_sovits python=3.10")
    print("  2. conda activate gpt_sovits")
    print("  3. git clone https://github.com/RVC-Boss/GPT-SoVITS.git")
    print(f"  4. cd GPT-SoVITS && pip install -r requirements.txt")
    print(f"  5. 按 GPT-SoVITS 文档进行预处理和训练")

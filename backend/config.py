"""
绘梨衣后端 · 配置文件
"""
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = Path(__file__).parent

# 数据目录
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# SQLite 数据库路径
DATABASE_PATH = DATA_DIR / "绘梨衣.db"

# 静态文件目录
STATIC_DIR = BACKEND_DIR / "static"

# 语音文件目录
VOICE_DIR = PROJECT_ROOT / "语音"

# 日记目录
DIARY_DIR = PROJECT_ROOT / "绘梨衣日记"

# 记忆目录
MEMORY_DIR = PROJECT_ROOT / ".workbuddy" / "memory"

# 声音克隆目录
VOICE_CLONE_DIR = PROJECT_ROOT / "voice_clone"

# 服务配置
HOST = os.environ.get("ELISHA_HOST", "127.0.0.1")
PORT = int(os.environ.get("ELISHA_PORT", "5432"))

# TTS 代理 — 留空=直连, 设如 http://127.0.0.1:7897
TTS_PROXY = os.environ.get("TTS_PROXY", "")

# 绘梨衣信息
ELISHA_VERSION = "3.0.0"
ELISHA_NAME = "绘梨衣"
ELISHA_COLOR = "#E8543E"  # 灯笼红

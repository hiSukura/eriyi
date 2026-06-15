# 绘梨衣 · Docker 镜像
FROM python:3.11-slim

LABEL description="绘梨衣 个人智能助手 · 后端服务"

# 系统依赖（音频解码 + 编译）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# PyTorch CPU 版（~200MB，避免下载 CUDA 版本）
RUN pip install --no-cache-dir \
    torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# Python 依赖
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# 应用代码（不包含 data/models/voice_clone — 通过卷挂载）
WORKDIR /app
COPY backend/ /app/backend/

# 项目根目录结构（config.py 中 PROJECT_ROOT = backend/..）
# voice_clone/ 语音/ 绘梨衣日记/ → 运行时卷挂载

WORKDIR /app/backend

EXPOSE 5432

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5432", "--log-level", "info"]

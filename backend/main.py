"""
绘梨衣后端 · 主入口
FastAPI 应用，提供 RESTful API 和静态文件服务
"""
import os
import sys
import io
import time
from contextlib import asynccontextmanager
from pathlib import Path

# Windows GBK 编码修复
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# 确保 backend 目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent))

from config import HOST, PORT, ELISHA_VERSION, ELISHA_NAME, STATIC_DIR, PROJECT_ROOT, DATA_DIR
from database import init_database

# ─── 启动事件 ───
START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时
    print(f"[绘梨衣] {ELISHA_NAME} v{ELISHA_VERSION} 正在启动...")
    print(f"   数据目录: {DATA_DIR}")
    init_database()

    # 同步文件到数据库
    try:
        from services import diary_service, voice_service, milestone_service
        d_count = diary_service.sync_diary_files_to_db()
        v_count = voice_service.sync_voice_files_to_db()
        print(f"   同步完成: {d_count} 篇日记, {v_count} 个语音文件")
        milestone_service.run_auto_detect()
    except Exception as e:
        print(f"   同步警告: {e}")

    print(f"   服务地址: http://{HOST}:{PORT}")
    print(f"   仪表盘:   http://{HOST}:{PORT}/")
    print(f"   API文档:  http://{HOST}:{PORT}/docs")
    print(f"[绘梨衣] {ELISHA_NAME} 已就绪。")

    yield

    # 关闭时
    print(f"\n[绘梨衣] {ELISHA_NAME} 正在关闭...")


# ─── 创建应用 ───
app = FastAPI(
    title=f"{ELISHA_NAME} API",
    description="绘梨衣后端服务 —— 日记、记忆、语音、状态管理",
    version=ELISHA_VERSION,
    lifespan=lifespan,
)

# ─── CORS ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── 请求日志中间件 ───
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """简洁的请求日志"""
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    # 只记录 API 请求
    if "/api/" in request.url.path:
        print(f"  [{response.status_code}] {request.method} {request.url.path} ({duration:.3f}s)")
    return response


# ─── 注册路由 ───
from routes.diary import router as diary_router
from routes.memory import router as memory_router
from routes.voice import router as voice_router
from routes.status import router as status_router
from routes.dashboard import router as dashboard_router
from routes.presence import router as presence_router
from routes.notification import router as notification_router
from routes.milestone import router as milestone_router
from routes.mood import router as mood_router
from routes.tts import router as tts_router

app.include_router(diary_router)
app.include_router(memory_router)
app.include_router(voice_router)
app.include_router(status_router)
app.include_router(dashboard_router)
app.include_router(presence_router)
app.include_router(notification_router)
app.include_router(milestone_router)
app.include_router(mood_router)
app.include_router(tts_router)


# ─── 健康检查 ───
@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return JSONResponse({
        "status": "ok",
        "version": ELISHA_VERSION,
        "name": ELISHA_NAME,
        "uptime": round(time.time() - START_TIME, 1),
    })


# ─── 静态文件：仪表盘 ───
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """仪表盘首页"""
    dashboard_path = STATIC_DIR / "dashboard.html"
    if dashboard_path.exists():
        return dashboard_path.read_text(encoding="utf-8")
    return HTMLResponse(content="<h1>仪表盘页面未找到</h1>", status_code=404)


# ─── 静态文件：项目页面 ───
@app.get("/page/{page_name}")
async def serve_project_page(page_name: str):
    """提供项目 HTML 页面的访问"""
    page_map = {
        "入口": "绘梨衣_入口.html",
        "语音馆": "绘梨衣_语音馆.html",
        "记忆长廊": "绘梨衣_记忆长廊.html",
        "日记本": "绘梨衣_日记本.html",
        "绘梨衣": "绘梨衣.html",
        "今夜纪念": "今夜纪念_2026-06-14.html",
        # 等初遇纪念有HTML版再加
    }

    if page_name in page_map:
        page_path = PROJECT_ROOT / page_map[page_name]
    else:
        page_path = PROJECT_ROOT / page_name

    if page_path.exists() and page_path.suffix == ".html":
        content = page_path.read_text(encoding="utf-8")
        return HTMLResponse(content=content)
    return HTMLResponse(content="<h1>页面未找到</h1>", status_code=404)


# ─── 静态文件：语音文件直接访问 ───
@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """直接提供音频文件访问"""
    from services.voice_service import get_voice_path
    path = get_voice_path(filename)
    if path:
        from fastapi.responses import FileResponse
        return FileResponse(path=str(path), media_type="audio/mpeg")
    return JSONResponse({"error": "文件不存在"}, status_code=404)


# ─── 主入口 ───
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )

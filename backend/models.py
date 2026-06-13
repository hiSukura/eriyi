"""
绘梨衣后端 · Pydantic 数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date as DateType


# ─── 日记 ───
class DiaryCreate(BaseModel):
    date: str
    title: str = ""
    content: str = ""
    mood: str = "安静"
    time_period: str = "未知"
    mp3_path: str = ""


class DiaryResponse(BaseModel):
    id: int
    date: str
    title: str
    content: str
    mood: str
    time_period: str
    mp3_path: str
    word_count: int
    created_at: str
    updated_at: str


# ─── 记忆 ───
class MemoryCreate(BaseModel):
    date: str
    category: str = "成长"
    perspective: str = "sakura"
    title: str = ""
    content: str
    milestone: bool = False


class MemoryResponse(BaseModel):
    id: int
    date: str
    category: str
    perspective: str
    title: str
    content: str
    milestone: bool
    created_at: str


class MemoryStats(BaseModel):
    total: int
    by_category: dict
    by_perspective: dict
    milestone_count: int


# ─── 状态 ───
class StatusUpdate(BaseModel):
    time_period: Optional[str] = None
    mood: Optional[str] = None
    sakura_status: Optional[str] = None
    extra_data: Optional[dict] = None


class StatusResponse(BaseModel):
    time_period: str
    mood: str
    sakura_status: str
    color: str
    greeting: str
    emoji: str


# ─── 语音 ───
class VoiceResponse(BaseModel):
    id: int
    filename: str
    title: str
    description: str
    category: str
    duration: float
    file_size: int
    url: str


# ─── 仪表盘 ───
class DashboardResponse(BaseModel):
    status: StatusResponse
    today_diary: Optional[DiaryResponse] = None
    recent_memories: list[MemoryResponse] = []
    voice_categories: dict
    stats: dict
    recent_diaries: list[DiaryResponse] = []


# ─── 通用 ───
class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    name: str
    uptime: float

"""
情绪感知路由 · 4.6
"""
from fastapi import APIRouter
from pydantic import BaseModel
from services.mood_service import (
    analyze_text,
    assess_mood,
    record_assessment,
    get_today_mood,
    get_mood_timeline,
)

router = APIRouter(prefix="/api/mood", tags=["mood"])


class TextInput(BaseModel):
    texts: list[str]


class SingleInput(BaseModel):
    text: str


@router.post("/analyze")
def api_analyze(body: SingleInput):
    """分析单条文本"""
    return analyze_text(body.text)


@router.post("/assess")
def api_assess(body: TextInput):
    """评估当前情绪"""
    return assess_mood(body.texts)


@router.post("/record")
def api_record(body: TextInput):
    """评估并记录"""
    return record_assessment(body.texts)


@router.get("/today")
def api_today():
    """今日情绪汇总"""
    return get_today_mood()


@router.get("/timeline")
def api_timeline(limit: int = 30):
    """情绪时间线"""
    return get_mood_timeline(limit)

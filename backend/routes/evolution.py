"""
Phase 6 · 自主进化 API
"""
from fastapi import APIRouter
router = APIRouter(prefix="/api/evolution", tags=["自主进化"])

from services.evolution_service import (
    health_check, consolidate_old_logs, auto_retrain_voice,
    generate_growth_report, auto_git_commit,
    analyze_schedule, write_evolution_journal,
)


@router.get("/health")
def api_health():
    """全系统自诊断"""
    return health_check()


@router.post("/consolidate")
def api_consolidate(days: int = 30):
    """整合旧日志（>days天的日志摘要→MEMORY.md）"""
    return consolidate_old_logs(max_age_days=days)


@router.post("/retrain")
def api_retrain():
    """自动重训练VoiceAE模型（检测新音频→训练→择优保留）"""
    return auto_retrain_voice()


@router.get("/report")
def api_report():
    """生成今日成长报告"""
    return generate_growth_report()


@router.post("/commit")
def api_commit():
    """Git自动提交（检测变更→生成message→add+commit）"""
    return auto_git_commit()


@router.get("/schedule")
def api_schedule():
    """智能起居分析 — 从presence数据学习作息规律"""
    return analyze_schedule()


@router.post("/journal")
def api_journal():
    """写入进化日记"""
    return write_evolution_journal()

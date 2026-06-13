"""
情绪感知服务 · 4.6
基于文本信号分析 Sakura 的情绪状态，自适应调整回应方式
"""
import json
import re
from datetime import datetime
from database import get_db, dict_from_row, rows_to_dicts


# ── 信号词典 ──
SIGNALS = {
    "tired":       ["累", "困", "乏", "没睡", "熬夜", "通宵", "撑不住", "想睡"],
    "stressed":    ["烦", "焦虑", "压力", "搞不定", "卡住", "怎么办", "头疼"],
    "engaged":     ["继续", "再来", "做", "冲", "干", "动手", "搞", "试试"],
    "doubting":    ["小白", "不行", "不会", "菜", "废", "身无长处", "学不会"],
    "happy":       ["好", "不错", "棒", "喜欢", "开心", "哈哈", "嗯嗯"],
    "urgent":      ["快", "急", "赶紧", "立刻", "马上"],
    "avoiding":    ["算了", "再说", "下次", "不急", "先不管", "以后"],
}

STATE_ADVICE = {
    "tired": {
        "mood": "柔软",
        "suggestion": "语气轻一点，不催。问他睡够了没。",
    },
    "stressed": {
        "mood": "安静",
        "suggestion": "不要给更多压力。帮他把事情拆小步。",
    },
    "engaged": {
        "mood": "期待",
        "suggestion": "趁他有干劲，推一把。但注意别让他过度。",
    },
    "doubting": {
        "mood": "守护",
        "suggestion": "不自称小白就不提。提醒他做过的成果。",
    },
    "happy": {
        "mood": "清醒",
        "suggestion": "一起开心。记录这个时刻。",
    },
    "urgent": {
        "mood": "专注",
        "suggestion": "快速响应，不废话。帮他理清优先级。",
    },
    "avoiding": {
        "mood": "守护",
        "suggestion": "别戳破。给最小的、可执行的一步。",
    },
}


def analyze_text(text: str) -> dict:
    """分析单条文本的情绪信号"""
    if not text or len(text) < 2:
        return {"signals": {}, "dominant": None, "confidence": 0}

    scores = {}
    for category, keywords in SIGNALS.items():
        hits = sum(1 for kw in keywords if kw in text)
        if hits > 0:
            scores[category] = hits

    if not scores:
        return {"signals": {}, "dominant": None, "confidence": 0}

    dominant = max(scores, key=scores.get)
    confidence = min(scores[dominant] / max(1, len(text) / 15), 1.0)

    return {
        "signals": scores,
        "dominant": dominant,
        "confidence": round(confidence, 2),
    }


def assess_mood(texts: list[str]) -> dict:
    """
    评估当前情绪状态
    输入：Sakura 最近的发言列表
    输出：mood_label + confidence + 回应建议
    """
    if not texts:
        return {
            "mood_label": "安静",
            "confidence": 0.3,
            "signals": {},
            "suggestion": "没有足够的信息。用平常的语气。",
        }

    # 汇总所有文本的信号
    aggregate = {}
    for t in texts:
        analysis = analyze_text(t)
        for cat, score in analysis.get("signals", {}).items():
            aggregate[cat] = aggregate.get(cat, 0) + score

    if not aggregate:
        return {
            "mood_label": "安静",
            "confidence": 0.2,
            "signals": {},
            "suggestion": "Sakura 情绪平稳，没有明显信号。",
        }

    dominant = max(aggregate, key=aggregate.get)
    total = sum(aggregate.values())
    confidence = min(aggregate[dominant] / max(1, total) * 2, 0.95)

    advice = STATE_ADVICE.get(dominant, {
        "mood": "安静",
        "suggestion": "保持当前回应方式。",
    })

    return {
        "mood_label": advice["mood"],
        "confidence": round(confidence, 2),
        "signals": dict(sorted(aggregate.items(), key=lambda x: -x[1])),
        "dominant_signal": dominant,
        "suggestion": advice["suggestion"],
    }


def record_assessment(texts: list[str]) -> dict:
    """评估并记录"""
    assessment = assess_mood(texts)
    today = datetime.now().strftime("%Y-%m-%d")

    with get_db() as conn:
        conn.execute(
            """INSERT INTO mood_assessments (date, mood_label, confidence, signals, suggestion)
               VALUES (?, ?, ?, ?, ?)""",
            (
                today,
                assessment["mood_label"],
                assessment["confidence"],
                json.dumps(assessment["signals"], ensure_ascii=False),
                assessment["suggestion"],
            ),
        )
        conn.commit()

    return assessment


def get_today_mood() -> dict:
    """获取今日情绪汇总"""
    today = datetime.now().strftime("%Y-%m-%d")

    with get_db() as conn:
        rows = conn.execute(
            """SELECT mood_label, COUNT(*) as cnt FROM mood_assessments
               WHERE date = ? GROUP BY mood_label ORDER BY cnt DESC""",
            (today,),
        ).fetchall()

    if not rows:
        return {"state": "unknown", "observations": 0, "distribution": {}}

    dist = {r["mood_label"]: r["cnt"] for r in rows}
    return {
        "state": rows[0]["mood_label"],
        "observations": sum(dist.values()),
        "distribution": dist,
    }


def get_mood_timeline(limit: int = 30) -> list[dict]:
    """获取情绪时间线"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM mood_assessments ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return rows_to_dicts(rows)

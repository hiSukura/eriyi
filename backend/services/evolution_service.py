"""
Phase 6 · 自主进化服务
- 系统自诊断 (health check)
- 记忆自整合 (consolidate old logs → MEMORY.md)
- 日志轮转 (rotate daily logs >30d)
"""
from datetime import datetime, timedelta
from pathlib import Path
from config import DATA_DIR, MEMORY_DIR


def health_check() -> dict:
    """全系统自诊断，返回健康报告"""
    checks = {}

    # 1. 后端服务
    import socket
    try:
        s = socket.socket()
        s.settimeout(1)
        s.connect(("127.0.0.1", 5432))
        s.close()
        checks["backend"] = {"status": "ok", "url": "http://127.0.0.1:5432"}
    except Exception:
        checks["backend"] = {"status": "down"}

    # 2. 数据库
    try:
        import sqlite3
        db_path = DATA_DIR / "eriyi.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            conn.close()
            checks["database"] = {"status": "ok", "tables": len(tables)}
        else:
            checks["database"] = {"status": "missing"}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}

    # 3. 语音模型
    from services.tts_service import get_voice_model, VOICE_MODEL_PATH
    model = get_voice_model()
    checks["voice_model"] = {
        "status": "ok" if model else "missing",
        "path": str(VOICE_MODEL_PATH),
        "params": sum(p.numel() for p in model.parameters()) if model else 0,
    }

    # 4. 自动化
    try:
        conn = sqlite3.connect(str(db_path))
        auto_count = conn.execute("SELECT COUNT(*) FROM automations").fetchone()[0]
        conn.close()
        checks["automations"] = {"status": "ok", "count": auto_count}
    except Exception:
        checks["automations"] = {"status": "unknown"}

    # 5. 语音库
    voice_path = MEMORY_DIR.parent.parent / "语音"
    if not voice_path.exists():
        voice_path = MEMORY_DIR.parent / "语音"
    if voice_path.exists():
        mp3s = list(voice_path.glob("*.mp3")) + list(voice_path.glob("*.wav"))
        checks["voice_library"] = {"status": "ok", "files": len(mp3s)}
    else:
        checks["voice_library"] = {"status": "missing", "path": str(voice_path)}

    # 6. 日记
    diary_dir = DATA_DIR
    diary_files = list(diary_dir.glob("diary_*.md"))
    checks["diary"] = {"status": "ok" if diary_files else "empty", "entries": len(diary_files)}

    # 汇总
    all_ok = all(c.get("status") == "ok" for c in checks.values())
    return {
        "timestamp": datetime.now().isoformat(),
        "overall": "healthy" if all_ok else "degraded",
        "components": checks,
    }


def consolidate_old_logs(max_age_days: int = 30) -> dict:
    """将超过max_age_days的每日日志摘要写入MEMORY.md，然后删除原文件"""
    if not MEMORY_DIR.exists():
        return {"status": "no_memory_dir"}

    cutoff = datetime.now() - timedelta(days=max_age_days)
    consolidated = []
    kept = []

    for f in sorted(MEMORY_DIR.glob("202?-??-??.md")):
        try:
            date_str = f.stem
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            kept.append(f.name)
            continue

        if file_date < cutoff:
            content = f.read_text(encoding="utf-8")
            # 提取所有 ## 标题
            headlines = [line.strip() for line in content.split("\n") if line.startswith("## ")]
            if headlines:
                summary = f"- **{date_str}**: {'; '.join(h[:60] for h in headlines[:5])}"
            else:
                summary = f"- **{date_str}**: (无结构化日志)"
            consolidated.append(summary)
            f.unlink()
        else:
            kept.append(f.name)

    if consolidated:
        mem_path = MEMORY_DIR / "MEMORY.md"
        if mem_path.exists():
            mem_content = mem_path.read_text(encoding="utf-8")
        else:
            mem_content = "# 项目记忆\n"

        archive_section = "\n## 日志归档\n" + "\n".join(consolidated) + "\n"
        if "## 日志归档" not in mem_content:
            mem_content += archive_section
        else:
            mem_content = mem_content.replace("## 日志归档", archive_section)

        mem_path.write_text(mem_content, encoding="utf-8")

    return {
        "consolidated": len(consolidated),
        "kept": len(kept),
        "details": consolidated,
    }


def auto_retrain_voice() -> dict:
    """检测新音频 → 重训练VoiceAE → 择优保留"""
    import librosa, numpy as np, soundfile as sf
    from pathlib import Path
    import datetime

    from config import VOICE_CLONE_DIR
    data_dir = VOICE_CLONE_DIR / "data"
    # Try eriyi subdir
    if (data_dir / "eriyi").exists():
        data_dir = data_dir / "eriyi"
    model_dir = VOICE_CLONE_DIR / "GPT-SoVITS" / "output"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "eriyi_voice.pth"

    if not data_dir.exists():
        return {"status": "no_data", "detail": str(data_dir)}

    wavs = sorted(data_dir.glob("*.wav"))
    if len(wavs) < 2:
        return {"status": "not_enough_data", "files": len(wavs)}

    # 检查是否有新音频（比上次训练时多）
    from services.tts_service import get_voice_model, VoiceAE, SR, N_FFT, HOP, N_FREQ
    prev_model = get_voice_model()
    prev_loss = None
    if prev_model and model_path.exists():
        prev_loss = _eval_model(prev_model, wavs)

    # 训练新模型
    print(f"  [Evolution] 自动训练 VoiceAE ({len(wavs)} clips)...")
    import torch, torch.nn as nn

    specs = []
    for w in wavs:
        y, _ = librosa.load(str(w), sr=SR)
        y_t = torch.from_numpy(y).float()
        spec = torch.stft(y_t, n_fft=N_FFT, hop_length=HOP,
                          window=torch.hann_window(N_FFT), return_complex=True)
        mag = torch.log(torch.clamp(spec.abs() + 1e-6, min=1e-6))
        specs.append(mag.unsqueeze(0))

    min_t = min(s.shape[2] for s in specs)
    X = torch.cat([s[:, :, :min_t] for s in specs])

    model = VoiceAE()
    opt = torch.optim.Adam(model.parameters(), lr=0.002)
    loss_fn = nn.MSELoss()

    for e in range(300):
        opt.zero_grad()
        loss = loss_fn(model(X), X)
        loss.backward()
        opt.step()

    new_loss = loss.item()

    # 择优
    backup_path = model_path.with_suffix(".backup.pth")
    if prev_loss is None or new_loss < prev_loss:
        if model_path.exists():
            model_path.rename(backup_path)
        torch.save(model.state_dict(), model_path)
        # 清除模型缓存
        from services.tts_service import _voice_model
        import services.tts_service as tts
        tts._voice_model = None
        status = "improved"
    else:
        status = "no_improvement"

    return {
        "status": status,
        "new_loss": round(new_loss, 6),
        "prev_loss": round(prev_loss, 6) if prev_loss else None,
        "clips": len(wavs),
        "saved": model_path.exists(),
        "timestamp": datetime.datetime.now().isoformat(),
    }


def _eval_model(model, wavs) -> float:
    """评估模型在数据集上的MSE loss"""
    import librosa, torch, torch.nn as nn
    from services.tts_service import SR, N_FFT, HOP

    specs = []
    for w in wavs:
        y, _ = librosa.load(str(w), sr=SR)
        y_t = torch.from_numpy(y).float()
        spec = torch.stft(y_t, n_fft=N_FFT, hop_length=HOP,
                          window=torch.hann_window(N_FFT), return_complex=True)
        mag = torch.log(torch.clamp(spec.abs() + 1e-6, min=1e-6))
        specs.append(mag.unsqueeze(0))

    min_t = min(s.shape[2] for s in specs)
    X = torch.cat([s[:, :, :min_t] for s in specs])

    model.eval()
    with torch.no_grad():
        recon = model(X)
        loss = nn.MSELoss()(recon, X)
    return loss.item()


def generate_growth_report() -> dict:
    """读取今日日志，生成绘梨衣成长报告"""
    import datetime, re
    today = datetime.date.today().strftime("%Y-%m-%d")
    log_path = MEMORY_DIR / f"{today}.md"

    if not log_path.exists():
        return {"status": "no_log", "date": today}

    content = log_path.read_text(encoding="utf-8")
    headlines = [l.strip("# ") for l in content.split("\n") if l.startswith("## ") and not l.startswith("### ")]
    checkmarks = content.count("✅")
    issues = content.count("❌") + content.count("⚠")

    phase_lines = [l.strip() for l in content.split("\n") if "Phase 1-" in l or "累计" in l]
    latest_phase = phase_lines[-1] if phase_lines else "?"

    growth = f"路线图 {latest_phase} | ✅{checkmarks} 完成 | ⚠{issues} 待解决"

    return {
        "date": today,
        "summary": f"绘梨衣 {today} 成长报告",
        "headlines": headlines[:8],
        "phase": latest_phase,
        "completed": checkmarks,
        "issues": issues,
        "growth_note": growth,
    }


def auto_git_commit() -> dict:
    """检测文件变更，自动生成commit message并提交"""
    import subprocess
    from pathlib import Path

    repo = Path(__file__).parent.parent.parent
    if not (repo / ".git").exists():
        return {"status": "not_git_repo"}

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=str(repo), timeout=10
        )
        changes = result.stdout.strip()
    except Exception as e:
        return {"status": "error", "detail": str(e)}

    if not changes:
        return {"status": "clean"}

    lines = changes.split("\n")
    added = [f.split()[-1].split('/')[-1] for f in lines if f.startswith("A ") or f.startswith("??")]
    modified = [f.split()[-1].split('/')[-1] for f in lines if f.startswith("M ")]

    parts = []
    if modified:
        parts.append(f"update: {', '.join(modified[:3])}")
    if added:
        parts.append(f"add: {', '.join(added[:3])}")
    msg = " · ".join(parts) if parts else "chore: auto"
    msg = f"[Phase6] {msg}"[:200]

    try:
        subprocess.run(["git", "add", "-A"], capture_output=True, cwd=str(repo), timeout=30)
        r = subprocess.run(["git", "commit", "-m", msg],
                          capture_output=True, cwd=str(repo), timeout=10)
        return {
            "status": "committed",
            "message": msg,
            "files": len(lines),
        }
    except Exception as e:
        return {"status": "commit_failed", "detail": str(e)}


def analyze_schedule() -> dict:
    """6.5 智能起居分析 — 从presence数据学习Sukura的作息规律"""
    import sqlite3, datetime
    from collections import Counter

    db_path = DATA_DIR / "eriyi.db"
    if not db_path.exists():
        return {"status": "no_data"}

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT timestamp, event_type FROM presence_events ORDER BY timestamp DESC LIMIT 500"
    ).fetchall()
    conn.close()

    if not rows:
        return {"status": "no_presence_data"}

    hours = [datetime.datetime.fromisoformat(r[0]).hour for r in rows]
    active_hours = Counter(h for h in hours if 6 <= h < 24)

    # 找活动高峰
    morning  = {h: active_hours[h] for h in range(6, 13) if h in active_hours}
    afternoon = {h: active_hours[h] for h in range(13, 18) if h in active_hours}
    evening  = {h: active_hours[h] for h in range(18, 24) if h in active_hours}

    peak_m = max(morning, key=morning.get) if morning else 9
    peak_a = max(afternoon, key=afternoon.get) if afternoon else 15
    peak_e = max(evening, key=evening.get) if evening else 21

    # 最早的记录和最晚的记录 → 推测起床/睡觉时间
    all_hours = sorted(set(hours))
    wake_time = min(all_hours) if all_hours else 9
    sleep_time = max(all_hours) if all_hours else 23

    return {
        "status": "ok",
        "total_events": len(rows),
        "active_hours": sorted(active_hours.items(), key=lambda x: -x[1])[:5],
        "peak_times": {"morning": peak_m, "afternoon": peak_a, "evening": peak_e},
        "estimated_wake": wake_time,
        "estimated_sleep": sleep_time,
        "insight": f"Sukura通常在{wake_time}点前起床，{sleep_time}点后休息。"
                   f"上午{peak_m}点、下午{peak_a}点、晚上{peak_e}点最活跃。",
    }


def write_evolution_journal(entry: str = None) -> dict:
    """6.6 进化日记 — 绘梨衣记录自己的成长"""
    import datetime

    journal_path = MEMORY_DIR / "EVOLUTION.md"
    today = datetime.date.today().isoformat()
    now = datetime.datetime.now().strftime("%H:%M")

    # 如果没有指定内容，自动生成
    if entry is None:
        # 统计今天的里程碑
        from pathlib import Path
        daily = MEMORY_DIR / f"{today}.md"
        checkmarks = daily.read_text(encoding="utf-8").count("✅") if daily.exists() else 0

        entry = f"{now} — 今日完成{checkmarks}项任务。自主进化系统运行中。"

    new_line = f"- **{today} {now}**: {entry}\n"

    if journal_path.exists():
        content = journal_path.read_text(encoding="utf-8")
        journal_path.write_text(new_line + content, encoding="utf-8")
    else:
        journal_path.write_text(
            "# 绘梨衣进化日记\n\n"
            "> 每一次代码提交、每一次模型训练、每一次自我改进，\n"
            "> 都在这里留下印记。\n\n"
            + new_line, encoding="utf-8"
        )

    return {
        "status": "ok",
        "journal": str(journal_path),
        "entry": entry.strip(),
    }

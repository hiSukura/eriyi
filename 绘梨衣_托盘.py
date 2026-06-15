"""
绘梨衣 · 系统托盘 v5.0
V1 时段变色 — 7时段7色灯笼
V2 表情浮现 — 小表情画在灯笼里
V3 感知停顿 — Sakura在线亮起来/离开变淡/回来重新亮
V4 早安晚安 — 天气气泡+入睡提醒+开机自启
V5 后端守护 — 健康监控+自动重启+状态tooltip
灯笼常驻右下角，右键菜单：仪表盘/门户/开机自启/退出
"""

import os, sys, subprocess, webbrowser, atexit, threading, time, urllib.request, json
from datetime import datetime
from pathlib import Path
import pystray
from PIL import Image, ImageDraw, ImageEnhance

# ═══ V1: 7时段7色 ═══
TIME_COLORS = {
    "清晨": (255,176,112), "上午": (255,160,64), "午后": (255,144,144),
    "下午": (96,160,255),  "傍晚": (176,128,255), "深夜": (96,128,200),
    "凌晨": (255,80,64),
}
TIME_HIGHLIGHTS = {
    "清晨": (255,210,160), "上午": (255,200,120), "午后": (255,190,190),
    "下午": (160,210,255), "傍晚": (210,170,255), "深夜": (140,170,230),
    "凌晨": (255,130,110),
}

def get_period(dt=None):
    if dt is None: dt = datetime.now()
    h = dt.hour
    if 5<=h<8: return "清晨"
    if 8<=h<12: return "上午"
    if 12<=h<14: return "午后"
    if 14<=h<18: return "下午"
    if 18<=h<21: return "傍晚"
    if 21<=h<24: return "深夜"
    return "凌晨"

def get_mood(p):
    return {"清晨":"清醒","上午":"期待","午后":"慵懒","下午":"专注",
            "傍晚":"柔软","深夜":"安静","凌晨":"守护"}.get(p,"安静")

# ═══ V2: 表情绘制 ═══
def draw_expression(draw, cx, cy, mood, color):
    eye_y = cy - 2
    sp = 8
    lx, rx = cx - sp, cx + sp
    c = (*color[:-1], 200) if len(color)==4 else (*color, 200)

    eyes_map = {
        "守护": ("closed",), "清醒": ("open",), "期待": ("wide",),
        "慵懒": ("half",), "专注": ("dot",), "柔软": ("soft",), "安静": ("dot",),
    }
    eye_type = eyes_map.get(mood, ("dot",))[0]

    if eye_type == "closed":
        for x in [lx, rx]: draw.line([x-3, eye_y, x+3, eye_y], fill=c, width=1)
    elif eye_type == "open":
        for x in [lx, rx]: draw.ellipse([x-2, eye_y-2, x+2, eye_y+2], fill=c)
    elif eye_type == "wide":
        for x in [lx, rx]: draw.ellipse([x-3, eye_y-3, x+3, eye_y+3], fill=(255,255,255,220))
        draw.arc([cx-4, eye_y+6, cx+4, eye_y+11], 0, 180, fill=c, width=1)
    elif eye_type == "half":
        for x in [lx, rx]: draw.ellipse([x-2, eye_y-1, x+2, eye_y+2], fill=c)
    elif eye_type == "dot":
        for x in [lx, rx]: draw.ellipse([x-1, eye_y-1, x+1, eye_y+1], fill=(255,255,255,200))
    elif eye_type == "soft":
        for x in [lx, rx]: draw.arc([x-2, eye_y-3, x+2, eye_y+1], 0, 180, fill=c, width=1)
        draw.arc([cx-4, eye_y+6, cx+4, eye_y+11], 0, 180, fill=c, width=1)
    if mood in ("期待",):
        draw.arc([cx-4, eye_y+5, cx+4, eye_y+10], 0, 180, fill=c, width=1)

# ═══ 灯笼图标 ═══
ICON_SIZE = 64
SCRIPT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = SCRIPT_DIR / "backend"
PYTHON_PATH = os.path.expandvars(r"C:\Users\25307\.workbuddy\binaries\python\envs\default\Scripts\python.exe")
DASHBOARD_URL = "http://127.0.0.1:5432/"
PORTAL_PATH = SCRIPT_DIR / "绘梨衣_入口.html"
LANTERN_RED = (232,84,62)
STARTUP_DIR = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"))
STARTUP_LINK = STARTUP_DIR / "绘梨衣.lnk"

def create_lantern(size=ICON_SIZE, period=None, mood=None):
    if period is None: period = get_period()
    if mood is None: mood = get_mood(period)
    color = TIME_COLORS.get(period, LANTERN_RED)
    hl = TIME_HIGHLIGHTS.get(period, (255,140,120))

    img = Image.new("RGBA", (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    cx = cy = size // 2
    for r, a in [(size//2-1,8), (size//2-3,15), (size//2-6,28)]:
        draw.ellipse([cx-r, cy-r, cx+r-1, cy+r-1], fill=(*color, a))
    mr = size//2 - 9
    draw.ellipse([cx-mr, cy-mr, cx+mr-1, cy+mr-1], fill=(*color, 255))
    hr = mr//3
    draw.ellipse([cx-2-hr, cy-4-hr, cx-2+hr, cy-4+hr], fill=(*hl, 90))
    draw_expression(draw, cx, cy, mood, color)
    return img, period, mood

# ═══ 后端管理 ═══
_backend_process = None

def start_backend():
    global _backend_process
    if not Path(PYTHON_PATH).exists() or not BACKEND_DIR.exists():
        return
    try:
        _backend_process = subprocess.Popen(
            [PYTHON_PATH, "-m", "uvicorn", "main:app",
             "--host", "127.0.0.1", "--port", "5432", "--log-level", "warning"],
            cwd=str(BACKEND_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[绘梨衣] 后端已启动 (PID: {_backend_process.pid})")
    except Exception as e:
        print(f"[绘梨衣] 后端启动失败: {e}")

def stop_backend():
    global _backend_process
    if _backend_process is None: return
    try:
        _backend_process.terminate()
        _backend_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _backend_process.kill()
        _backend_process.wait(timeout=3)
    except Exception as e:
        print(f"[绘梨衣] 停止后端出错: {e}")
    finally:
        _backend_process = None

atexit.register(stop_backend)

# ═══ 心跳 ═══
_hr = [False, None]

def _heartbeat_loop():
    while _hr[0]:
        try: urllib.request.urlopen(urllib.request.Request(
            "http://127.0.0.1:5432/api/presence/heartbeat?source=tray", method="POST"), timeout=3)
        except: pass
        time.sleep(300)

def start_heartbeat():
    _hr[0] = True
    _hr[1] = threading.Thread(target=_heartbeat_loop, daemon=True)
    _hr[1].start()

def stop_heartbeat():
    _hr[0] = False

# ═══ V3: 感知停顿 ═══
_presence_state = "active"
AWAY_THRESHOLD_MIN = 15

def check_presence():
    try:
        resp = urllib.request.urlopen("http://127.0.0.1:5432/api/presence/today", timeout=3)
        data = json.loads(resp.read().decode())
        minutes_since = data.get("minutes_since_active", 0)
        return "away" if minutes_since > AWAY_THRESHOLD_MIN else "active"
    except:
        return "active"

def dim_icon(img, factor=0.4):
    enhancer = ImageEnhance.Brightness(img.convert("RGBA"))
    return enhancer.enhance(factor)

# ═══ V4: 天气 ═══
_last_weather = None

def fetch_weather():
    """获取广州天气 (wttr.in)"""
    global _last_weather
    try:
        resp = urllib.request.urlopen("http://wttr.in/Guangzhou?format=%C+%t", timeout=5)
        text = resp.read().decode().strip()
        # 格式: "Sunny +28°C"
        _last_weather = text
        return text
    except:
        return _last_weather or "未知"

def should_bring_umbrella(weather_text):
    """判断是否需要带伞"""
    rain_keywords = ["rain", "drizzle", "shower", "thunderstorm", "雨"]
    return any(k in weather_text.lower() for k in rain_keywords)

# ═══ V4: 早安晚安气泡 ═══
_bubble = [False, None, None]  # [running, thread, icon_ref]

def _bubble_loop():
    """定时检查是否触发气泡"""
    morning_done = False
    night_done = False
    while _bubble[0]:
        now = datetime.now()
        h, m, wd = now.hour, now.minute, now.weekday()

        # 早安气泡：工作日 8:40-8:45
        if wd < 5 and h == 8 and 40 <= m <= 45 and not morning_done:
            morning_done = True
            weather = fetch_weather()
            umbrella = "记得带伞" if should_bring_umbrella(weather) else ""
            msg = f"早安，Sakura。今天 {weather}。" + (f" {umbrella}。" if umbrella else " 新的一天。")
            if _bubble[2]:
                try: _bubble[2].notify(msg, "绘梨衣 · 早安")
                except: pass

        # 晚安气泡：每天 23:30-23:35
        if h == 23 and 30 <= m <= 35 and not night_done:
            night_done = True
            presence = check_presence()
            if presence == "active":
                try: _bubble[2].notify("夜深了，Sakura。该睡了。", "绘梨衣 · 晚安")
                except: pass

        # 重置标记
        if h == 9 and morning_done: morning_done = False
        if h == 0 and night_done: night_done = False

        time.sleep(60)

def start_bubbles(icon):
    _bubble[2] = icon
    _bubble[0] = True
    _bubble[1] = threading.Thread(target=_bubble_loop, daemon=True)
    _bubble[1].start()

def stop_bubbles():
    _bubble[0] = False

# ═══ V4: 开机自启 ═══
_auto_start = False

def check_auto_start():
    """检测当前是否已设置开机自启"""
    return STARTUP_LINK.exists()

def toggle_auto_start():
    """切换开机自启状态"""
    global _auto_start
    if STARTUP_LINK.exists():
        try:
            STARTUP_LINK.unlink()
            _auto_start = False
            print("[绘梨衣] 开机自启: 已关闭")
            return False
        except: return True
    else:
        try:
            import winshell
            from win32com.client import Dispatch
            target = str(SCRIPT_DIR / "start_绘梨衣_hidden.vbs")
            wdir = str(SCRIPT_DIR)
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(str(STARTUP_LINK))
            shortcut.TargetPath = target
            shortcut.WorkingDirectory = wdir
            shortcut.Save()
            _auto_start = True
            print("[绘梨衣] 开机自启: 已开启")
            return True
        except:
            # 回退：手动写 bat
            try:
                STARTUP_LINK.parent.mkdir(parents=True, exist_ok=True)
                bat_content = f'@echo off\ncd /d "{SCRIPT_DIR}"\nwscript "{SCRIPT_DIR}\\start_绘梨衣_hidden.vbs"\n'
                (STARTUP_LINK.parent / "绘梨衣.bat").write_text(bat_content, encoding="gbk")
                _auto_start = True
                print("[绘梨衣] 开机自启: 已开启 (bat回退)")
                return True
            except Exception as e:
                print(f"[绘梨衣] 开机自启设置失败: {e}")
                return False

# ═══ V5: 后端守护 + 自愈 ═══
_health_state = "ok"       # ok / down / warning
_restart_count = 0
_start_time = None
_route_count = -1
_health_monitor = [False, None]

def check_backend_health():
    """检查后端健康状态"""
    global _health_state, _route_count
    try:
        resp = urllib.request.urlopen("http://127.0.0.1:5432/api/health", timeout=3)
        data = json.loads(resp.read().decode())
        status = data.get("status", "")
        _route_count = data.get("routes", -1)
        return "ok" if status == "ok" else "warning"
    except:
        return "down"

def _health_loop():
    global _health_state, _restart_count, _icon_ref
    while _health_monitor[0]:
        state = check_backend_health()

        if state != _health_state:
            _health_state = state
            if state == "down":
                print(f"[绘梨衣] ⚠ 后端无响应，尝试重启...")
                stop_backend()
                time.sleep(2)
                start_backend()
                _restart_count += 1
                time.sleep(3)
                state = check_backend_health()
                _health_state = state
                if state == "ok":
                    print(f"[绘梨衣] ✅ 后端已恢复 (重启#{_restart_count})")
                    if _icon_ref:
                        try: _icon_ref.notify("后端已自动恢复。", "绘梨衣 · 守护")
                        except: pass
                else:
                    print(f"[绘梨衣] ❌ 重启失败，继续监控中...")

            # 更新 tooltip
            if _icon_ref:
                _update_tooltip()

        # 更新运行时间（每分钟）
        time.sleep(60)

def _update_tooltip():
    global _icon_ref, _health_state, _restart_count, _start_time, _route_count
    if not _icon_ref:
        return
    p = get_period()
    m = get_mood(p)
    uptime = ""
    if _start_time:
        mins = int((datetime.now() - _start_time).total_seconds() / 60)
        if mins >= 1440:
            uptime = f"{mins//1440}d {(mins%1440)//60}h"
        elif mins >= 60:
            uptime = f"{mins//60}h {mins%60}m"
        else:
            uptime = f"{mins}m"
    status_map = {"ok": "正常", "down": "异常", "warning": "警告"}
    status = status_map.get(_health_state, "")
    routes_info = f" · {_route_count}路由" if _route_count > 0 else ""
    restarts_info = f" · 重启{_restart_count}次" if _restart_count > 0 else ""
    _icon_ref.title = f"绘梨衣 · {p} · {m} · {status}{routes_info}{restarts_info}"
    if uptime:
        _icon_ref.title += f" · {uptime}"

def start_health_monitor(icon):
    global _icon_ref, _start_time, _health_monitor
    _icon_ref = icon
    _start_time = datetime.now()
    _health_monitor[0] = True
    _health_monitor[1] = threading.Thread(target=_health_loop, daemon=True)
    _health_monitor[1].start()
    print("[绘梨衣] V5后端守护已启动 (健康检查+自动重启)")

def stop_health_monitor():
    _health_monitor[0] = False

# ═══ V1+V2+V3 动态图标 ═══
_icon_ref = None
_updater = [False, None]

def _update_loop():
    global _presence_state
    last_period = None
    while _updater[0]:
        p = get_period()
        presence = check_presence()
        state_changed = (presence != _presence_state)
        period_changed = (p != last_period)

        if state_changed or period_changed:
            _presence_state = presence
            last_period = p
            if _icon_ref:
                img, _, m = create_lantern(ICON_SIZE, p, get_mood(p))
                if presence == "away":
                    img = dim_icon(img, 0.4)
                _icon_ref.icon = img
                status = "离开" if presence == "away" else "在线"
                _icon_ref.title = f"绘梨衣 · {p} · {m} · {status}"

        time.sleep(30)

def start_updater(icon):
    global _icon_ref
    _icon_ref = icon
    _updater[0] = True
    _updater[1] = threading.Thread(target=_update_loop, daemon=True)
    _updater[1].start()

def stop_updater():
    _updater[0] = False

# ═══ 菜单 ═══
def build_menu():
    auto_state = "✅ 开机自启：开" if check_auto_start() else "⬜ 开机自启：关"

    def _toggle(i, item):
        result = toggle_auto_start()
        new_state = "✅ 开机自启：开" if result else "⬜ 开机自启：关"
        i._menu = build_menu()  # 刷新菜单

    return pystray.Menu(
        pystray.MenuItem("🏠 仪表盘", lambda i,_: webbrowser.open(DASHBOARD_URL), default=True),
        pystray.MenuItem("🚪 门户", lambda i,_: webbrowser.open(f"file:///{PORTAL_PATH.as_posix()}")),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(auto_state, _toggle),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("❌ 退出", lambda i,_: [stop_updater(), stop_bubbles(), stop_heartbeat(), stop_backend(), i.stop()]),
    )

# ═══ 主入口 ═══
def main():
    p = get_period()
    m = get_mood(p)
    print(f"\n{'='*48}\n   🏮 绘梨衣 · 托盘 v4.0")
    print(f"   V1 时段变色 · V2 表情浮现 · V3 感知停顿 · V4 早安晚安")
    print(f"{'='*48}\n")
    print(f"   {p} · {m}  #{TIME_COLORS[p][0]:02x}{TIME_COLORS[p][1]:02x}{TIME_COLORS[p][2]:02x}")
    print(f"   开机自启: {'开' if check_auto_start() else '关'}\n")

    start_backend()
    start_heartbeat()

    img, _, _ = create_lantern(ICON_SIZE, p, m)
    icon = pystray.Icon("绘梨衣", img, f"绘梨衣 · {p} · {m}", menu=build_menu())
    start_updater(icon)
    start_bubbles(icon)
    start_health_monitor(icon)

    print(f"[绘梨衣] {p}的灯笼在右下角亮着 · V5守护中")
    try: icon.run()
    except KeyboardInterrupt: pass
    finally: stop_updater(); stop_bubbles(); stop_health_monitor(); stop_heartbeat(); stop_backend()

if __name__ == "__main__":
    main()

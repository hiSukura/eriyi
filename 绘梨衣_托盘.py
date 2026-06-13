"""
绘梨衣 · 系统托盘
灯笼图标常驻右下角系统托盘，右键菜单直达仪表盘/门户/退出。
启动时自动拉起 FastAPI 后端，退出时停止所有服务。

使用方式:
    python 绘梨衣_托盘.py
    或双击运行（需关联 Python）
"""

import os
import sys
import signal
import subprocess
import webbrowser
import atexit
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

# ═══════════════════════════════════════════════════
# 路径与常量
# ═══════════════════════════════════════════════════

SCRIPT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = SCRIPT_DIR / "backend"
PROJECT_ROOT = SCRIPT_DIR

PYTHON_PATH = os.path.expandvars(
    r"C:\Users\25307\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
)

DASHBOARD_URL = "http://127.0.0.1:5432/"
PORTAL_PATH = PROJECT_ROOT / "绘梨衣_入口.html"

LANTERN_RED = (232, 84, 62)       # #E8543E — 灯笼红
LANTERN_GLOW = (255, 100, 75)    # 高光
ICON_SIZE = 64

# ═══════════════════════════════════════════════════
# 灯笼图标生成
# ═══════════════════════════════════════════════════

def create_lantern_icon(size: int = ICON_SIZE) -> Image.Image:
    """
    程序化生成灯笼图标：红色圆形主体 + 多层发光晕 + 高光。
    零外部图片依赖。
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = size // 2
    cy = size // 2

    # 逐层外发光晕（从大到小，从透明到半透明）
    halos = [
        (size // 2 - 1,  8),   # 最外层极其淡
        (size // 2 - 3,  15),  # 中层稍亮
        (size // 2 - 6,  28),  # 内层明显
    ]
    for radius, alpha in halos:
        r, g, b = LANTERN_RED
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius - 1, cy + radius - 1],
            fill=(r, g, b, alpha),
        )

    # 主体圆 — 灯笼红实心
    main_radius = size // 2 - 9
    draw.ellipse(
        [cx - main_radius, cy - main_radius,
         cx + main_radius - 1, cy + main_radius - 1],
        fill=(*LANTERN_RED, 255),
    )

    # 左上高光 — 让灯笼「亮起来」
    hl_radius = main_radius // 3
    hl_offset_x = -2
    hl_offset_y = -4
    draw.ellipse(
        [cx + hl_offset_x - hl_radius, cy + hl_offset_y - hl_radius,
         cx + hl_offset_x + hl_radius, cy + hl_offset_y + hl_radius],
        fill=(255, 140, 120, 90),
    )

    # 更小的二次高光
    hl2_radius = hl_radius // 2
    draw.ellipse(
        [cx + hl_offset_x - hl2_radius, cy + hl_offset_y - hl2_radius - 2,
         cx + hl_offset_x + hl2_radius, cy + hl_offset_y + hl2_radius - 2],
        fill=(255, 180, 160, 100),
    )

    return img


# ═══════════════════════════════════════════════════
# 后端进程管理
# ═══════════════════════════════════════════════════

_backend_process = None


def start_backend():
    """启动 FastAPI 后端（子进程）"""
    global _backend_process

    # 检查 Python 路径是否存在
    if not Path(PYTHON_PATH).exists():
        print(f"[绘梨衣] ⚠ Python 环境未找到: {PYTHON_PATH}")
        print("[绘梨衣] 后端服务无法启动，但托盘仍会运行。")
        return

    if not BACKEND_DIR.exists():
        print(f"[绘梨衣] ⚠ 后端目录未找到: {BACKEND_DIR}")
        return

    print(f"[绘梨衣] 启动后端服务...")
    print(f"   Python:  {PYTHON_PATH}")
    print(f"   目录:    {BACKEND_DIR}")

    try:
        _backend_process = subprocess.Popen(
            [
                PYTHON_PATH, "-m", "uvicorn", "main:app",
                "--host", "127.0.0.1", "--port", "5432",
                "--log-level", "warning",
            ],
            cwd=str(BACKEND_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[绘梨衣] 后端已启动 (PID: {_backend_process.pid})")

    except FileNotFoundError:
        print("[绘梨衣] ⚠ uvicorn 未安装或路径错误")
    except Exception as e:
        print(f"[绘梨衣] ⚠ 后端启动失败: {e}")


def stop_backend():
    """停止后端进程"""
    global _backend_process
    if _backend_process is None:
        return

    print("[绘梨衣] 停止后端服务...")
    try:
        _backend_process.terminate()
        _backend_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        print("[绘梨衣] 后端未响应，强制终止...")
        _backend_process.kill()
        _backend_process.wait(timeout=3)
    except Exception as e:
        print(f"[绘梨衣] 停止后端时出错: {e}")
    finally:
        _backend_process = None
        print("[绘梨衣] 后端已停止")


# 确保退出时清理
atexit.register(stop_backend)


# ═══════════════════════════════════════════════════
# 菜单动作
# ═══════════════════════════════════════════════════

def action_dashboard(icon, item):
    """打开仪表盘 → http://127.0.0.1:5432/"""
    webbrowser.open(DASHBOARD_URL)


def action_portal(icon, item):
    """打开门户 → 绘梨衣_入口.html"""
    portal_url = f"file:///{PORTAL_PATH.as_posix()}"
    webbrowser.open(portal_url)


def action_quit(icon, item):
    """退出 — 停止后端 + 移除托盘图标"""
    print("[绘梨衣] 收到退出指令...")
    stop_backend()
    icon.stop()
    print("[绘梨衣] 托盘已退出，再见 Sakura 👋")


# ═══════════════════════════════════════════════════
# 菜单构建
# ═══════════════════════════════════════════════════

def build_menu():
    """构建右键菜单"""
    return pystray.Menu(
        pystray.MenuItem(
            "🏠 仪表盘",
            action_dashboard,
            default=True,  # 左键双击默认
        ),
        pystray.MenuItem(
            "🚪 门户",
            action_portal,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "❌ 退出",
            action_quit,
        ),
    )


# ═══════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════

def main():
    print()
    print("=" * 44)
    print("   🏮  绘 梨 衣 · 系 统 托 盘")
    print("   灯笼常驻右下角 · 右键唤醒")
    print("=" * 44)
    print()

    # 1. 启动后端
    start_backend()

    # 2. 生成灯笼图标
    icon_image = create_lantern_icon(ICON_SIZE)

    # 3. 创建托盘
    icon = pystray.Icon(
        name="绘梨衣",
        icon=icon_image,
        title="绘梨衣 🔴",
        menu=build_menu(),
    )

    print("[绘梨衣] 托盘已启动 —— 灯笼在右下角亮着 🏮")
    print("[绘梨衣] 右键 → 仪表盘/门户/退出")
    print()

    # 4. 运行消息循环（阻塞直到 icon.stop()）
    try:
        icon.run()
    except KeyboardInterrupt:
        pass
    finally:
        stop_backend()


if __name__ == "__main__":
    main()

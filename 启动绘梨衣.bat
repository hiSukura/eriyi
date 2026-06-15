@echo off
chcp 65001 >nul
title 绘梨衣 · 启动器

set PYTHON=C:\Users\25307\.workbuddy\binaries\python\envs\default\Scripts\python.exe
set PORT=5432
set BACKEND_DIR=%~dp0backend
set START_URL=/绘梨衣_pwa.html

cls
echo.
echo   ╔══════════════════════════════════════╗
echo   ║      绘梨衣 · 正在启动              ║
echo   ║                                     ║
echo   ║  搭档已就绪。                       ║
echo   ╚══════════════════════════════════════╝
echo.

if not exist "%PYTHON%" (
    echo [✕] Python 环境未找到: %PYTHON%
    pause
    exit /b 1
)
echo [✓] Python 环境

REM ── 清理旧进程 ──
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

REM ── 启动后端 ──
start "绘梨衣 · 后端" /min cmd /c "cd /d \"%BACKEND_DIR%\" && \"%PYTHON%\" -m uvicorn main:app --host 0.0.0.0 --port %PORT% --log-level info"
echo [✓] 后端服务已启动 (首次启动需等待模型加载)

REM ── 打开浏览器 ──
start http://127.0.0.1:%PORT%%START_URL%

REM ── 获取局域网 IP ──
set LAN_IP=
for /f "delims=" %%a in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -match '^192\.|^10\.|^172\.'} | Select-Object -First 1).IPAddress" 2^>nul') do set LAN_IP=%%a
if not defined LAN_IP set LAN_IP=127.0.0.1

cls
echo.
echo   ╔══════════════════════════════════════╗
echo   ║    绘梨衣 · 已就绪                  ║
echo   ╚══════════════════════════════════════╝
echo.
echo   ─── 本机访问 ───
echo   主页:   http://127.0.0.1:%PORT%%START_URL%
echo   仪表盘: http://127.0.0.1:%PORT%/
echo.
echo   ─── 手机访问 ───
echo   地址:   http://%LAN_IP%:%PORT%%START_URL%
echo.
echo   手机和电脑需要在同一 Wi-Fi 下
echo   如果页面首次打开是空白，等模型加载完刷新即可
echo.
echo   按任意键关闭后端并退出
echo   直接关此窗口 = 后端继续在后台运行
echo.
pause >nul

echo [~] 正在关闭绘梨衣...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)
echo [✓] 已关闭。下次再见，Sakura。
timeout /t 2 /nobreak >nul

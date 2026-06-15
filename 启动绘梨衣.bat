@echo off
chcp 65001 >nul
title 绘梨衣 · 启动器

setlocal enabledelayedexpansion

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

REM ── 检查 Python ──
if not exist "%PYTHON%" (
    echo [✕] Python 环境未找到
    echo     路径: %PYTHON%
    pause
    exit /b 1
)
echo [✓] Python 环境

REM ── 清理旧端口进程 ──
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

REM ── 启动后端（新窗口，最小化，工作目录 backend） ──
start "绘梨衣 · 后端" /min cmd /c "cd /d \"%BACKEND_DIR%\" && \"%PYTHON%\" -m uvicorn main:app --host 0.0.0.0 --port %PORT% --log-level info"
echo [✓] 后端服务已启动  (端口 %PORT%)

REM ── 等待后端就绪 ──
echo [~] 等待后端就绪...
set WAIT_MAX=15
set WAIT_COUNT=0
:WAIT_LOOP
timeout /t 1 /nobreak >nul
set /a WAIT_COUNT+=1
if %WAIT_COUNT% gtr %WAIT_MAX% (
    echo [!] 后端启动较慢，继续尝试打开页面...
    goto :READY
)
>"%TEMP%\eriyi_check.txt" 2>&1 curl -s http://127.0.0.1:%PORT%/api/health
findstr "ok" "%TEMP%\eriyi_check.txt" >nul 2>&1
if errorlevel 1 goto WAIT_LOOP
:READY
del "%TEMP%\eriyi_check.txt" 2>nul
echo [✓] 后端响应正常

REM ── 获取局域网 IP ──
set LAN_IP=
for /f "delims=" %%a in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -match '^192\.|^10\.|^172\.'} | Select-Object -First 1).IPAddress" 2^>nul') do set LAN_IP=%%a
if not defined LAN_IP set LAN_IP=127.0.0.1

REM ── 打开浏览器 ──
start http://127.0.0.1:%PORT%/page/绘梨衣
timeout /t 1 /nobreak >nul
start http://127.0.0.1:%PORT%%START_URL%

cls
echo.
echo   ╔══════════════════════════════════════╗
echo   ║    绘梨衣 · 已就绪                  ║
echo   ╚══════════════════════════════════════╝
echo.
echo   ─── 本机访问 ───
echo   主页:   http://127.0.0.1:%PORT%%START_URL%
echo   仪表盘: http://127.0.0.1:%PORT%/
echo   接口:   http://127.0.0.1:%PORT%/docs
echo.
echo   ─── 手机访问 ───
echo   地址:   http://%LAN_IP%:%PORT%%START_URL%
echo.
echo   手机和电脑需要在同一 Wi-Fi 下
echo   在手机浏览器输入上面的地址
echo.
echo   ─── 操作 ───
echo   按 Q 关闭服务并退出
echo   直接关窗口 = 后端继续在后台运行
echo.

:LOOP
choice /c Q /n /t 86400 /d Q /m "按 Q 退出 > "
if errorlevel 1 (
    echo.
    echo [~] 正在关闭绘梨衣...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
        taskkill /f /pid %%a >nul 2>&1
    )
    echo [✓] 已关闭。下次再见，Sakura。
    timeout /t 2 /nobreak >nul
    exit /b 0
)
goto LOOP

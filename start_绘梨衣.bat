@echo off
chcp 65001 >nul
title 绘梨衣 · 本地服务

echo.
echo   ============================================
echo          绘梨衣 本地服务 启动中...
echo   ============================================
echo.

cd /d "%~dp0backend"

REM 使用隔离环境中的 Python
set PYTHON=C:\Users\25307\.workbuddy\binaries\python\envs\default\Scripts\python.exe

if not exist "%PYTHON%" (
    echo [错误] Python 环境未找到
    echo 路径: %PYTHON%
    pause
    exit /b 1
)

echo [绘梨衣] Python 环境: %PYTHON%
echo [绘梨衣] 工作目录: %cd%
echo.

REM 启动 uvicorn
"%PYTHON%" -m uvicorn main:app --host 127.0.0.1 --port 5432 --log-level info

pause

@echo off
cd /d "%~dp0"
title 绘梨衣 3D
set NODE=C:\Users\25307\.workbuddy\binaries\node\versions\22.22.2\node.exe
if not exist "%NODE%" set NODE=node

echo [*] 绘梨衣 3D · 启动中...
start "绘梨衣3D" /MIN %NODE% server.js
timeout /t 2 /nobreak >nul

:: Chrome --app
where chrome >nul 2>&1 && (
  start chrome --app=http://localhost:3901 --window-size=440,660
  goto :end
)
where msedge >nul 2>&1 && (
  start msedge --app=http://localhost:3901 --window-size=440,660
  goto :end
)
start http://localhost:3901

:end
echo [*] http://localhost:3901
exit

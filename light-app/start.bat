@echo off
title Erii Light

:: Use managed Node.js (absolute path, avoids PATH/NODE_OPTIONS issues)
set NODE=C:\Users\25307\.workbuddy\binaries\node\versions\22.22.2\node.exe
if not exist "%NODE%" set NODE=node

echo.
echo [*] Erii Light - Starting...
echo.

cd /d "%~dp0"

:: Start server
start "EriiLightServer" /MIN %NODE% server.js

timeout /t 2 /nobreak >nul

:: Get screen position via VBScript (no encoding issues)
set POS=100,100
for /f "tokens=*" %%i in ('cscript //nologo "%~dp0get_screen.vbs"') do set POS=%%i
echo [*] Position: %POS%

:: Launch in --app mode
where msedge >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo -^> Edge --app mode ^| 320x320
    start msedge --app=http://localhost:3900 --window-size=320,320 --window-position=%POS% --disable-extensions --disable-sync
    goto :done
)

where chrome >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo -^> Chrome --app mode ^| 320x320
    start chrome --app=http://localhost:3900 --window-size=320,320 --window-position=%POS% --disable-extensions
    goto :done
)

echo -^> Default browser
start http://localhost:3900

:done
echo.
echo [*] Light running on port 3900
echo     Close server window to stop
echo.
pause

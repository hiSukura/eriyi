# 绘梨衣 · PowerShell 启动脚本
# 双击运行或在终端执行: .\start_绘梨衣.ps1

$ErrorActionPreference = "Stop"
$host.UI.RawUI.WindowTitle = "绘梨衣 · 本地服务"

Write-Host ""
Write-Host "  ============================================"  -ForegroundColor Red
Write-Host "       绘梨衣 本地服务 启动中..."            -ForegroundColor Red
Write-Host "  ============================================"  -ForegroundColor Red
Write-Host ""

# 切换到 backend 目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$scriptDir\backend"

# Python 路径
$pythonPath = "C:\Users\25307\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

if (-not (Test-Path $pythonPath)) {
    Write-Host "[错误] Python 环境未找到: $pythonPath" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

Write-Host "[绘梨衣] Python: $pythonPath"
Write-Host "[绘梨衣] 工作目录: $(Get-Location)"
Write-Host "[绘梨衣] 仪表盘: http://127.0.0.1:5432/"
Write-Host "[绘梨衣] API文档: http://127.0.0.1:5432/docs"
Write-Host ""

# 启动服务
& $pythonPath -m uvicorn main:app --host 127.0.0.1 --port 5432 --log-level info

Write-Host ""
Write-Host "[绘梨衣] 服务已停止。" -ForegroundColor Red
Read-Host "按回车关闭窗口"

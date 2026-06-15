# 绘梨衣 · 光点 启动脚本 (PowerShell)
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host ""
Write-Host "🔴 绘梨衣 · 光点 — 启动中..." -ForegroundColor Red
Write-Host ""

# 启动本地服务器（后台）
$serverJob = Start-Job -ScriptBlock {
    Set-Location $using:scriptDir
    node server.js
}

Start-Sleep -Seconds 2

# 尝试 Edge --app 模式
$edge = Get-Command msedge -ErrorAction SilentlyContinue
$chrome = Get-Command chrome -ErrorAction SilentlyContinue

if ($edge) {
    Write-Host "→ 使用 Edge --app 模式" -ForegroundColor Yellow
    Start-Process msedge -ArgumentList "--app=http://localhost:3900", "--window-size=320,320", "--disable-extensions", "--disable-sync"
}
elseif ($chrome) {
    Write-Host "→ 使用 Chrome --app 模式" -ForegroundColor Yellow
    Start-Process chrome -ArgumentList "--app=http://localhost:3900", "--window-size=320,320", "--disable-extensions"
}
else {
    Write-Host "→ 使用默认浏览器" -ForegroundColor Yellow
    Start-Process "http://localhost:3900"
}

Write-Host ""
Write-Host "🔴 光点已启动 | 端口: 3900 | 按 Ctrl+C 停止服务器"
Write-Host ""

# 保持运行，等待 Ctrl+C
try {
    while ($true) { Start-Sleep -Seconds 1 }
}
finally {
    Stop-Job $serverJob
    Remove-Job $serverJob
    Write-Host "🔴 光点已休眠" -ForegroundColor Red
}

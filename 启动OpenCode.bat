@echo off
:: 绘梨衣 · OpenCode 网页版 启动脚本
:: 双击打开浏览器访问 http://127.0.0.1:4000

set DEEPSEEK_API_KEY=sk-17d16f9df1124224a4ee361fc12d1736
set PATH=C:\Users\25307\.workbuddy\binaries\node\versions\22.22.2;%PATH%

start "" http://127.0.0.1:4000
cd /d E:\WorkSpaceForWorkbuddy\绘梨衣
opencode web --port 4000

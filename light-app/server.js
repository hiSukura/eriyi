// 绘梨衣光点 · 本地静态服务器
// 用途：解决 file:// 协议下 ES Module 的 CORS 限制
// 配合浏览器 --app 模式使用

const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3900;
const ROOT = __dirname;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'application/javascript',
  '.css':  'text/css',
  '.json': 'application/json',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.svg':  'image/svg+xml',
  '.ico':  'image/x-icon',
};

const server = http.createServer((req, res) => {
  let reqPath = req.url === '/' ? '/index.html' : decodeURIComponent(req.url);
  let filePath = path.join(ROOT, reqPath);
  const ext = path.extname(filePath).toLowerCase();

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('404 Not Found');
      return;
    }
    res.writeHead(200, {
      'Content-Type': MIME[ext] || 'application/octet-stream',
      'Cache-Control': 'no-cache',
      'Access-Control-Allow-Origin': '*',
    });
    res.end(data);
  });
});

server.listen(PORT, () => {
  console.log(`🔴 绘梨衣光点服务器已启动 → http://localhost:${PORT}`);
  console.log(`   浏览器打开: http://localhost:${PORT}`);
  console.log(`   --app 模式: chrome --app=http://localhost:${PORT} --window-size=300,300`);
});

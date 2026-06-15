// 绘梨衣3D · VRM等待页
const http=require('http'),fs=require('fs'),path=require('path');
const ROOT=path.resolve(__dirname,'..'),PORT=3901;
const VRM=path.join(ROOT,'visual','model','eriyi.vrm');
http.createServer((req,res)=>{
  let fp=path.join(ROOT,req.url==='/'?'/visual/index.html':decodeURIComponent(req.url));
  if(req.url==='/vrm'){res.writeHead(200,{'Content-Type':'application/json'});return res.end(JSON.stringify({ready:fs.existsSync(VRM)}));}
  fs.readFile(fp,(e,d)=>{
    if(e){res.writeHead(404);return res.end('404');}
    let ct='application/octet-stream';
    if(fp.endsWith('.html'))ct='text/html;charset=utf-8';
    if(fp.endsWith('.js'))ct='application/javascript';
    if(fp.endsWith('.vrm'))ct='model/vrm';
    res.writeHead(200,{'Content-Type':ct,'Access-Control-Allow-Origin':'*','Cache-Control':'no-cache'});
    res.end(d);
  });
}).listen(PORT,()=>console.log(`绘梨衣 http://localhost:${PORT} | VRM: ${fs.existsSync(VRM)?'✅':'⏳'}`));

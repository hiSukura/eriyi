// 绘梨衣 Service Worker · 离线缓存策略 v2.0
const CACHE_NAME = "eriyi-v2.0.0";
const PRE_CACHE_URLS = [
    "/绘梨衣_pwa.html",
    "/绘梨衣_语音馆.html",
    "/绘梨衣_记忆长廊.html",
    "/绘梨衣_日记本.html",
    "/绘梨衣_入口.html",
    "/绘梨衣.html",
    "/manifest.json",
    "/icons/icon-192.png",
    "/icons/icon-512.png",
];

// ── 安装：预缓存核心页面 ──
self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(PRE_CACHE_URLS).catch((err) => {
                console.warn("[SW] 预缓存部分失败:", err);
                // 不阻塞安装
            });
        })
    );
    self.skipWaiting();
});

// ── 激活：清理旧缓存 ──
self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((key) => key !== CACHE_NAME)
                    .map((key) => caches.delete(key))
            )
        )
    );
    self.clients.claim();
});

// ── 请求拦截：Network First，降级到缓存 ──
self.addEventListener("fetch", (event) => {
    // 跳过非 GET 和非 http(s)
    if (event.request.method !== "GET") return;
    const url = new URL(event.request.url);
    if (!url.protocol.startsWith("http")) return;

    // API 不走缓存
    if (url.pathname.startsWith("/api/")) return;

    event.respondWith(
        fetch(event.request)
            .then((response) => {
                // 成功响应 → 更新缓存
                if (response.ok) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) =>
                        cache.put(event.request, clone)
                    );
                }
                return response;
            })
            .catch(() => {
                // 网络失败 → 走缓存
                return caches.match(event.request).then((cached) => {
                    return cached || new Response("离线中，请稍后再试", { status: 503 });
                });
            })
    );
});

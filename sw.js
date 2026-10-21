const CACHE='peseteando-v2.1.0';
const SHELL=['./','./index.html','./styles.css?v=2.1.0','./app.js?v=2.1.0','./catalog.mjs','./manifest.webmanifest','./guide.json','./assets/icon-v2-192.png','./assets/icon-v2-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('peseteando-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{const url=new URL(e.request.url);if(e.request.method!=='GET'||url.origin!==self.location.origin||!url.href.startsWith(self.registration.scope))return;
 const isData=url.pathname.endsWith('/offers.json');const key=isData?new URL('offers.json',self.registration.scope).href:e.request;
 // Network first for every first-party asset; cache is a connection-loss fallback only.
 e.respondWith(fetch(e.request).then(r=>{if(r.ok){const clone=r.clone();e.waitUntil(caches.open(CACHE).then(c=>c.put(key,clone)));}return r;}).catch(async()=>{const c=await caches.open(CACHE);const hit=await c.match(key);return hit||(e.request.mode==='navigate'?await c.match('./index.html'):null)||Response.error();}));
});

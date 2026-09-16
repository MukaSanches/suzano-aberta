const CACHE = "suzano-aberta-app-v1";
const SHELL = ["./","./index.html","./styles.css","./app.js","./icon.svg","./manifest.webmanifest"];
self.addEventListener("install",event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting()));});
self.addEventListener("activate",event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener("fetch",event=>{
  if(event.request.method!=="GET") return;
  const url=new URL(event.request.url);
  if(url.origin!==self.location.origin) return;
  const isData=url.pathname.includes("/data/")||url.pathname.endsWith("/config.json");
  if(isData){
    event.respondWith(caches.open(CACHE).then(async cache=>{
      try{const fresh=await fetch(event.request,{cache:"no-store"});if(fresh.ok)cache.put(event.request,fresh.clone());return fresh;}catch(_){return (await cache.match(event.request))||new Response(JSON.stringify({offline:true}),{headers:{"Content-Type":"application/json"},status:503});}
    })); return;
  }
  event.respondWith(caches.match(event.request).then(cached=>cached||fetch(event.request).then(response=>{if(response.ok){const clone=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,clone));}return response;}).catch(()=>caches.match("./index.html"))));
});

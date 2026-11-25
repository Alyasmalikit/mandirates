var C='mr-1795585620';
self.addEventListener('install',function(e){self.skipWaiting();e.waitUntil(caches.open(C).then(function(c){return c.addAll(['/','/theme.css','/app.js','/logic.js','/icon.svg'])}))});
self.addEventListener('activate',function(e){e.waitUntil(caches.keys().then(function(k){return Promise.all(k.filter(function(x){return x!==C}).map(function(x){return caches.delete(x)}))}).then(function(){return self.clients.claim()}))});
function keep(req,r){if(r&&r.ok){var c2=r.clone();caches.open(C).then(function(c){c.put(req,c2)})}return r}
self.addEventListener('fetch',function(e){var q=e.request;if(q.method!=='GET')return;var u=new URL(q.url);if(u.origin!==location.origin)return;
if(q.mode==='navigate'){e.respondWith(fetch(q).then(function(r){return keep(q,r)}).catch(function(){return caches.match(q).then(function(m){return m||caches.match('/')})}));return}
if(u.pathname.indexOf('/api/')===0||u.pathname.indexOf('/data/')===0){e.respondWith(fetch(q).then(function(r){return keep(q,r)}).catch(function(){return caches.match(q)}));return}
e.respondWith(caches.match(q).then(function(m){var n=fetch(q).then(function(r){return keep(q,r)}).catch(function(){return m});return m||n}))});

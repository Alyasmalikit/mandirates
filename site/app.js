(function(){
var h=document.documentElement;
function ls(k,v){try{if(v===undefined)return localStorage.getItem(k);localStorage.setItem(k,v)}catch(e){return null}}
var th=ls('mr-theme'),md=ls('mr-mode');if(th)h.dataset.theme=th;if(md)h.dataset.mode=md;
var ip=null;window.addEventListener('beforeinstallprompt',function(e){e.preventDefault();ip=e;var b=document.getElementById('install');if(b)b.hidden=false});
var MR=window.MR={ls:ls,inr:function(v){return'₹'+Math.round(v).toLocaleString('en-IN')},
el:function(t,x,c){var e=document.createElement(t);if(x!=null)e.textContent=x;if(c)e.className=c;return e},
ld:function(k){try{return JSON.parse(localStorage.getItem(k)||'[]')}catch(e){return[]}},sv:function(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}};
function get(u,ms){var c=new AbortController(),t=setTimeout(function(){c.abort()},ms);return fetch(u,{signal:c.signal}).then(function(r){clearTimeout(t);if(!r.ok)throw 0;return r.json()})}
MR.prices=function(){var pack=function(j,src){var r=MRL.normaliseAll(j);if(!r.length)throw 0;return{rows:r,demo:!!(j&&j.demo),updated:(j&&j.updated)||'',source:src}};
var live=function(){return get('/api/prices?limit=1000',5000).then(function(j){return pack(j,'live')})};
return get('/data/latest.json',6000).then(function(j){var p=pack(j,'daily');if(!p.demo)return p;return live().catch(function(){return p})}).catch(function(){return live()}).catch(function(){return{rows:MRL.demo(),demo:true,updated:'',source:'sample'}})};
MR.banner=function(p,id){var e=document.getElementById(id||'dn');if(!e)return;e.hidden=!p.demo;if(p.demo)e.textContent='Sample data is shown because live prices could not be loaded. Real prices appear when the daily feed is connected.'};
MR.download=function(name,text,type){var b=new Blob([text],{type:type||'text/csv'}),a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(function(){URL.revokeObjectURL(a.href)},1000)};
MR.fill=function(sel,vals){vals.forEach(function(v){var o=document.createElement('option');o.value=v;o.textContent=v;sel.appendChild(o)})};
function ready(f){if(document.readyState!=='loading')f();else document.addEventListener('DOMContentLoaded',f)}
ready(function(){
var ib=document.getElementById('install');if(ib){ib.hidden=!ip;ib.addEventListener('click',function(){if(ip){ip.prompt();ip=null;ib.hidden=true}})}
var t=document.getElementById('th'),m=document.getElementById('md'),l=document.getElementById('lg'),hi=ls('mr-lang')==='hi';
if(t){if(th)t.value=th;t.addEventListener('input',function(){h.dataset.theme=t.value;ls('mr-theme',t.value)})}
if(m)m.addEventListener('click',function(){var dark=h.dataset.mode?h.dataset.mode==='dark':matchMedia('(prefers-color-scheme: dark)').matches;h.dataset.mode=dark?'light':'dark';ls('mr-mode',h.dataset.mode)});
var tmap=new WeakMap(),busy=false;
function tr(s){var HI=window.MRHI,k=s.trim();if(!k||!HI)return s;var v=HI.ui[k];if(v==null)v=HI.states[k];if(v==null)v=HI.crops[k.split('(')[0].trim().toLowerCase()];if(v==null){for(var i=0;i<HI.pats.length;i++){var m=k.match(HI.pats[i][0]);if(m){v=HI.pats[i][1].apply(null,m.slice(1));break}}}return v==null?s:s.replace(k,v)}
function nodes(f){var w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,{acceptNode:function(n){var p=n.parentNode&&n.parentNode.nodeName;return p==='SCRIPT'||p==='STYLE'||p==='TEXTAREA'?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT}}),n;while((n=w.nextNode()))f(n)}
var ATTR=['placeholder','aria-label','title'];
function pass(){nodes(function(n){var c=n.nodeValue,m=tmap.get(n);if(m&&c===m.t)return;var t=tr(c);tmap.set(n,{o:c,t:t});if(t!==c)n.nodeValue=t});
document.querySelectorAll('[placeholder],[aria-label],[title]').forEach(function(e){ATTR.forEach(function(a){if(!e.hasAttribute(a))return;e.__m=e.__m||{};var c=e.getAttribute(a),m=e.__m[a];if(m&&c===m.t)return;var t=tr(c);e.__m[a]={o:c,t:t};if(t!==c)e.setAttribute(a,t)})})}
function restore(){nodes(function(n){var m=tmap.get(n);if(m&&n.nodeValue===m.t)n.nodeValue=m.o});document.querySelectorAll('[placeholder],[aria-label],[title]').forEach(function(e){if(!e.__m)return;ATTR.forEach(function(a){var m=e.__m[a];if(m&&e.getAttribute(a)===m.t)e.setAttribute(a,m.o)})})}
var pend=false,obs=new MutationObserver(function(){if(!hi||pend||!window.MRHI)return;pend=true;requestAnimationFrame(function(){pend=false;if(hi){pass();obs.takeRecords()}})});
obs.observe(document.body,{childList:true,subtree:true,characterData:true});
function loadHi(cb){if(window.MRHI)return cb();var s=document.createElement('script');s.src='/hi.js';s.onload=cb;document.head.appendChild(s)}
function setDate(){var e=document.getElementById('today');if(!e)return;try{e.textContent=(hi?'आज: ':'Today: ')+new Date().toLocaleDateString(hi?'hi-IN':'en-IN',{weekday:'long',day:'numeric',month:'long',year:'numeric',timeZone:'Asia/Kolkata'})}catch(x){}}
function lang(){if(hi)loadHi(function(){pass();setDate()});else{restore();setDate()}h.lang=hi?'hi':'en';if(l)l.textContent=hi?'English':'हिन्दी'}
setDate();
if(l)l.addEventListener('click',function(){hi=!hi;ls('mr-lang',hi?'hi':'en');lang()});if(hi)lang();
document.querySelectorAll('[data-csv]').forEach(function(b){b.addEventListener('click',function(){var tb=document.getElementById(b.dataset.csv);if(!tb)return;var rows=[];tb.querySelectorAll('tr').forEach(function(tr){rows.push(Array.prototype.map.call(tr.children,function(c){var v=c.textContent.replace(/"/g,'""');return/[",\n]/.test(v)?'"'+v+'"':v}).join(','))});MR.download(b.dataset.name||'mandi-prices.csv',rows.join('\n'))})});
if('serviceWorker' in navigator)addEventListener('load',function(){navigator.serviceWorker.register('/sw.js')});
});
})();

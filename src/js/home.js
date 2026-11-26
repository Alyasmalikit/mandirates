(function(){
var $=function(i){return document.getElementById(i)},E=MR.el,inr=MR.inr,rows=[],shown=30;
function td(tr,t,c){tr.appendChild(E('td',t,c))}
function draw(){var f=MRL.filt(rows,$('q').value,$('st').value),b=$('tb');b.textContent='';f.slice(0,shown).forEach(function(r){var tr=E('tr');td(tr,r.commodity);td(tr,r.market);td(tr,r.state);td(tr,inr(r.mn),'n');td(tr,inr(r.md)+(r.odd?' ⚠':''),'n p');td(tr,inr(r.mx),'n');td(tr,r.d==null?'–':r.d>0?'▲ '+r.d:r.d<0?'▼ '+Math.abs(r.d):'–',(r.d>0?'up':r.d<0?'dn':'')+' n');td(tr,r.date);b.appendChild(tr)});
$('cnt').textContent=f.length?'Showing '+Math.min(shown,f.length)+' of '+f.length+' prices':'No prices match. Try another crop or state.';$('more').hidden=f.length<=shown}
function movers(){var m=$('mv');m.textContent='';var has=rows.some(function(r){return r.d!=null});$('mvt').textContent=has?'Top movers':'Highest prices today';
var a=has?rows.filter(function(r){return r.d!=null&&!r.odd}).sort(function(x,y){return Math.abs(y.d)-Math.abs(x.d)}):rows.filter(function(r){return!r.odd}).sort(function(x,y){return y.md-x.md});
a.slice(0,5).forEach(function(r){var li=E('li'),d=E('div'),c=E('div');d.appendChild(E('b',r.commodity));d.appendChild(E('span',r.market+', '+r.state));li.appendChild(d);if(has){c.textContent=(r.d>0?'▲ ':'▼ ')+inr(Math.abs(r.d));c.className=r.d>0?'up':'dn'}else{c.textContent=inr(r.md);c.className='p'}li.appendChild(c);m.appendChild(li)})}
MR.prices().then(function(p){rows=p.rows;MR.banner(p);var s={};rows.forEach(function(r){s[r.state]=1});MR.fill($('st'),Object.keys(s).sort());if(p.updated)$('upd').textContent='Updated '+p.updated;draw();movers()});
['q','st'].forEach(function(i){$(i).addEventListener('input',function(){shown=30;draw()})});
$('more').addEventListener('click',function(){shown+=30;draw()});
$('sf').addEventListener('submit',function(e){e.preventDefault();$('prices').scrollIntoView()});
})();

(function(){
var $=function(i){return document.getElementById(i)},E=MR.el,NOW=Date.now(),kind='sell',LIMIT=3,CFG=window.MR_CONFIG||{},LIVE=!!(CFG.supabaseUrl&&CFG.supabaseKey),L=[],loadErr='';
function getSess(){try{var s=JSON.parse(localStorage.getItem('mr-sess')||'null');return MRL.sessionOk(s,Date.now())?s:null}catch(e){return null}}
var MODE=(CFG.authMode==='phone')?'phone':'email',sess=getSess();
var emailOk=function(x){return/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(x)&&x.length<=80};
function api(path,o,tok){o=o||{};var h={apikey:CFG.supabaseKey,'Content-Type':'application/json',Authorization:'Bearer '+(tok||CFG.supabaseKey)};if(o.prefer)h.Prefer=o.prefer;
return fetch(CFG.supabaseUrl+path,{method:o.method||'GET',headers:h,body:o.body?JSON.stringify(o.body):undefined}).then(function(r){return r.text().then(function(t){var j=null;try{j=t?JSON.parse(t):null}catch(e){}if(!r.ok)throw new Error((j&&(j.msg||j.message||j.error_description||j.hint))||'Something went wrong. Please try again.');return j})})}
// ---- demo data (used only when no database is configured) ----
var DEMO=[{id:1,kind:'sell',crop:'Wheat',qty:200,price:2450,state:'Punjab',district:'Ludhiana',phone:'9876543210',note:'Dara variety, clean, ready for loading',ver:1,at:NOW-3e6},{id:2,kind:'buy',crop:'Onion',qty:500,price:1700,state:'Maharashtra',district:'Nashik',phone:'9812345678',note:'Need red onion, 55mm+, weekly supply',ver:1,at:NOW-9e6},{id:3,kind:'sell',crop:'Soybean',qty:150,price:4450,state:'Madhya Pradesh',district:'Indore',phone:'9988776655',note:'Yellow, moisture below 12%',ver:0,at:NOW-2e7},{id:4,kind:'sell',crop:'Rice',qty:300,price:3250,state:'Haryana',district:'Karnal',phone:'9123456780',note:'Basmati 1121, new crop',ver:1,at:NOW-4e7},{id:5,kind:'buy',crop:'Wheat',qty:1000,price:2480,state:'Rajasthan',district:'Kota',phone:'9001122334',note:'Flour mill, monthly purchase',ver:1,at:NOW-6e7},{id:6,kind:'sell',crop:'Tomato',qty:80,price:2100,state:'Maharashtra',district:'Nashik',phone:'9700011122',note:'Grade A crates',ver:0,at:NOW-8e7}];
var mine=MR.ld('mr-list'),today=new Date().toISOString().slice(0,10),used=MR.ld('mr-used');if(used.day!==today)used={day:today,ids:[]};
function usedList(){return(used&&used.ids)||[]}
function fill(id,key){var s={};L.forEach(function(l){s[l[key]]=1});var v=$(id).value;$(id).length=1;MR.fill($(id),Object.keys(s).sort());$(id).value=v}
function load(){if(!LIVE){L=mine.concat(DEMO);return Promise.resolve()}return api('/rest/v1/listings?status=eq.active&order=created_at.desc&limit=100').then(function(r){loadErr='';L=(r||[]).map(MRL.fromApi)}).catch(function(e){L=[];loadErr='Could not load listings: '+e.message})}
function msg(card,t){var m=card.querySelector('.cm');if(!m){m=E('div',null,'mut cm');card.appendChild(m)}m.textContent=t}
function show(){var a=MRL.filterL(L,$('ft').value,$('fc').value,$('fs').value,$('fq').value),b=$('ls');b.textContent='';var prem=$('pm').checked;
a.forEach(function(l){var c=E('div',null,'card');c.appendChild(E('h3',(l.kind==='sell'?'Selling ':'Wants ')+l.qty+' qtl '+l.crop));var t=E('div');t.appendChild(E('span',l.kind==='sell'?'For sale':'Buyer needs','tag'+(l.kind==='buy'?' b':'')));if(l.ver)t.appendChild(E('span','✓ Verified','tag v'));c.appendChild(t);
c.appendChild(E('div','₹'+l.price.toLocaleString('en-IN')+' / quintal','pr'));c.appendChild(E('div',(l.district?l.district+', ':'')+l.state+' · '+MRL.ago(l.at,NOW),'mut'));if(l.note)c.appendChild(E('p',l.note));
var open=!LIVE&&(prem||usedList().indexOf(l.id)>-1),p=E('div',LIVE?'📞 Hidden until you tap Show contact':open?'📞 '+l.phone:'📞 '+MRL.mask(l.phone),'mut');c.appendChild(p);
if(!open){var bt=E('button','Show contact','btn g s');bt.type='button';bt.onclick=function(){
 if(!LIVE){var left=MRL.contactsLeft(usedList().length,LIMIT);if(left<=0){p.textContent='Free contact views are finished for today. Premium gives more.';return}used.ids=usedList().concat([l.id]);MR.sv('mr-used',used);show();return}
 if(!sess){$('auth').hidden=false;$('auth').scrollIntoView();msg(c,'Please sign in first.');return}
 api('/rest/v1/rpc/get_contact',{method:'POST',body:{lid:l.id}},sess.token).then(function(ph){if(ph==='LIMIT')p.textContent='Free contact views are finished for today. Premium gives more.';else if(ph){p.textContent='📞 '+ph;bt.remove()}else p.textContent='Contact not available.'}).catch(function(e){msg(c,e.message)})};c.appendChild(bt)}
if(LIVE&&sess&&l.owner===sess.user){var sd=E('button','Mark as sold','btn g s');sd.type='button';sd.onclick=function(){api('/rest/v1/listings?id=eq.'+encodeURIComponent(l.id),{method:'PATCH',body:{status:'sold'},prefer:'return=minimal'},sess.token).then(function(){return load()}).then(function(){fill('fc','crop');fill('fs','state');show()}).catch(function(e){msg(c,e.message)})};c.appendChild(sd)}
var r=E('button','Report this listing','btn r');r.type='button';r.onclick=function(){
 if(!LIVE){l.status='hidden';r.textContent='Reported, hidden for review';r.disabled=true;return}
 if(!sess){$('auth').hidden=false;msg(c,'Please sign in to report.');return}
 api('/rest/v1/reports',{method:'POST',body:{listing_id:l.id,reporter:sess.user},prefer:'return=minimal'},sess.token).then(function(){r.textContent='Reported, thank you';r.disabled=true}).catch(function(e){msg(c,e.message)})};c.appendChild(r);b.appendChild(c)});
$('cnt').textContent=(loadErr?loadErr+' · ':'')+a.length+' listing'+(a.length===1?'':'s')+' found · '+(LIVE?'Free: '+LIMIT+' contact views a day':prem?'Premium preview: unlimited contacts':MRL.contactsLeft(usedList().length,LIMIT)+' free contact views left today');
$('st1').textContent=L.filter(function(l){return l.kind==='sell'}).length+' produce offers';$('st2').textContent=L.filter(function(l){return l.kind==='buy'}).length+' buyer requirements'}
function tab(n){['1','2','3'].forEach(function(i){$('t'+i).setAttribute('aria-selected',String(i===String(n)))});$('p1').hidden=n!==1;$('p2').hidden=n===1;if(n!==1){kind=n===2?'sell':'buy';$('fh').textContent=n===2?'Post your produce':'Post what you need to buy';$('er').textContent='';if(LIVE&&!sess){$('auth').hidden=false;$('er').textContent='Please sign in first.'}}}
$('t1').onclick=function(){tab(1)};$('t2').onclick=function(){tab(2)};$('t3').onclick=function(){tab(3)};
['ft','fc','fs','fq','pm'].forEach(function(i){$(i).addEventListener('input',show)});
function refresh(){fill('fc','crop');fill('fs','state');show()}
$('f').addEventListener('submit',function(ev){ev.preventDefault();var l={id:Date.now(),kind:kind,crop:$('c').value.trim(),qty:+$('q').value,price:+$('p').value,state:$('s').value.trim(),district:$('d').value.trim(),phone:(LIVE&&MODE==='phone')?(sess&&sess.phone)||'':$('ph').value.trim(),note:$('n').value.trim(),consent:$('cs').checked,ver:0,at:Date.now()},er=MRL.validate(l);
if(LIVE&&!sess)er=['Please sign in first.'].concat(MODE==='phone'?er.filter(function(x){return x.indexOf('mobile')<0}):er);
if(er.length){$('er').textContent=er.join(' ');return}
if(!LIVE){delete l.consent;L.unshift(l);mine.unshift(l);MR.sv('mr-list',mine.slice(0,50));$('f').reset();$('er').textContent='';tab(1);refresh();return}
(MODE==='email'?api('/rest/v1/profiles?on_conflict=id',{method:'POST',body:{id:sess.user,email:sess.email,phone:l.phone},prefer:'resolution=merge-duplicates,return=minimal'},sess.token):Promise.resolve()).then(function(){return api('/rest/v1/listings',{method:'POST',body:MRL.toApi(l,sess.user),prefer:'return=minimal'},sess.token)}).then(function(){return load()}).then(function(){$('f').reset();$('er').textContent='';tab(1);refresh()}).catch(function(e){$('er').textContent=e.message})});
// ---- sign-in (only when a database is configured) ----
function setSess(s){sess=s;try{localStorage.setItem('mr-sess',JSON.stringify(s))}catch(e){}authUi()}
function authUi(){if(!LIVE)return;$('au').textContent=sess?(MODE==='phone'?'Signed in as +91 '+sess.phone:'Signed in as '+sess.email):'';$('auth').hidden=false;$('a1').hidden=!!sess;$('ah').hidden=!!sess;$('ahint').hidden=!!sess;$('so').hidden=!sess;if(sess)$('a2').hidden=true}
if(LIVE){$('dm').hidden=true;$('phw').hidden=(MODE==='phone');authUi();
 if(MODE==='email'){$('ap').type='email';$('ap').setAttribute('inputmode','email');$('ap').setAttribute('maxlength','80');$('ap').setAttribute('autocomplete','email');document.querySelector('label[for=ap]').textContent='Email address';$('ahint').textContent='Sign in with your email to post listings and see contacts.'}
 $('so').onclick=function(){sess=null;try{localStorage.removeItem('mr-sess')}catch(e){}authUi();show()};
 $('as').onclick=function(){var p=$('ap').value.trim();
  if(MODE==='email'){if(!emailOk(p)){$('ae').textContent='Enter a valid email address.';return}$('ae').textContent='';api('/auth/v1/otp',{method:'POST',body:{email:p,create_user:true}}).then(function(){$('a2').hidden=false;$('ae').textContent='We sent a code to your email.'}).catch(function(e){$('ae').textContent=e.message});return}
  if(!MRL.phoneOk(p)){$('ae').textContent='Enter a valid 10-digit mobile number.';return}$('ae').textContent='';api('/auth/v1/otp',{method:'POST',body:{phone:MRL.e164(p),create_user:true}}).then(function(){$('a2').hidden=false;$('ae').textContent='We sent a code by SMS.'}).catch(function(e){$('ae').textContent=e.message})};
 $('av').onclick=function(){var p=$('ap').value.trim(),o=$('ao').value.trim();if(!o){$('ae').textContent=MODE==='email'?'Enter the code from your email.':'Enter the code from the SMS.';return}
  var vb=MODE==='email'?{type:'email',email:p,token:o}:{type:'sms',phone:MRL.e164(p),token:o};
  api('/auth/v1/verify',{method:'POST',body:vb}).then(function(j){var s={token:j.access_token,user:j.user&&j.user.id,exp:Date.now()+(j.expires_in||3600)*1000};if(MODE==='email')s.email=p;else s.phone=p;if(!s.token||!s.user)throw new Error('Sign-in failed.');
   return api('/rest/v1/profiles?on_conflict=id',{method:'POST',body:MODE==='email'?{id:s.user,email:p}:{id:s.user,phone:p},prefer:'resolution=merge-duplicates,return=minimal'},s.token).then(function(){setSess(s);$('ae').textContent=''})}).catch(function(e){$('ae').textContent=e.message})}}
else{$('dm').hidden=false}
load().then(refresh);
})();

import json,os,re,sys,html,datetime,collections,shutil,time
from urllib.parse import urlencode
from urllib.request import urlopen,Request
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from content import SCHEMES,GUIDES,REVIEWED,REVIEWED_ISO
IST=datetime.timezone(datetime.timedelta(hours=5,minutes=30));NOW=datetime.datetime.now(IST);BUILD_DATE=f'{NOW.day} {NOW.strftime("%b %Y")}'
FOOT={'states':[],'crops':[],'latest':''}
EMOJI={'wheat':'🌾','rice':'🍚','paddy':'🌾','maize':'🌽','bajra':'🌾','jowar':'🌾','barley':'🌾','onion':'🧅','tomato':'🍅','potato':'🥔','garlic':'🧄','ginger':'🫚','green chilli':'🌶️','dry chillies':'🌶️','brinjal':'🍆','cabbage':'🥬','cauliflower':'🥦','carrot':'🥕','bhindi':'🌿','cucumbar':'🥒','soyabean':'🫘','soybean':'🫘','mustard':'🌼','groundnut':'🥜','sunflower':'🌻','cotton':'☁️','gram':'🫘','arhar':'🫘','moong':'🫘','black gram':'🫘','masur':'🫘','lentil':'🫘','apple':'🍎','banana':'🍌','mango':'🥭','orange':'🍊','grapes':'🍇','pomegranate':'🍎','papaya':'🍈','lemon':'🍋','coconut':'🥥','sugarcane':'🎋','turmeric':'🟡','coriander':'🌿','pumpkin':'🎃','watermelon':'🍉','pineapple':'🍍','guava':'🍐'}
def emoji(c):return EMOJI.get(c.split('(')[0].strip().lower(),'🌱')
def nice(s):
    try:d=datetime.datetime.strptime(s,'%d/%m/%Y');return f'{d.day} {d.strftime("%b %Y")}'
    except Exception:return s
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE=(os.environ.get('SITE_URL') or 'https://mandirates.pages.dev').rstrip('/')
OUT=os.environ.get('OUT',os.path.join(ROOT,'site'));DATA=os.environ.get('DATA',os.path.join(ROOT,'data','sample.json'))
SERIES_DIR=os.environ.get('SERIES_DIR',os.path.join(ROOT,'data','series'))
KEY=os.environ.get('DATA_GOV_API_KEY') or os.environ.get('DATA_GOV_KEY') or ''
MAX_PAGES=int(os.environ.get('MAX_PAGES','15000'));CONTACT=os.environ.get('CONTACT_EMAIL','')
RID='9ef84268-d588-465a-a308-a864a43d0070';TESTLIVE=bool(os.environ.get('MR_TEST_LIVE'));DEMO=not(KEY or TESTLIVE);BUILD=str(int(time.time()))
E=lambda s:html.escape(str(s),quote=True)
def slug(s):return re.sub(r'[^a-z0-9]+','-',str(s).lower()).strip('-') or 'na'
def rs(v):return '₹'+format(int(v),',d')
UA='Mozilla/5.0 (compatible; MandiRates-build/1.0)';WAIT=float(os.environ.get('RETRY_WAIT','3'));PROXY=os.environ.get('PRICES_PROXY','')
def why(ex):
    code=getattr(ex,'code',None)
    if code:
        try:body=ex.read().decode('utf-8','ignore')[:120]
        except Exception:body=''
        if KEY:body=body.replace(KEY,'***')
        return f'HTTP {code} {body}'.strip()
    r=getattr(ex,'reason',None)
    return f'{type(ex).__name__}: {r}' if r else type(ex).__name__
def http_json(url,tries=3,wait=None):
    last=None;w=WAIT if wait is None else wait
    for i in range(tries):
        try:
            with urlopen(Request(url,headers={'User-Agent':UA,'Accept':'application/json'}),timeout=40) as r:return json.load(r)
        except Exception as ex:
            last=ex
            if i<tries-1:time.sleep(w*(i+1))
    raise last
def fetch_pages(make,tries=3,wait=None):
    rows=[];off=0
    while off<60000:
        d=http_json(make(off),tries,wait);rec=d.get('records',[])
        if not rec:break
        rows+=rec;off+=1000
        tot=d.get('total')
        if isinstance(tot,int) and off>=tot:break
    return rows
def fetch():
    direct=lambda off:f'https://api.data.gov.in/resource/{RID}?'+urlencode({'api-key':KEY,'format':'json','limit':1000,'offset':off})
    try:return fetch_pages(direct,2)
    except Exception as e1:
        proxy=PROXY or BASE+'/api/prices'
        try:rows=fetch_pages(lambda off:proxy+'?'+urlencode({'limit':1000,'offset':off}),5,WAIT*2 if WAIT else 0)
        except Exception as e2:raise Exception(f'direct fetch failed ({why(e1)}) and the Cloudflare route failed ({why(e2)})')
        if not rows:raise Exception('the Cloudflare route returned no rows')
        return rows
def num(v):
    try:return int(float(str(v).replace(',','')))
    except:return 0
def dt(s):
    try:return datetime.datetime.strptime(str(s),'%d/%m/%Y')
    except:return datetime.datetime(1970,1,1)
LAST=os.environ.get('LAST_FILE') or os.path.join(ROOT,'data','last.json');KEEP_DAYS=int(os.environ.get('KEEP_DAYS','3'))
def merge_last(fresh):
    # Early in the day only some mandis have reported. Keep each mandi's newest price from the last few days so pages stay full. Every row keeps its own date.
    try:old=json.load(open(LAST,encoding='utf-8'))
    except Exception:old=[]
    best={}
    for r in old+fresh:
        k=(r['state'],r['district'],r['market'],r['commodity'],r['variety'])
        if k not in best or dt(r['date'])>=dt(best[k]['date']):best[k]=r
    allr=list(best.values());newest=max(dt(r['date']) for r in allr);cut=newest-datetime.timedelta(days=KEEP_DAYS)
    kept=[r for r in allr if dt(r['date'])>=cut]
    os.makedirs(os.path.dirname(LAST),exist_ok=True);json.dump(kept,open(LAST,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
    return kept
def mark_odd(rows):
    g=collections.defaultdict(list)
    for r in rows:g[r['commodity']].append(r['md'])
    med={}
    for c,v in g.items():
        s=sorted(v);n=len(s);med[c]=(s[n//2] if n%2 else (s[n//2-1]+s[n//2])/2) if n>=5 else 0
    for r in rows:
        m=med[r['commodity']];r['odd']=bool(m and (r['md']>3*m or r['md']*3<m))
    return rows
def best(L):
    good=[x for x in L if not x.get('odd')];return (good or L)[0]
def clean(raw):
    best={}
    for r in raw:
        r={k.lower():v for k,v in r.items()}
        row=dict(state=str(r.get('state','')).strip(),district=str(r.get('district','')).strip(),market=str(r.get('market','')).strip(),commodity=str(r.get('commodity','')).strip(),variety=str(r.get('variety','')).strip(),date=str(r.get('arrival_date','')),mn=num(r.get('min_price')),mx=num(r.get('max_price')),md=num(r.get('modal_price')))
        if not(row['state'] and row['district'] and row['market'] and row['commodity']):continue
        if row['md']<=0 or row['mn']<0 or row['mx']<row['mn']:continue
        k=(row['state'],row['district'],row['market'],row['commodity'],row['variety'])
        if k not in best or dt(row['date'])>dt(best[k]['date']):best[k]=row
    return list(best.values())
# ---------- history (series) ----------
def merge_series(state,rows,iso):
    p=os.path.join(SERIES_DIR,slug(state)+'.json');os.makedirs(SERIES_DIR,exist_ok=True)
    try:data=json.load(open(p,encoding='utf-8'))
    except:data={'d':[],'v':{}}
    d,v=data['d'],data['v']
    if d and iso<d[-1] and iso not in d:return data
    if iso not in d:
        d.append(iso)
        for a in v.values():a.append(None)
    i=d.index(iso)
    for r in rows:
        k=f"{r['market']}|{r['commodity']}|{r['variety']}";a=v.setdefault(k,[None]*len(d))
        while len(a)<len(d):a.append(None)
        a[i]=r['md']
    if len(d)>30:
        cut=len(d)-30;data['d']=d=d[cut:]
        for k in list(v):
            v[k]=v[k][cut:]
            if all(x is None for x in v[k]):del v[k]
    json.dump(data,open(p,'w',encoding='utf-8'),separators=(',',':'));return data
def series_for(data,r):
    a=data.get('v',{}).get(f"{r['market']}|{r['commodity']}|{r['variety']}");return a
def svg_chart(vals,label):
    pts=[(i,x) for i,x in enumerate(vals) if x is not None]
    if len(pts)<3:return ''
    mn=min(x for _,x in pts);mx=max(x for _,x in pts);sp=(mx-mn) or 1;n=max(1,len(vals)-1)
    p=' '.join(f"{i*600/n:.1f},{142-(x-mn)/sp*120:.1f}" for i,x in pts)
    return f'<svg class="sv" viewBox="0 0 600 150" role="img" aria-label="{E(label)}"><polyline points="{p}" fill="none" stroke="#1b6b3b" stroke-width="3" stroke-linejoin="round"/></svg><p class="mut">{len(pts)} days saved · low {rs(mn)} · high {rs(mx)}</p>'
# ---------- page shell ----------
CSP="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'"
NAV=[('Home','/','होम'),('Prices','/mandi-prices/','भाव'),('Compare','/compare/','तुलना'),('Tools','/tools/','टूल्स'),('Guides','/guides/','गाइड'),('Schemes','/schemes/','योजनाएँ'),('Buy / Sell','/marketplace/','खरीद / बिक्री')]
written=[]
def write(path,content):
    p=os.path.join(OUT,path.strip('/'),'index.html') if path.endswith('/') else os.path.join(OUT,path.lstrip('/'))
    os.makedirs(os.path.dirname(p),exist_ok=True);open(p,'w',encoding='utf-8').write(content);written.append(path)
def footer_html():
    st=''.join(f'<a href="/mandi-prices/{slug(s)}/">{E(s)}</a>' for s in FOOT['states']);cr=''.join(f'<a href="/mandi-prices/crop/{slug(c)}/">{E(c)}</a>' for c in FOOT['crops'])
    return f'<footer class="site"><div class="w"><div class="fcols"><div><h3>Mandi prices</h3>{st}<a href="/mandi-prices/">All states</a></div><div><h3>Popular crops</h3>{cr}</div><div><h3>Learn</h3><a href="/guides/">Guides</a><a href="/schemes/">Government schemes</a><a href="/sitemap/">Site map</a></div><div><h3>Company</h3><a href="/about/">About</a><a href="/contact/">Contact</a><a href="/premium/">Premium</a><a href="/advertise/">Advertise</a><a href="/privacy/">Privacy</a><a href="/terms/">Terms</a><a href="/disclaimer/">Disclaimer</a></div></div><p>Source: Government of India open data (data.gov.in). Prices are indicative; confirm with the mandi before you trade. © MandiRates</p></div></footer>'
def shell(path,title,desc,h1,lead,body,crumbs=None,ld=None,scripts=(),hero='',index=True,hi=None,connect=''):
    graph=list(ld or [])
    if crumbs:graph.append({"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":i+1,"name":n,"item":BASE+p} for i,(n,p) in enumerate(crumbs)]})
    if path=='/':graph+= [{"@type":"WebSite","name":"MandiRates","url":BASE+'/'},{"@type":"Organization","name":"MandiRates","url":BASE+'/',"logo":BASE+'/icon-512.png'}]
    ldj=json.dumps({"@context":"https://schema.org","@graph":graph},ensure_ascii=False).replace('</','<\\/') if graph else ''
    nav=''.join(f'<a href="{u}"{" aria-current=\"page\"" if (u==path or (u!="/" and path.startswith(u))) else ""}>{E(n)}</a>' for n,u,h in NAV)
    cr=''
    if crumbs and len(crumbs)>1:cr='<div class="crumbs">'+' › '.join(f'<a href="{p}">{E(n)}</a>' for n,p in crumbs[:-1])+' › '+E(crumbs[-1][0])+'</div>'
    robots='index,follow,max-image-preview:large,max-snippet:-1' if index else 'noindex,follow'
    if title.endswith(' | MandiRates') and len(title)>70:title=title[:-13]
    banner='<div class="note" id="dn" hidden></div>' if 'js/home.js' in scripts or 'js/tools.js' in scripts or 'js/compare.js' in scripts else ''
    h1a=''
    sc=''.join(f'<script src="/{s}" defer></script>' for s in ('logic.js','app.js')+tuple(scripts))
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{BASE+path}"><meta name="robots" content="{robots}">
<meta http-equiv="Content-Security-Policy" content="{CSP if not connect else CSP.replace("connect-src 'self'","connect-src 'self' "+connect)}"><meta name="theme-color" content="#14532d">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:type" content="website"><meta property="og:url" content="{BASE+path}"><meta property="og:image" content="{BASE}/og.png"><meta name="twitter:card" content="summary_large_image">
<link rel="manifest" href="/manifest.webmanifest"><link rel="icon" href="/icon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/icon-192.png"><link rel="stylesheet" href="/theme.css">
{'<script type="application/ld+json">'+ldj+'</script>' if ldj else ''}</head>
<body><header class="site"><div class="datebar"><div class="w"><span id="today">Last updated {BUILD_DATE}</span><span>Prices as of {nice(FOOT["latest"]) if FOOT["latest"] else "n/a"}</span><span>Source: data.gov.in</span></div></div><div class="w"><div class="nav"><a class="brand" href="/">🌾 MandiRates</a><nav aria-label="Main">{nav}</nav>
<div class="ctl"><a class="btn s" href="/marketplace/">+ Post free ad</a><label class="vh" for="th">Colour theme</label><select id="th"><option value="forest">Forest</option><option value="leaf">Leaf</option><option value="sun">Earth</option><option value="ocean">Teal</option></select><button id="md" type="button" aria-label="Toggle dark mode">🌙</button><button id="lg" type="button">हिन्दी</button></div></div>
<div class="band">{cr}<h1{h1a}>{E(h1)}</h1><p class="lead">{lead}</p>{hero}</div></div></header>
<main class="w">{banner}{body}</main>
{footer_html()}{sc}</body></html>'''
def table(rows,idn='pt',cols=('Mandi','Variety','Min','Modal','Max','Per kg','Date')):
    th=''.join(f'<th>{c}</th>' for c in cols)
    b=''.join(f'<tr{" class=best" if i==0 else ""}><td>{E(x["market"])}</td><td>{E(x["variety"])}</td><td>{rs(x["mn"])}</td><td class="p">{rs(x["md"])}{" ⚠" if x.get("odd") else ""}</td><td>{rs(x["mx"])}</td><td>₹{x["md"]/100:.2f}</td><td>{E(x["date"])}</td></tr>' for i,x in enumerate(rows))
    return f'<div class="tw"><table id="{idn}"><thead><tr>{th}</tr></thead><tbody>{b}</tbody></table></div>'
# ---------- main ----------
def main():
    if KEY and not TESTLIVE:
        try:raw=fetch()
        except Exception as ex:sys.exit(f'Feed failed, site left unchanged: {ex}')
    else:raw=json.load(open(DATA,encoding='utf-8'))
    fresh=clean(raw);rows=fresh if DEMO else merge_last(fresh);mark_odd(rows);carried=len(rows)-len(fresh) if not DEMO else 0
    if not rows:sys.exit('No valid rows, site left unchanged')
    if os.path.isdir(OUT):shutil.rmtree(OUT)
    os.makedirs(OUT)
    S=collections.defaultdict(lambda:collections.defaultdict(lambda:collections.defaultdict(list)))
    for r in rows:S[r['state']][r['district']][r['commodity']].append(r)
    cropn=collections.Counter(r['commodity'] for r in rows);top40={c for c,_ in cropn.most_common(40)}
    cand=[(len(S[s][d][c]),s,d,c) for s in S for d in S[s] for c in S[s][d] if len(S[s][d][c])>=2 or c in top40]
    csn=collections.Counter((r['commodity'],r['state']) for r in rows);cs_ok={k for k,v in csn.items() if v>=3 and cropn[k[0]]>=3}
    cand.sort(key=lambda x:-x[0]);fixed=len(S)+sum(len(S[s]) for s in S)+len([c for c in cropn if cropn[c]>=3])+len(cs_ok)+40
    allowed={(s,d,c) for _,s,d,c in cand[:max(0,MAX_PAGES-fixed)]}
    dates=[dt(r['date']) for r in rows if dt(r['date']).year>1970];latest=max(dates).strftime('%d/%m/%Y') if dates else ''
    iso=max(dates).strftime('%Y-%m-%d') if dates else datetime.date.today().isoformat()
    DD=nice(latest);FOOT['latest']=latest
    FOOT['states']=sorted(S,key=lambda x:-sum(len(v) for v in S[x].values()))[:8];FOOT['crops']=[c for c,_ in cropn.most_common(8) if cropn[c]>=3]
    def cstats(c):
        g=sorted(r['md'] for r in rows if r['commodity']==c and not r['odd']) or sorted(r['md'] for r in rows if r['commodity']==c);n=len(g)
        return (g[n//2] if n%2 else (g[n//2-1]+g[n//2])//2),g[0],g[-1],n
    # history: only on real runs
    SD={}
    if not DEMO:
        for s in S:
            keep=[x for d in S[s] for c in S[s][d] if (s,d,c) in allowed for x in S[s][d][c]]
            SD[s]=merge_series(s,keep,iso)
    else:
        for s in S:SD[s]={'d':[],'v':{}}
    R='/mandi-prices/';home=[('Home','/')];root=home+[('Mandi prices',R)]
    # home
    top_rows=[]
    for c,_ in cropn.most_common(15):
        g=sorted([r for r in rows if r['commodity']==c and not r['odd']],key=lambda r:r['md']) or sorted([r for r in rows if r['commodity']==c],key=lambda r:r['md']);top_rows.append(g[len(g)//2])
    sc=''.join(f'<a href="{R}{slug(s)}/">{E(s)}</a>' for s in sorted(S,key=lambda x:-sum(len(v) for v in S[x].values()))[:12])
    hero=f'''<div class="cta"><a class="btn" href="/marketplace/">+ Sell produce</a><a class="btn o" href="/marketplace/">+ Post requirement</a></div>
<form class="bar" id="sf" role="search"><div><label class="vh" for="st">State</label><select id="st"><option value="">All states</option></select></div><div><label class="vh" for="q">Search crop or mandi</label><input id="q" type="search" placeholder="Crop or mandi: wheat, Indore…" autocomplete="off" maxlength="40"></div><button class="btn" type="submit">Search prices</button></form>'''
    cards=''.join(f'<a class="ccard" href="/mandi-prices/crop/{slug(c)}/"><span class="em">{emoji(c)}</span><b>{E(c)}</b><span class="pr">{rs(m)}</span><small>{rs(lo)} – {rs(hi)} · {n} mandis</small></a>' for c,_ in cropn.most_common(12) if cropn[c]>=5 for m,lo,hi,n in [cstats(c)])
    cropsec=f'<section class="card"><h2>Popular crops today</h2><p class="hint">Typical price per quintal across India. Tap a crop to see every mandi.</p><div class="cgrid">{cards}</div></section>' if cards else ''
    trust='<div class="trust"><span>✔ Government data (data.gov.in)</span><span>🕒 Updated daily</span><span>🆓 Free to use</span><span>🔓 No sign-up for prices</span></div>'
    learnsec='<section class="card"><h2>Guides for farmers and traders</h2><div class="grid">'+''.join(f'<a class="lcard" href="/guides/{g["slug"]}/"><small>Guide</small><b>{E(g["short"])}</b></a>' for g in GUIDES)+'</div></section>'
    HING={'wheat':'Gehun','rice':'Chawal','onion':'Pyaz','tomato':'Tamatar','potato':'Aloo','maize':'Makka','mustard':'Sarson','garlic':'Lahsun','ginger':'Adrak','banana':'Kela','apple':'Seb','mango':'Aam','cotton':'Kapas','gram':'Chana','sugarcane':'Ganna','soyabean':'Soyabean'}
    qs='<div class="qs"><a href="/mandi-prices/"><span class="ic">📊</span>Mandi prices</a><a href="/compare/"><span class="ic">⚖️</span>Compare</a><a href="/tools/#sell"><span class="ic">🚚</span>Where to sell</a><a href="/marketplace/"><span class="ic">🛒</span>Buy / Sell</a><a href="/schemes/"><span class="ic">🏛️</span>Schemes</a><a href="/guides/"><span class="ic">📖</span>Guides</a></div>'
    nm=len({(r['state'],r['market']) for r in rows})
    stats=f'<div class="stats"><div class="st g"><b>{nm:,}</b><span>Mandis with prices</span></div><div class="st p"><b>{len(cropn):,}</b><span>Crops tracked</span></div><div class="st b"><b>{len(S):,}</b><span>States and UTs</span></div><div class="st y"><b>Daily</b><span>Price updates</span></div></div>'
    premium='<section class="promo"><div><span class="tag b">Coming soon</span><h2>MandiRates Premium</h2><p>Longer price history, more alerts and more contact views. Prices, comparison and CSV stay free.</p></div><a class="btn" href="/premium/">See what is planned</a></section>'
    sch=[('pm-kisan','PM-KISAN','₹6,000 a year in three instalments for eligible farmer families.','https://pmkisan.gov.in/'),('pm-fasal-bima-yojana','Crop insurance (PMFBY)','Cover for crop loss from calamities, pests and diseases, at a low farmer premium.','https://pmfby.gov.in/'),('kisan-credit-card','Kisan Credit Card','Short-term farm credit with an interest benefit for timely repayment.','https://www.nabard.org/')]
    schemesec='<section class="card"><h2>Government schemes for farmers</h2><div class="grid">'+''.join(f'<div class="scard"><b>{E(n)}</b><p>{E(t)}</p><div class="row2"><a class="btn g s" href="/schemes/{sl}/">Learn more</a><a class="btn g s" href="{u}" rel="noopener nofollow" target="_blank">Official site</a></div></div>' for sl,n,t,u in sch)+'</div></section>'
    how='<section class="card"><h2>How MandiRates works</h2><div class="how"><div><span class="n">1</span><b>Search your crop</b><p class="hint">Type a crop or mandi name.</p></div><div><span class="n">2</span><b>Pick your state</b><p class="hint">Filter prices to where you sell.</p></div><div><span class="n">3</span><b>Compare mandis</b><p class="hint">See who pays the most after transport.</p></div><div><span class="n">4</span><b>Set a price alert</b><p class="hint">Get told when your price comes.</p></div></div></section>'
    topst=sorted(S,key=lambda x:-sum(len(v) for v in S[x].values()))[:6];cl=[]
    for c,_ in cropn.most_common(14):
        if cropn[c]<3:continue
        bn=c.split('(')[0].strip();cl.append((f'{bn} price today',f'{R}crop/{slug(c)}/'))
        if bn.lower() in HING:cl.append((f'{HING[bn.lower()]} ka bhav',f'{R}crop/{slug(c)}/'))
        cl+=[(f'{bn} rate in {s2}',f'{R}crop/{slug(c)}/{slug(s2)}/') for s2 in topst if (c,s2) in cs_ok]
    cloud='<section class="card"><h2>Popular searches</h2><div class="cloud">'+''.join(f'<a href="{u}">{E(t)}</a>' for t,u in cl[:90])+'</div></section>' if cl else ''
    body=f'''{qs}
{trust}{cropsec}{stats}<div class="cols"><section class="card" id="prices"><h2>Today’s mandi prices</h2><p class="hint">₹ per quintal · <span id="upd">{('Latest data: '+latest) if latest else ''}</span></p><div class="tw"><table id="pt"><thead><tr><th>Crop</th><th>Mandi</th><th>State</th><th>Min</th><th>Modal</th><th>Max</th><th>Change</th><th>Date</th></tr></thead><tbody id="tb">{''.join(f'<tr><td>{E(r["commodity"])}</td><td>{E(r["market"])}</td><td>{E(r["state"])}</td><td>{rs(r["mn"])}</td><td class="p">{rs(r["md"])}</td><td>{rs(r["mx"])}</td><td>–</td><td>{E(r["date"])}</td></tr>' for r in top_rows)}</tbody></table></div><p class="hint" id="cnt"></p><button class="btn g s" id="more" type="button" hidden>Show more</button> <button class="btn g s" type="button" data-csv="pt" data-name="mandi-prices.csv">Download CSV</button></section>
<aside class="card"><h2 id="mvt">Highest prices today</h2><ul class="mv" id="mv"></ul></aside></div>
{premium}{schemesec}{how}{cloud}
<section class="card"><h2>Browse by state</h2><p class="hint">Choose a state, then a district, then a crop.</p><div class="chips">{sc}<a href="{R}">All states →</a></div></section>
{learnsec}<section class="card app"><div><h2>Use MandiRates like an app</h2><p class="hint">Open the browser menu and choose “Add to Home screen”. Last prices still show offline.</p></div><div class="cta2"><button class="btn" id="install" type="button" hidden>Install app</button><a class="btn" href="/marketplace/">Buy and sell produce</a></div></section>'''
    faq=[("How do I find the best mandi to sell my crop?","Use the Where to sell tool: choose your crop, quantity and location. It ranks mandis by the money you keep after transport."),("Where do these prices come from?","Prices come from the Government of India open data portal (data.gov.in), which publishes Agmarknet mandi prices. Each price shows its date."),("Is MandiRates free?","Yes. Prices, comparison of up to 8 mandis and CSV download are free.")]
    fld=[{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in faq]}]
    body+='<section class="card"><h2>Common questions</h2>'+''.join(f'<details><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q,a in faq)+'</section>'
    write('/',shell('/','Mandi Bhav Today: Live Mandi Prices India | MandiRates','Today’s mandi prices across India. Compare mandis, see trends, and post produce to sell or a requirement to buy. Free and fast.','Mandi bhav today across India','Compare mandis, see who pays the most, and buy or sell produce. Free, fast, and works on slow networks.',body,None,fld,('js/home.js',),hero,hi='आज का मंडी भाव, पूरे भारत में'))
    # inner tool pages
    write('/compare/',shell('/compare/','Compare Mandi Prices (Up to 8 Mandis) | MandiRates','Compare up to 8 mandis for the same crop, see who pays the most, and download the comparison as CSV. Free.','Compare up to 8 mandis for one crop','See who pays the most today and by how much. Free, with CSV download.',
     '<section class="card"><div class="row"><div><label for="cr">Crop</label><select id="cr"></select></div><div><label for="mf">Find a mandi</label><input id="mf" type="search" maxlength="40" placeholder="Type a mandi or state"></div></div><p class="mut">Tick up to 8 mandis. The 60 highest-priced mandis are listed; search to find others.</p><div class="pick" id="pk"></div><div class="big" id="sm" aria-live="polite"></div><div class="tw"><table><thead><tr><th>Mandi</th><th>Min</th><th>Modal</th><th>Max</th><th>Below best</th><th>Compare</th></tr></thead><tbody id="tb"></tbody></table></div><p><button class="btn" id="dl" type="button">Download CSV</button></p></section>',
     home+[('Compare','/compare/')],None,('js/compare.js',)))
    write('/tools/',shell('/tools/','Trader Tools: Where to Sell, Trends, Alerts, Profit | MandiRates','Free tools for traders and farmers: best mandi after transport cost, price trend signal, price alerts and a profit calculator.','Tools for traders and farmers','Pick the best mandi, check if today’s price is high or low, and calculate your real profit.',
     '''<div class="two"><section class="card" id="sell"><h2>Where to sell</h2><p class="hint">Ranks mandis by money left after transport.</p><div class="row"><div><label for="sc">Crop</label><select id="sc"></select></div><div><label for="sq">Quintals</label><input id="sq" type="number" min="1" value="100"></div></div><div class="row"><div><label for="so">Your nearest city</label><select id="so"></select></div><div><label for="sr">Transport ₹ per quintal per 100 km</label><input id="sr" type="number" min="0" value="60"></div></div><div id="so2" aria-live="polite"></div></section>
<section class="card" id="trend"><h2>Price trend and signal</h2><p class="hint">Is today’s price high or low for this crop and mandi?</p><div class="row"><div><label for="tc">Crop and mandi</label><select id="tc"></select></div></div><div id="tsv"></div><div id="to" aria-live="polite"></div></section></div>
<div class="two mt"><section class="card" id="alerts"><h2>Price alerts</h2><p class="hint">Saved on this device. Alerts show here when you open the site. WhatsApp alerts need accounts (coming later).</p><div class="row"><div><label for="ac">Crop and mandi</label><select id="ac"></select></div><div><label for="ad">When price is</label><select id="ad"><option value="above">above</option><option value="below">below</option></select></div><div><label for="at">₹ per quintal</label><input id="at" type="number" min="1" value="2500"></div></div><button class="btn" id="aa" type="button">Add alert</button><ul class="al" id="al"></ul></section>
<section class="card"><h2>Trader profit calculator</h2><p class="hint">Buy, sell, transport and commission in one place.</p><div class="row"><div><label for="b">Buy ₹/qtl</label><input id="b" type="number" min="0" value="2200"></div><div><label for="s">Sell ₹/qtl</label><input id="s" type="number" min="0" value="2400"></div><div><label for="n">Quintals</label><input id="n" type="number" min="0" value="100"></div></div><div class="row"><div><label for="t">Transport ₹</label><input id="t" type="number" min="0" value="3000"></div><div><label for="c">Commission %</label><input id="c" type="number" min="0" max="20" step="0.1" value="1"></div></div><div id="po" aria-live="polite"></div></section></div>''',
     home+[('Tools','/tools/')],None,('js/tools.js',)))
    write('/marketplace/',shell('/marketplace/','Buy and Sell Farm Produce in India | MandiRates','Post your produce free, find genuine buyers and sellers across India, and check mandi rates before you deal.','Buy and sell farm produce, no middleman','Post your produce or requirement free. Compare with today’s mandi rate before you agree a price.',
     '''<div class="note" id="dm">Demo: these listings are samples saved only on this device. Real listings need sign-in and a secure database, which are being set up.</div><section class="card" id="auth" hidden><h2 id="ah">Sign in</h2><p class="hint" id="ahint">Sign in with your mobile number to post listings and see contacts.</p><div class="row" id="a1"><div><label for="ap">Mobile number</label><input id="ap" inputmode="numeric" maxlength="10" autocomplete="tel-national"></div><div><button class="btn" id="as" type="button">Send OTP</button></div></div><div class="row" id="a2" hidden><div><label for="ao">OTP code</label><input id="ao" inputmode="numeric" maxlength="8" autocomplete="one-time-code"></div><div><button class="btn" id="av" type="button">Verify</button></div></div><p class="err" id="ae" role="alert"></p><p class="mut" id="au"></p><button class="btn g s" id="so" type="button" hidden>Sign out</button></section><div class="tabs" role="tablist"><button type="button" role="tab" id="t1" aria-selected="true">Browse deals</button><button type="button" role="tab" id="t2" aria-selected="false">Post produce to sell</button><button type="button" role="tab" id="t3" aria-selected="false">Post what I need to buy</button></div>
<section id="p1" class="card"><div class="row"><div><label for="ft">I want to see</label><select id="ft"><option value="">Everything</option><option value="sell">Produce for sale</option><option value="buy">Buyer requirements</option></select></div><div><label for="fc">Crop</label><select id="fc"><option value="">All crops</option></select></div><div><label for="fs">State</label><select id="fs"><option value="">All states</option></select></div><div><label for="fq">Search</label><input id="fq" type="search" maxlength="40" placeholder="e.g. basmati"></div></div>
<label class="chk"><input type="checkbox" id="pm"><span>Preview as a Premium member (demo): shows every contact number</span></label><p class="mut"><span id="st1"></span> · <span id="st2"></span> · <span id="cnt" aria-live="polite"></span></p><div class="grid" id="ls"></div></section>
<section id="p2" class="card" hidden><h2 id="fh">Post your produce</h2><form id="f" novalidate><div class="row"><div><label for="c">Crop</label><input id="c" maxlength="40" required placeholder="Wheat"></div><div><label for="q">Quantity (quintals)</label><input id="q" type="number" min="1" required></div><div><label for="p">Price ₹ per quintal</label><input id="p" type="number" min="1" required></div></div><div class="row"><div><label for="s">State</label><input id="s" maxlength="40" required placeholder="Punjab"></div><div><label for="d">District</label><input id="d" maxlength="40" placeholder="Ludhiana"></div><div id="phw"><label for="ph">Mobile number</label><input id="ph" inputmode="numeric" maxlength="10" required placeholder="10 digits"></div></div><div><label for="n">Details (variety, quality, delivery)</label><textarea id="n" rows="3" maxlength="300"></textarea></div>
<label class="chk"><input type="checkbox" id="cs"><span>I agree that my number is shown only to people who unlock it, and that I will not post false rates or quantities.</span></label><p class="err" id="er" role="alert"></p><button class="btn" type="submit">Post for free</button></form></section>''',
     home+[('Buy / Sell','/marketplace/')],None,('config.js','js/market.js'),connect='https://*.supabase.co'))
    # legal
    D=datetime.date.today().strftime('%d %B %Y')
    def legal(p,t,h,paras):write(p,shell(p,t+' | MandiRates',h,t,h,'<section class="card">'+''.join(f'<p>{x}</p>' if not x.startswith('#') else f'<h2>{E(x[1:])}</h2>' for x in paras)+f'<p class="mut">Last updated: {D}</p></section>',home+[(t,p)]))
    legal('/about/','About MandiRates','MandiRates gives farmers and traders free, simple access to mandi prices.',['MandiRates shows daily mandi prices from the Government of India open data portal, helps you compare mandis, and lets buyers and sellers find each other.','#Our promise','We show the source and date of every price, we never invent prices, and we keep the site fast and free to use.'])
    legal('/privacy/','Privacy Policy','How MandiRates handles your information, saved choices and phone numbers in marketplace listings.',['#What we collect','The price pages need no account. Choices such as your colour theme, language, watchlist and alerts are saved only in your own browser. If you post a listing, the details you enter, including your mobile number, are used to run the marketplace.','#Phone numbers','Your number is hidden from other visitors and shown only through the unlock rules of the marketplace. Do not post anyone else’s number.','#Your choices','You can clear saved choices by clearing your browser data. To ask us to remove a listing or data, use the contact details on the Contact page.'])
    legal('/terms/','Terms of Use','The rules for using MandiRates: your responsibilities, marketplace listings and our limits of liability.',['By using MandiRates you agree to use it lawfully and honestly.','#Listings','You are responsible for the accuracy of what you post. Do not post false prices, quantities or contact details. We may hide or remove listings that are reported or look unsafe.','#No guarantee','MandiRates is not a party to any deal. Check the other person, the goods and the payment yourself before you trade.'])
    legal('/disclaimer/','Disclaimer','Why prices on MandiRates are indicative, and what to confirm with the mandi before you trade.',['Prices come from government open data and can be delayed or incomplete. Always confirm the final rate with the mandi before you load, buy or sell.','Trend signals and calculators are simple aids, not financial or trading advice. Actual transport costs and commissions will differ.'])
    cm=f'You can write to us at <a href="mailto:{E(CONTACT)}">{E(CONTACT)}</a>.' if CONTACT else 'Our contact email will be added here soon. For a problem with a marketplace listing, use the Report button on that listing.'
    legal('/contact/','Contact Us','How to contact MandiRates for questions, listing problems, advertising and partnership enquiries.',[cm])
    write('/poster/',shell('/poster/','Poster: Check Mandi Prices Free | MandiRates','Printable poster for mandis and farmer groups.','Printable poster','Print this page and put it up at your mandi, shop or farmer group.',
     f'<section class="card"><div class="poster"><h2>Check mandi prices free</h2><p class="pt">आज का मंडी भाव मुफ़्त देखें</p><ul><li>Prices from mandis across India</li><li>Compare up to 8 mandis</li><li>Find the best place to sell</li><li>Buy and sell produce</li></ul><div class="url">{BASE.replace("https://","")}</div></div><p class="noprint"><button class="btn" type="button" id="pp">Print poster</button></p></section>',home+[('Poster','/poster/')],None,('js/poster.js',),index=False))
    write('/404.html',shell('/404.html','Page not found | MandiRates','This page does not exist.','Page not found','The page you opened does not exist. Try the price pages.','<section class="card"><p><a class="btn" href="/mandi-prices/">See mandi prices</a></p></section>',None,None,(),index=False))
    # content: guides, schemes, hubs, html sitemap, premium, advertise
    def prose(ps):
        out='';buf=[]
        for p in ps:
            if p.startswith('- '):buf.append(p[2:])
            else:
                if buf:out+='<ul>'+''.join(f'<li>{E(x)}</li>' for x in buf)+'</ul>';buf=[]
                out+=f'<p>{E(p)}</p>'
        return out+('<ul>'+''.join(f'<li>{E(x)}</li>' for x in buf)+'</ul>' if buf else '')
    def article(kind,g,peers):
        path=f'/{kind}/{g["slug"]}/';hub=f'/{kind}/';hubn='Government schemes' if kind=='schemes' else 'Guides'
        body='<article class="card prose"><p class="meta">By MandiRates Editorial Team · Last reviewed '+REVIEWED+'</p>'+''.join(f'<h2>{E(h)}</h2>'+prose(ps) for h,ps in g['sections'])
        body+='<h2>Frequently asked questions</h2>'+''.join(f'<details><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q,a in g['faq'])
        if g['links']:body+='<h2>Official links</h2><ul>'+''.join(f'<li><a href="{u}" rel="noopener nofollow" target="_blank">{E(t)}</a></li>' for t,u in g['links'])+'</ul>'
        if kind=='schemes':body+='<p class="note">Scheme rules can change. Always confirm on the official website or at your bank or agriculture office before you act.</p>'
        body+='</article><section class="card"><h2>Read next</h2><div class="chips">'+''.join(f'<a href="/{kind}/{x["slug"]}/">{E(x["short"])}</a>' for x in peers if x['slug']!=g['slug'])+f'<a href="/mandi-prices/">Today’s mandi prices</a></div></section>'
        ld=[{"@type":"Article","headline":g['title'],"description":g['desc'],"datePublished":REVIEWED_ISO,"dateModified":REVIEWED_ISO,"author":{"@type":"Organization","name":"MandiRates Editorial Team"},"publisher":{"@type":"Organization","name":"MandiRates","logo":{"@type":"ImageObject","url":BASE+'/icon-512.png'}},"mainEntityOfPage":BASE+path},{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in g['faq']]}]
        write(path,shell(path,g['title']+' | MandiRates',g['desc'],g['title'],g['lead'],body,home+[(hubn,hub),(g['short'],path)],ld))
    for kind,L,hn,hd in (('schemes',SCHEMES,'Government Schemes for Farmers','Plain-language guides to PM-KISAN, crop insurance, Kisan Credit Card, eNAM and MSP, with links to the official sites.'),('guides',GUIDES,'Mandi and Farming Guides','Simple guides on reading mandi prices, choosing the best mandi, staying safe from fraud and timing your sale.')):
        hp=f'/{kind}/'
        write(hp,shell(hp,hn+' | MandiRates',hd,hn,hd,'<div class="grid">'+''.join(f'<a class="lcard" href="{hp}{g["slug"]}/"><b>{E(g["title"])}</b><small>{E(g["desc"])}</small></a>' for g in L)+'</div>',home+[(hn,hp)]))
        for g in L:article(kind,g,L)
    write('/sitemap/',shell('/sitemap/','Site Map | MandiRates','All main pages of MandiRates: prices, tools, guides, government schemes and company pages.','Site map','Every main page on MandiRates.',
      '<section class="card"><h2>Main</h2><div class="chips"><a href="/">Home</a><a href="/mandi-prices/">Mandi prices</a><a href="/compare/">Compare mandis</a><a href="/tools/">Trader tools</a><a href="/marketplace/">Buy / Sell</a><a href="/premium/">Premium</a><a href="/advertise/">Advertise</a></div></section>'
      '<section class="card"><h2>Government schemes</h2><div class="chips">'+''.join(f'<a href="/schemes/{g["slug"]}/">{E(g["short"])}</a>' for g in SCHEMES)+'</div></section><section class="card"><h2>Guides</h2><div class="chips">'+''.join(f'<a href="/guides/{g["slug"]}/">{E(g["short"])}</a>' for g in GUIDES)+'</div></section>'
      '<section class="card"><h2>Mandi prices by state</h2><div class="chips">'+''.join(f'<a href="{R}{slug(s)}/">{E(s)}</a>' for s in sorted(S))+'</div></section><section class="card"><h2>Mandi prices by crop</h2><div class="chips">'+''.join(f'<a href="{R}crop/{slug(c)}/">{E(c)}</a>' for c in [x for x,_ in cropn.most_common(60) if cropn[x]>=3])+'</div></section>'
      '<section class="card"><h2>Company</h2><div class="chips"><a href="/about/">About</a><a href="/contact/">Contact</a><a href="/privacy/">Privacy</a><a href="/terms/">Terms</a><a href="/disclaimer/">Disclaimer</a></div></section>',home+[('Site map','/sitemap/')]))
    cm2=f'Write to us at <a href="mailto:{E(CONTACT)}">{E(CONTACT)}</a>.' if CONTACT else 'Our contact email will be added here soon.'
    write('/premium/',shell('/premium/','MandiRates Premium: Plans and What Is Coming | MandiRates','Prices, comparison and CSV stay free. See what MandiRates Premium and Business plans are planned to include.','MandiRates Premium','Everything you use today stays free. Premium is for people who want more.',
      '<div class="grid"><section class="card"><span class="tag">Free</span><h2>Free, always</h2><ul><li>Daily mandi prices</li><li>Compare up to 8 mandis</li><li>CSV download</li><li>Where to sell and profit calculator</li><li>Guides and scheme information</li></ul></section>'
      '<section class="card"><span class="tag b">Coming soon</span><h2>Premium</h2><ul><li>Longer price history</li><li>More price alerts, including WhatsApp</li><li>More contact views in the marketplace</li><li>No advertising</li></ul></section>'
      '<section class="card"><span class="tag b">Coming soon</span><h2>Business</h2><ul><li>Bulk data export for traders and companies</li><li>Data access for your own tools</li><li>Featured and verified seller placement</li></ul></section></div>'
      f'<section class="card"><h2>Tell us what you need</h2><p>Prices for these plans are not announced yet. {cm2}</p></section>',home+[('Premium','/premium/')]))
    write('/advertise/',shell('/advertise/','Advertise on MandiRates | MandiRates','Reach farmers, traders and agri businesses. Planned ad formats and our advertising rules.','Advertise on MandiRates','Reach people who check mandi prices every day.',
      '<div class="grid"><section class="card"><h2>Who sees your message</h2><p>Farmers, traders, commission agents and agri businesses looking at prices, comparing mandis and planning where to sell.</p></section><section class="card"><h2>Planned formats</h2><ul><li>Sponsored crop or state pages</li><li>Clearly labelled banners</li><li>Featured marketplace listings</li></ul></section><section class="card"><h2>Our rules</h2><ul><li>Every ad is labelled as an ad</li><li>Ads never change prices or rankings</li><li>Only relevant farm and trade products</li></ul></section></div>'
      f'<section class="card"><h2>Get in touch</h2><p>{cm2}</p></section>',home+[('Advertise','/advertise/')]))
    # silo
    def state_crops(s):
        cs=sorted([(csn[(c,s)],c) for (c,s2) in cs_ok if s2==s],reverse=True)[:30]
        return '<section class="card"><h2>Popular crops in '+E(s)+'</h2><div class="chips">'+''.join(f'<a href="{R}crop/{slug(c)}/{slug(s)}/">{E(c)}</a>' for _,c in cs)+'</div></section>' if cs else ''
    topc=[c for c,_ in cropn.most_common(30) if cropn[c]>=3]
    write(R,shell(R,'Mandi Prices by State, District and Crop | MandiRates','Browse today’s mandi prices by state, district and crop across India.','Mandi prices by state','Choose a state to see its districts and crops, or pick a crop to see prices across India.',
      '<section class="card"><h2>States</h2><div class="chips">'+''.join(f'<a href="{R}{slug(s)}/">{E(s)}</a>' for s in sorted(S))+'</div></section><section class="card"><h2>Popular crops</h2><div class="chips">'+''.join(f'<a href="{R}crop/{slug(c)}/">{E(c)}</a>' for c in topc)+'</div></section>',root))
    for c in cropn:
        if cropn[c]<3:continue
        L=sorted([r for r in rows if r['commodity']==c],key=lambda r:-r['md']);L=([x for x in L if not x['odd']] or L)[:25];cp=f'{R}crop/{slug(c)}/';top=L[0]
        pd=max((x['date'] for x in L),key=dt);fr=(pd==NOW.strftime('%d/%m/%Y'))
        ans=f'The highest {c} price {"today is" if fr else "on "+nice(pd)+" was"} {rs(top["md"])} per quintal at {top["market"]}, {top["state"]}.'
        b=f'<section class="card"><p class="big">{E(ans)}</p><div class="tw"><table id="pt"><thead><tr><th>Mandi</th><th>State</th><th>Min</th><th>Modal</th><th>Max</th><th>Date</th></tr></thead><tbody>'+''.join(f'<tr{" class=best" if i==0 else ""}><td>{E(x["market"])}</td><td><a href="{R}{slug(x["state"])}/">{E(x["state"])}</a></td><td>{rs(x["mn"])}</td><td class="p">{rs(x["md"])}{" ⚠" if x.get("odd") else ""}</td><td>{rs(x["mx"])}</td><td>{E(x["date"])}</td></tr>' for i,x in enumerate(L))+f'</tbody></table></div><p><a class="btn g s" href="/compare/?crop={E(c)}">Compare mandis</a> <button class="btn g s" type="button" data-csv="pt" data-name="{slug(c)}-prices.csv">Download CSV</button></p></section>'
        sc_=''.join(f'<a href="{cp}{slug(s2)}/">{E(s2)} ({csn[(c,s2)]})</a>' for s2 in sorted({r['state'] for r in rows if r['commodity']==c}) if (c,s2) in cs_ok)
        if sc_:b+=f'<section class="card"><h2>{E(c)} price by state</h2><div class="chips">{sc_}</div></section>'
        write(cp,shell(cp,f'{c} Price Today in India ({nice(pd)}) | MandiRates',ans[:155],(f'{c} price today in India' if fr else f'{c} price in India: latest rates'),ans,b,root+[(c,cp)],[{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":f"What is the highest {c} price today?","acceptedAnswer":{"@type":"Answer","text":ans}}]}],('js/csv.js',)))
    for (c,s) in sorted(cs_ok):
        cp=f'{R}crop/{slug(c)}/';csp=f'{cp}{slug(s)}/'
        L=sorted([r for r in rows if r['commodity']==c and r['state']==s],key=lambda r:-r['md']);Lg=[x for x in L if not x['odd']] or L;top=best(L)
        pd=max((x['date'] for x in L),key=dt);fr=(pd==NOW.strftime('%d/%m/%Y'));vals=sorted(x['md'] for x in Lg);med=vals[len(vals)//2]
        ans=f'{c} price in {s} {"today is" if fr else "on "+nice(pd)+" was"} typically {rs(med)} per quintal (modal), from {rs(vals[0])} to {rs(vals[-1])} across {len(Lg)} mandis. Highest: {rs(top["md"])} at {top["market"]}, {top["district"]}.'
        trs=''.join(f'<tr{" class=best" if x is top else ""}><td>{E(x["market"])}</td><td>{(f"<a href=\"{R}{slug(s)}/{slug(x[chr(100)+chr(105)+chr(115)+chr(116)+chr(114)+chr(105)+chr(99)+chr(116)])}/{slug(c)}/\">{E(x[chr(100)+chr(105)+chr(115)+chr(116)+chr(114)+chr(105)+chr(99)+chr(116)])}</a>") if (s,x["district"],c) in allowed else E(x["district"])}</td><td>{rs(x["mn"])}</td><td class="p">{rs(x["md"])}{" ⚠" if x.get("odd") else ""}</td><td>{rs(x["mx"])}</td><td>{E(x["date"])}</td></tr>' for x in L[:60])
        b=f'<section class="card"><p class="big">{E(ans)}</p><div class="tw"><table id="pt"><thead><tr><th>Mandi</th><th>District</th><th>Min</th><th>Modal</th><th>Max</th><th>Date</th></tr></thead><tbody>{trs}</tbody></table></div><p><a class="btn g s" href="/compare/?crop={E(c)}">Compare mandis</a> <button class="btn g s" type="button" data-csv="pt" data-name="{slug(c)}-{slug(s)}.csv">Download CSV</button></p></section><section class="card"><h2>More about {E(c)} and {E(s)}</h2><div class="chips"><a href="{cp}">{E(c)} price in India</a><a href="{R}{slug(s)}/">All prices in {E(s)}</a></div></section>'
        write(csp,shell(csp,f'{c} Price in {s} ({nice(pd)}) | MandiRates',ans[:155],f'{c} price in {s}'+(' today' if fr else ': latest rates'),E(ans),b,root+[(c,cp),(s,csp)],[{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":f"What is the {c} price in {s} today?","acceptedAnswer":{"@type":"Answer","text":ans}}]}],('js/csv.js',)))
    for s in sorted(S):
        sp=f'{R}{slug(s)}/';ds=sorted(S[s]);scr=root+[(s,sp)];spd=max((x['date'] for d in S[s] for c in S[s][d] for x in S[s][d][c]),key=dt)
        write(sp,shell(sp,f'Mandi Prices in {s} ({nice(spd)}) | MandiRates',f'Today’s mandi prices in {s} by district and crop, per quintal.',f'Mandi prices in {s}',f'Choose a district in {E(s)} to see today’s crop rates per quintal.','<section class="card"><div class="chips">'+''.join(f'<a href="{sp}{slug(d)}/">{E(d)} ({len(S[s][d])})</a>' for d in ds)+'</div></section>'+state_crops(s),scr))
        for d in ds:
            dp=f'{sp}{slug(d)}/';dcr=scr+[(d,dp)];items='';dpd=max((x['date'] for c in S[s][d] for x in S[s][d][c]),key=dt)
            for c in sorted(S[s][d]):
                m=best(sorted(S[s][d][c],key=lambda x:-x['md']))['md'];items+=f'<li><div>{(f"<a href=\"{dp}{slug(c)}/\">{E(c)}</a>") if (s,d,c) in allowed else E(c)}</div><div class="p">{rs(m)}</div></li>'
            write(dp,shell(dp,f'Mandi Prices in {d}, {s} ({nice(dpd)}) | MandiRates',f'Today’s mandi rates in {d}, {s}: crop prices per quintal.',f'Mandi prices in {d}, {s}',f'Latest crop prices in {E(d)} district, per quintal.',f'<section class="card"><h2>Crops</h2><p class="hint">Highest modal price in this district</p><ul class="mv">{items}</ul></section>',dcr))
            for c in sorted(S[s][d]):
                if (s,d,c) not in allowed:continue
                L=sorted(S[s][d][c],key=lambda x:-x['md']);cp=f'{dp}{slug(c)}/';top=best(L);low=min(x['mn'] for x in L);high=max(x['mx'] for x in L);date=max((x['date'] for x in L),key=dt)
                fr2=(date==NOW.strftime('%d/%m/%Y'))
                plain=f'{c} price in {d} district {"today is" if fr2 else "on "+nice(date)+" was"} {rs(top["md"])} per quintal (modal) at {top["market"]} mandi, ranging {rs(low)} to {rs(high)} across {len(L)} listing{"s" if len(L)>1 else ""}. Last updated {date}.'
                ch=svg_chart(series_for(SD[s],top) or [],f'{c} price trend at {top["market"]}')
                hist=f'<section class="card"><h2>Price trend at {E(top["market"])}</h2>{ch}</section>' if ch else f'<section class="card"><h2>Price trend</h2><p class="mut">History builds one day at a time. A chart appears here after a few days of saved prices.</p></section>'
                sib=[x for x in sorted(S[s]) if x!=d and (s,x,c) in allowed][:8];oth=[x for x in sorted(S[s][d]) if x!=c and (s,d,x) in allowed][:8];rel=''
                if sib or oth:rel='<section class="card"><h2>More prices nearby</h2>'+(f'<p class="hint">{E(c)} in other districts of {E(s)}</p><div class="chips">'+''.join(f'<a href="{sp}{slug(x)}/{slug(c)}/">{E(x)}</a>' for x in sib)+'</div>' if sib else '')+(f'<p class="hint">Other crops in {E(d)}</p><div class="chips">'+''.join(f'<a href="{dp}{slug(x)}/">{E(x)}</a>' for x in oth)+'</div>' if oth else '')+'</section>'
                b=f'<section class="card"><p class="big">{E(plain)}</p>{table(L)}<p><a class="btn g s" href="/compare/?crop={E(c)}">Compare mandis</a> <button class="btn g s" type="button" data-csv="pt" data-name="{slug(c)}-{slug(d)}.csv">Download CSV</button></p></section>{hist}{rel}<section class="card"><h2>Frequently asked</h2><details open><summary>What is the {E(c)} price in {E(d)} today?</summary><p>{E(plain)}</p></details><details><summary>Where does this price come from?</summary><p>From the Government of India open data portal (Agmarknet). Confirm with the mandi before you trade.</p></details></section>'
                write(cp,shell(cp,f'{c} Price in {d}, {s} ({nice(date)}) | MandiRates',plain[:155],(f'{c} price in {d} today' if fr2 else f'{c} price in {d}: latest rates'),E(plain),b,dcr+[(c,cp)],[{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":f"What is the {c} price in {d} today?","acceptedAnswer":{"@type":"Answer","text":plain}}]}],('js/csv.js',)))
    # data + static
    os.makedirs(os.path.join(OUT,'data'),exist_ok=True)
    json.dump({'demo':DEMO,'updated':latest,'rows':rows},open(os.path.join(OUT,'data','latest.json'),'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
    if not DEMO and os.path.isdir(SERIES_DIR):shutil.copytree(SERIES_DIR,os.path.join(OUT,'data','series'))
    src=os.path.join(ROOT,'src')
    for f in('theme.css','app.js','logic.js','hi.js'):shutil.copy(os.path.join(src,f),OUT)
    shutil.copytree(os.path.join(src,'js'),os.path.join(OUT,'js'))
    open(os.path.join(OUT,'js','csv.js'),'w').write('')  # CSV buttons are wired by app.js
    open(os.path.join(OUT,'js','poster.js'),'w').write("document.addEventListener('DOMContentLoaded',function(){var b=document.getElementById('pp');if(b)b.addEventListener('click',function(){window.print()})});")
    for f in('manifest.webmanifest','icon.svg','robots.txt','_headers','icon-192.png','icon-512.png','og.png','config.js','_redirects'):
        p=os.path.join(ROOT,'static',f)
        if os.path.exists(p):shutil.copy(p,OUT)
    for f in os.listdir(os.path.join(ROOT,'static')):
        if re.fullmatch(r'google[0-9a-f]+\.html|BingSiteAuth\.xml|yandex_[0-9a-f]+\.html',f):shutil.copy(os.path.join(ROOT,'static',f),OUT)
    open(os.path.join(OUT,'robots.txt'),'w').write(f'User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /data/\nDisallow: /poster/\n\nSitemap: {BASE}/sitemap.xml\n')
    sw=open(os.path.join(ROOT,'static','sw.js')).read().replace('__BUILD__',BUILD);open(os.path.join(OUT,'sw.js'),'w').write(sw)
    smu=[u for u in written if u not in('/404.html','/poster/')]
    lm=datetime.datetime.strptime(latest,'%d/%m/%Y').strftime('%Y-%m-%d') if latest else datetime.date.today().isoformat()
    main_u=[u for u in smu if not u.startswith('/mandi-prices/') or u=='/mandi-prices/'];price_u=[u for u in smu if u.startswith('/mandi-prices/') and u!='/mandi-prices/']
    files=[('sitemap-main.xml',main_u)]+[(f'sitemap-prices-{k+1}.xml',price_u[k*10000:(k+1)*10000]) for k in range((len(price_u)+9999)//10000)]
    for n,Lu in files:open(os.path.join(OUT,n),'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{BASE+u}</loc><lastmod>{lm}</lastmod></url>' for u in Lu)+'</urlset>')
    open(os.path.join(OUT,'sitemap.xml'),'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<sitemap><loc>{BASE}/{n}</loc><lastmod>{lm}</lastmod></sitemap>' for n,_ in files)+'</sitemapindex>')
    print(f'Built {len(written)} pages from {len(rows)} valid rows ({len(fresh)} fresh, {max(carried,0)} carried from earlier days); demo={DEMO}')
if __name__=='__main__':main()

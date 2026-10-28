#!/usr/bin/env python3
"""Price tracker for explicitly authorized CSV/JSON feeds. Python stdlib only."""
import csv,io,json,os,pathlib,datetime,urllib.request,urllib.parse,re
ROOT=pathlib.Path(__file__).resolve().parent
DATA=ROOT/'data';DATA.mkdir(exist_ok=True)
MAX_BYTES=12_000_000
CATEGORIES=['GPU','CPU','RAM','SSD','Motherboard','PSU','Case','Cooling','Monitor','Other']
def read_json(p,default):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except (FileNotFoundError,json.JSONDecodeError):return default
def valid_url(url):
    p=urllib.parse.urlparse(str(url));return p.scheme=='https' and bool(p.hostname) and not p.username and not p.password

def fetch(url):
    if not valid_url(url):raise ValueError('Only HTTPS feed URLs allowed')
    req=urllib.request.Request(url,headers={'User-Agent':'PCDealNorge/2.0 (+authorized-feed-client)'})
    with urllib.request.urlopen(req,timeout=25) as response:
        if response.geturl()!=url and not valid_url(response.geturl()):raise ValueError('Unsafe redirect')
        raw=response.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise ValueError('Feed too large')
    return raw.decode('utf-8-sig')
def parse_rows(content,fmt):
    data=json.loads(content) if fmt=='json' else list(csv.DictReader(io.StringIO(content)))
    if isinstance(data,dict):data=data.get('products',data.get('items',[]))
    if not isinstance(data,list):raise ValueError('Feed must contain a product list')
    return data

def normalized(row,config):
    mapping=config.get('columns',{})
    def get(k):return row.get(mapping.get(k,k),'')
    name=str(get('name')).strip();store=str(config.get('store') or get('store')).strip()
    url=str(get('url')).strip();rawprice=str(get('price_nok')).replace(' ','').replace('\u00a0','').replace(',','.')
    try:price=round(float(rawprice),2)
    except (ValueError,TypeError):return None
    if not name or not store or not valid_url(url) or not 0<price<10000000:return None
    ean=str(get('ean')).strip();pid=str(get('id')).strip() or ean or re.sub('[^a-z0-9]+','-',name.lower()).strip('-')
    category=str(get('category')).strip() or 'Other'
    if category not in CATEGORIES:category='Other'
    affiliate=str(get('affiliate_url')).strip();image=str(get('image_url')).strip()
    try:shipping=max(0,float(str(get('shipping_nok') or 0).replace(',','.')))
    except ValueError:shipping=0
    stock=str(get('in_stock')).strip().lower() not in ('false','0','no','nei','out of stock')
    return {'id':pid,'name':name[:180],'store':store[:70],'category':category,'price_nok':price,'shipping_nok':round(shipping,2),'total_nok':round(price+shipping,2),'url':url,'affiliate_url':affiliate if valid_url(affiliate) else '', 'image_url':image if valid_url(image) else '', 'ean':ean[:32],'in_stock':stock}

def main():
    now=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    configs=[{'name':'Local CSV','path':'products.csv','format':'csv'}]+read_json(ROOT/'feeds.json',[])
    for store in read_json(ROOT/'stores.json',[]):
        env=store['feed_env'];url=os.getenv(env,'').strip()
        if url:configs.append({'name':store['name'],'store':store['name'],'url':url,'format':'json' if urllib.parse.urlparse(url).path.lower().endswith('.json') else 'csv'})
    items={};errors=[];successful=0
    for cfg in configs:
        try:
            if cfg.get('enabled') is False:continue
            if cfg.get('url'):
                url=os.path.expandvars(cfg['url']);content=fetch(url)
            else:
                path=(ROOT/cfg['path']).resolve()
                if not path.is_relative_to(ROOT):raise ValueError('Feed path outside project')
                content=path.read_text(encoding='utf-8-sig')
            for row in parse_rows(content,cfg.get('format','csv')):
                if not isinstance(row,dict):continue
                product=normalized(row,cfg)
                if product:items[product['store']+'|'+product['id']]=product
            successful+=1
        except Exception as exc:errors.append(f"{cfg.get('name','Feed')}: {exc}")
    history=read_json(DATA/'history.json',{});old=read_json(DATA/'products.json',{});previous={p['store']+'|'+p['id']:p for p in old.get('products',[])}
    output=[];alerts=[]
    for key,item in sorted(items.items()):
        points=history.setdefault(key,[])
        oldprice=previous.get(key,{}).get('price_nok')
        if not points or points[-1]['price_nok']!=item['price_nok']:
            points.append({'at':now,'price_nok':item['price_nok']})
        points[:]=points[-365:]
        item['previous_price_nok']=oldprice
        item['historical_low_nok']=min(p['price_nok'] for p in points)
        item['drop_percent']=round((oldprice-item['price_nok'])/oldprice*100,1) if oldprice and item['price_nok']<oldprice else 0
        item['observations']=len(points);item['history']=points[-60:]
        output.append(item)
        if item['drop_percent']>=10 and item['in_stock']:alerts.append(item)
    # Avoid erasing the live catalogue if all feeds fail.
    if successful==0 and previous:
        errors.append('All feeds failed; previous catalogue preserved')
        output=list(previous.values())
    payload={'updated_at':now,'products':output,'sources_ok':successful,'source_errors':errors}
    (DATA/'products.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    (DATA/'history.json').write_text(json.dumps(history,ensure_ascii=False,indent=2),encoding='utf-8')
    hook=os.getenv('DISCORD_WEBHOOK_URL','')
    if hook and valid_url(hook):
        for item in alerts[:10]:
            msg={'content':f"PCDeal: {item['name']} — {item['store']} {item['price_nok']:,.0f} kr ({item['drop_percent']}% ned siden forrige registrerte pris) {item['url']}"}
            try:
                req=urllib.request.Request(hook,data=json.dumps(msg).encode(),headers={'Content-Type':'application/json'},method='POST')
                urllib.request.urlopen(req,timeout=15).close()
            except Exception as exc:errors.append(f'Discord alert: {exc}')
    print(f'Imported {len(output)} offers from {successful} sources. Alerts: {len(alerts)}')
    for e in errors:print('WARNING:',e)
if __name__=='__main__':main()

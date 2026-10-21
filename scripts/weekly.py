"""Read the same unauthenticated circular requests used by Walgreens' public shopper.
No login, private account data, checkout actions or private API credentials.
"""
import hashlib
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from lxml import html

API='https://wag-dwa-api-prod.przone.net/'
WEEKLY_URL='https://www.walgreens.com/offers/offers.jsp?view=weeklyad&store_code=677'
STORE=677

def request_json(path):
    req=urllib.request.Request(API+path, data=json.dumps({'store':{'storeNumber':STORE}}).encode(),
       headers={'Content-Type':'application/json','Accept':'application/json','User-Agent':'PeseteandoPR/2.0'})
    with urllib.request.urlopen(req,timeout=25) as r:return json.loads(r.read(5_000_000))

def plain(s):
    return ' '.join(html.fromstring('<div>'+str(s or '')+'</div>').text_content().split())

def money(v):
    s=str(v).strip()
    return '$'+s if re.fullmatch(r'\d+(?:\.\d{1,2})?',s) else None

def pricing(o):
    d=o.get('dataColumns') or {};t=o.get('pricingTemplateName','');q=str(d.get('Quantity',''));g=str(d.get('GetFree',''))
    a,b=money(d.get('AdRetail','')),money(d.get('SingleItemPrice',''))
    value='';unit_price=None
    if 'BOGO PercentOff' in t and q.isdigit() and g.isdigit() and str(d.get('BOGOPercentOff','')).isdigit():
        value=f'Compra {q} + {g} con {d["BOGOPercentOff"]}% dto.'
    elif 'BOGO FREE' in t and q.isdigit() and g.isdigit():value=f'Compra {q} + {g} GRATIS'
    elif 'BXGY for STD' in t and q.isdigit() and g.isdigit() and a:value=f'Compra {q} + {g} por {a}'
    elif 'Price 2For' in t and q.isdigit() and a:value=f'{q} por {a}'+(f' · 1 a {b}' if b else '')
    elif 'Price Range' in t and a and b:value=f'{a}–{b} c/u'
    elif 'Price Percent Off' in t and str(d.get('PercentOff','')).isdigit():value=f'{d["PercentOff"]}% de descuento'
    elif 'Price Dollar Off' in t and money(d.get('AdPriceDollarOff','')):value=f'{money(d["AdPriceDollarOff"])} de descuento'
    elif 'Price STD' in t and a:value=f'{a} c/u';unit_price=float(d['AdRetail'])
    reward='';rw=money(d.get('RegisterReward',''))
    if rw:
        suffix=f'al gastar {money(d["RewardSpend"])}' if money(d.get('RewardSpend','')) else f'al comprar {d["LTYRewardQuantity"]}' if str(d.get('LTYRewardQuantity','')).isdigit() else 'en productos elegibles'
        if 'BR ' in t:reward=f'{rw} en Walgreens Cash {suffix}; para una compra futura.'
        elif 'RR' in t:reward=f'{rw} en recompensa de tienda {suffix}; para una compra futura.'
    if not value and reward:value='Recompensa en tienda'
    return value,unit_price,reward

def parse_weekly(circular, collections, disclaimer, now=None):
    now=now or datetime.now(timezone.utc)
    if circular.get('marketVersion')!='PR' or not circular.get('isPublished'):
        raise ValueError('El shopper no está identificado como PR y publicado')
    start=datetime.fromisoformat(circular['startDate']).replace(tzinfo=ZoneInfo('America/Puerto_Rico'))
    end=datetime.combine(datetime.fromisoformat(circular['endDate']).date(),time(23,59,59),ZoneInfo('America/Puerto_Rico'))
    if not start<=now<=end:raise ValueError('Shopper fuera de vigencia')
    disclaimer=plain(disclaimer)
    # Fail closed if regional exclusions or the local membership instructions disappear.
    if not re.search(r'shopper no es válido',disclaimer,re.I) or 'myWalgreens' not in disclaimer:
        raise ValueError('Faltan condiciones regionales legibles')
    exclusion=disclaimer.split('Este shopper no es válido',1)[-1].split('Ver detalles',1)[0]
    exclusions=re.findall(r'#(\d+)',exclusion)
    if str(STORE) in exclusions:raise ValueError('La sucursal de referencia está excluida')
    result=[]
    for c in collections:
        if c.get('catalogId')!=circular['catalogId']:raise ValueError('Colección de otro catálogo')
        for o in c.get('offers',[]):
            title=plain(o.get('pricingHeader'));image=o.get('imageUrl') or o.get('featureConfig',{}).get('mediaImg') or ''
            if o.get('offerType')=='teaser' or not title or title.startswith('PR_') or 'Evergreen' in o.get('pricingTemplateName','') or not image.startswith('https://'):continue
            if not str(o.get('pricingTemplateName','')).startswith('PR '):continue
            value,price,reward=pricing(o)
            if not value:continue
            try:
                offer_start=datetime.fromisoformat(o['startDate']).replace(tzinfo=ZoneInfo('America/Puerto_Rico'))
                offer_end=min(end,datetime.combine(datetime.fromisoformat(o['endDate']).date(),time(23,59,59),ZoneInfo('America/Puerto_Rico')))
            except (ValueError,KeyError):continue
            if not offer_start<=now<=offer_end:continue
            d=o.get('dataColumns') or {};coupon_discount=money(d.get('InstantCoupon',''))
            body=plain(o.get('pricingBody'));terms=plain(o.get('disclaimerText'))
            conditions=['Oferta del shopper oficial de Puerto Rico; artículos y variedades elegibles, mientras duren las existencias.']
            requires_membership=bool(d.get('myWalgreens')) or 'membresía' in disclaimer
            if requires_membership:conditions.append('Identifica tu membresía myWalgreens antes de finalizar la compra en caja.')
            if terms:conditions.append(terms)
            if coupon_discount:conditions.append(f'El shopper anuncia un cupón Walgreens adicional de {coupon_discount}. No se ha restado del precio mostrado; consulta y activa el cupón elegible.')
            if reward:conditions.append(reward+' No se descuenta del precio de esta compra.')
            if exclusions:conditions.append('Sucursales excluidas del shopper: '+', '.join('#'+x for x in exclusions)+'. Consulta sus direcciones en las condiciones oficiales.')
            if coupon_discount:
                instructions=['Abre el cupón oficial de Walgreens y actívalo en tu cuenta antes de pagar.','Comprueba la presentación y cantidad de productos elegibles.','Da tu número de myWalgreens en caja; confirma el precio y el cupón en el recibo.']
            else:instructions=['Elige los artículos y las cantidades indicadas en el shopper.','Da tu número de myWalgreens antes de que termine la compra.','Comprueba el precio anunciado y cualquier recompensa en el recibo.']
            result.append({'id':'weekly-'+str(o.get('offerVersionGroupId') or o['uniqueId']), 'retailer_id':'walgreens','kind':'weekly_ad','code':None,
             'title':title,'official_title':title,'presentation':body or 'Presentación no especificada; ver artículos elegibles en Walgreens.',
             'store':'Walgreens','category':c.get('name','Shopper PR'),'category_id':'weekly','discount':value,'percent':int(d['PercentOff']) if 'Price Percent Off' in o.get('pricingTemplateName','') and str(d.get('PercentOff','')).isdigit() else None,'minimum':None,
             'price':price,'price_text':value,'reward':reward or None,'coupon_discount':coupon_discount,
             'coupon_ids':[x['couponId'] for x in o.get('coupons') or [] if x.get('couponId')],
             'new_customer':False,'expires':offer_end.date().isoformat(),'expires_at':offer_end.astimezone(timezone.utc).isoformat(),
             'starts_at':offer_start.astimezone(timezone.utc).isoformat(),'source_id':'weekly_pr','source':o.get('offerLinkUrl') or WEEKLY_URL,
             'image':image,'image_kind':'merchant_product','conditions':conditions,'instructions':instructions,
             'channels':['store'],'requires_activation':bool(coupon_discount),'requires_membership':requires_membership,
             'pr_status':'official_pr','pr_label':'Anunciada para PR','pr_note':'Publicada en el shopper PR para sucursales participantes. No garantiza existencia del producto ni se ha probado la compra.',
             'verification_level':'official_regional_terms','redemption_tested':False,'stock_status':'not_checked','excluded_stores':exclusions,
             'checked_at':now.isoformat(),'evidence_hash':hashlib.sha256(json.dumps({'catalog':circular['catalogId'],'offer':o,'regional_terms':disclaimer},sort_keys=True).encode()).hexdigest(),
             'collection_id':c.get('collectionId'),'reference_store':STORE})
    return list({o['id']:o for o in result}.values())

def load_weekly(fixtures=False,now=None):
    if fixtures:
        circular=json.loads(Path('/tmp/pr-circular.json').read_text());disclaimer=json.loads(Path('/tmp/pr-disclaimer.json').read_text())
        collections=[json.loads(p.read_text()) for p in Path('/tmp/pr-collections').glob('*.json')]
    else:
        circular=request_json('api/wag/dwa/circular');disclaimer=request_json('api/wag/dwa/circular/disclaimer')
        if circular.get('marketVersion')!='PR':raise ValueError('Se rechazó un catálogo no regional')
        pages=[p for p in circular.get('pages',[]) if p.get('isActive') and not p.get('isHidden')]
        if not pages or len(pages)>30:raise ValueError('Estructura de catálogo no reconocida')
        def collection(p):return request_json('api/wag/dwa/collection?collectionid='+p['collectionId']+'&store='+str(STORE))
        with ThreadPoolExecutor(max_workers=4) as pool:collections=list(pool.map(collection,pages))
    offers=parse_weekly(circular,collections,disclaimer,now)
    if not offers:raise ValueError('Shopper sin ofertas legibles')
    return offers,{'market':'PR','reference_store':STORE,'period_start':circular['startDate'][:10],'period_end':circular['endDate'][:10],'catalog_id':circular['catalogId'],'collections':len(collections)}

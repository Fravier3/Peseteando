"""Read public merchant terms. Never turn coupon IDs into promo codes or infer PR acceptance."""
import argparse
import hashlib
import json
import re
import urllib.request
from datetime import datetime, time, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from lxml import html
try:
    from .weekly import load_weekly, WEEKLY_URL, plain
except ImportError:
    from weekly import load_weekly, WEEKLY_URL, plain

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'walgreens': 'https://www.walgreens.com/promotion/offer-details',
    'photo': 'https://photo.walgreens.com/store/deals',
    'coupons_pr': 'https://www.walgreens.com/offers/offers.jsp?storeid=677',
    'weekly_pr': WEEKLY_URL,
}
MONTHS = 'January February March April May June July August September October November December'.split()
DATE = re.compile(r'(' + '|'.join(MONTHS) + r')\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(20\d{2})', re.I)
PR_EXCLUSION = re.compile(r'(?:not\s+(?:available|valid)|exclud(?:es?|ed|ing))[^.;]{0,90}(?:\bPR\b|Puerto\s+Rico)|(?:\bPR\b|Puerto\s+Rico)[^.;]{0,50}(?:excluded|not\s+(?:available|valid))', re.I)
CATEGORY = {'general': 'Compra online', 'photo': 'Fotografía', 'beauty': 'Belleza', 'pickup': 'Recogido', 'delivery': 'Entrega'}

def clean(value):
    return ' '.join(value.split())

def expiry(terms):
    # Require explicit year; never roll an expired promotion forward into a new year.
    matches = list(DATE.finditer(clean(terms)))
    if len(matches) != 1:
        return None
    m = matches[0]
    try:
        d = datetime(int(m[3]), MONTHS.index(m[1].capitalize()) + 1, int(m[2])).date()
    except ValueError:
        return None
    if not re.search(r'11:59\s*(?:p\.?m\.?|pm)', terms, re.I) or not re.search(r'Central Time|\bCT\b', terms):
        return None
    return datetime.combine(d, time(23, 59, 59), ZoneInfo('America/Chicago'))

def section_text(heading):
    parts = []
    for node in heading.itersiblings():
        if isinstance(node.tag, str) and re.fullmatch('h[1-6]', node.tag):
            break
        parts.append(node.text_content())
    return clean(' '.join(parts))

def parse(source_id, markup, now=None):
    now = now or datetime.now(timezone.utc)
    doc = html.fromstring(markup)
    offers = []
    if source_id == 'coupons_pr':
        return parse_coupons(markup, now)
    for h in doc.xpath('//h3' if source_id == 'walgreens' else '//h5'):
        title, terms = clean(h.text_content()), section_text(h)
        if source_id == 'photo':
            m = re.search(r'Must use code\s+([A-Z0-9]{3,24})\b', terms)
        else:
            m = re.search(r'with code\s+([A-Z0-9]{3,24})\b', title, re.I)
        if not m or PR_EXCLUSION.search(terms):
            continue
        code = m[1].upper()
        end = expiry(terms)
        if not end or end < now:
            continue
        percent = re.search(r'(\d{1,2})\s*%\s*(?:off|OFF)', title)
        amount = re.search(r'\$(\d+(?:\.\d+)?)\s*off', title, re.I)
        if not percent and not amount and not re.search(r'\bFree\b', title, re.I):
            continue
        minimum = re.search(r'\$(\d+(?:\.\d+)?)\+?', title) if not amount else None
        category = 'photo' if source_id == 'photo' else 'general'
        if 'Maybelline' in title: category = 'beauty'
        if 'Pickup' in title: category = 'pickup'
        if 'Delivery' in title: category = 'delivery'
        discount = f'{percent[1]}%' if percent else f'${amount[1]}' if amount else 'GRATIS'
        names = {
            'general': 'Artículos elegibles online', 'beauty': 'Labiales Maybelline seleccionados',
            'pickup': 'Pedido con recogido el mismo día', 'delivery': 'Entrega en una hora',
        }
        if category == 'photo':
            name = title
            for a,b in [('Everything Photo','Todo en fotografía'), ('All Cards & Premium Stationery','Tarjetas y papelería premium'),('Photo Ornaments','Adornos con fotos'),('Same Day Wood Panels','Paneles de madera'),('Same Day Custom Bottle Labels','Etiquetas para botellas')]:
                if a.lower() in title.lower(): name = b
        else: name = names[category]
        new_customer = bool(re.search(r'new customers', title, re.I))
        conditions = ['Aplicar el código antes de pagar; solo en artículos o servicios elegibles.',
                      'Revisa las exclusiones y reglas de combinación en la fuente oficial.']
        if minimum: conditions.insert(0, f'Compra mínima de ${minimum[1]} en artículos elegibles; consulta cómo se calcula en los términos.')
        if new_customer: conditions.insert(0, 'Exclusivo para clientes nuevos.')
        if category == 'beauty': conditions.insert(0, 'Compra 2 o más labiales Maybelline elegibles; excluye Baby Lips.')
        if category == 'photo': conditions.insert(0, 'Requiere cuenta de Walgreens Photo. La disponibilidad del servicio depende de la tienda.')
        if category == 'pickup': conditions.insert(0, 'Solo pedidos elegibles para recogido el mismo día.')
        if category == 'delivery': conditions.insert(0, 'Descuento del cargo de entrega; sujeto a cobertura del servicio.')
        if re.search(r'3 uses per account',terms,re.I): conditions.append('Hasta 3 usos por cuenta y 1 por pedido, según los términos.')
        elif re.search(r'1 use[s]? per account',terms,re.I): conditions.append('Hasta 1 uso por cuenta, según los términos.')
        # Image comes from an actual matching source tile; no invented product photographs.
        image = ''
        if source_id == 'photo':
            for tile in doc.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," tile-l3-v1 ")]'):
                if re.search(r'Coupon code:\s*' + re.escape(code) + r'\b',tile.text_content()):
                    imgs = tile.xpath('.//img/@data-pagespeed-lazy-src | .//img/@data-src | .//img/@src')
                    image = next((u for u in imgs if u.startswith('https://')), '')
                    break
        channels = ['online']
        if category == 'pickup' or re.search(r'Order must be placed for Same Day Pick', terms, re.I): channels.append('pickup')
        if source_id == 'photo' and re.search(r'in.store.*?kiosk', terms, re.I): channels.append('photo_kiosk')
        offers.append({
            'id': source_id + '-' + code, 'code': code, 'retailer_id':'walgreens', 'kind':'promo_code', 'title': name, 'official_title': title,
            'store': 'Walgreens Photo' if source_id == 'photo' else 'Walgreens',
            'category': CATEGORY[category], 'category_id': category, 'discount': discount,
            'percent': int(percent[1]) if percent else None, 'minimum': float(minimum[1]) if minimum else None,
            'new_customer': new_customer, 'expires': end.date().isoformat(),
            'expires_at': end.astimezone(timezone.utc).isoformat(),
            'source_id': source_id, 'source': SOURCES[source_id] + ('#'+code if source_id == 'photo' else ''),
            'image': image, 'image_kind':'merchant_product' if image else 'general_promotion', 'conditions': conditions,
            'presentation':'Oferta general; no corresponde a un producto o presentación únicos.' if category != 'photo' else 'Servicio fotográfico; consulta formatos elegibles.',
            'price':None, 'price_text':None, 'channels':channels, 'requires_activation':False,
            'instructions':(['Haz un pedido online para recoger en una sucursal elegible.','Pega el código antes de pagar online.','Confirma el descuento en el total; no se aplica al recoger.'] if category == 'pickup' else ['Entra a Walgreens.com o a Walgreens Photo, según corresponda.','Elige productos o servicios elegibles y pega el código al finalizar el pedido.','Confirma que aparezca el descuento antes de pagar.']),
            'verification_level':'official_source_only', 'redemption_tested':False, 'stock_status':'not_checked',
            'pr_status': 'unverified', 'pr_label': 'Sin verificar en PR',
            'pr_note': 'La fuente no excluye expresamente a Puerto Rico. Su aceptación para tu tienda o dirección de PR aún no se ha comprobado en el carrito.',
            'checked_at': now.isoformat(), 'evidence_hash': hashlib.sha256((title+terms).encode()).hexdigest(),
        })
    return list({o['id']: o for o in offers}.values())

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'PeseteandoPR/1.0 (+https://fravier3.github.io/Peseteando/)'})
    with urllib.request.urlopen(req, timeout=30) as response:
        if 'html' not in response.headers.get('Content-Type', ''): raise ValueError('Respuesta inesperada')
        return response.read(4_000_000).decode('utf-8')

def parse_coupons(markup, now):
    states=[]
    for match in re.finditer(r'window\.__APP_INITIAL_STATE__\s*=\s*',markup):
        try:states.append(json.JSONDecoder().raw_decode(markup[match.end():])[0])
        except (ValueError,IndexError):pass
    state=next((x for x in reversed(states) if (x.get('CouponCard',{}).get('recommendData') or {}).get('coupons')),None)
    if not state:raise ValueError('No se encontró catálogo público de cupones')
    store=state.get('StoreLocator',{});context=store.get('storeAddressData') or {}
    regional=store.get('isPrStore') is True and (context.get('address') or {}).get('state')=='PR'
    coupons=state['CouponCard']['recommendData']['coupons'];offers=[]
    for c in coupons:
        # Manufacturer coupons and personalized loyalty offers are not in-store PR offers.
        if c.get('source')!='Walgreens IVC' or c.get('redemptionType')!='POS' or c.get('type')!='AmountOff':continue
        if c.get('isEmplCoupon') or c.get('isJustForYou') or c.get('sneakpeek'):continue
        terms=clean(str(c.get('description',''))+' '+str(c.get('offerDisclaimer','')))
        if PR_EXCLUSION.search(terms):continue
        try:
            end=datetime.combine(datetime.strptime(c['expiryDate'],'%m/%d/%y').date(),time(23,59,59),ZoneInfo('America/Puerto_Rico'))
            start=datetime.fromtimestamp(float(c['activeDateAsUTC'])/1000,timezone.utc)
            value=float(c['offerValue']);qty=int(c['minQty'])
            if not start<=now<=end or value<=0 or qty<1:continue
        except (KeyError,ValueError,TypeError):continue
        offers.append({
            'id':'coupon-'+str(c['id']),'retailer_id':'walgreens','kind':'digital_coupon','code':None,'coupon_id':c['id'],
            'title':plain(c.get('brandName')),'official_title':plain(c.get('brandName')),
            'presentation':plain(c.get('description')) or 'Consulta los productos y presentaciones elegibles en Walgreens.',
            'store':'Walgreens','category':c.get('categoryName','Cupones'),'category_id':'digital',
            'discount':f'${value:g} de descuento','discount_amount':value,'minimum_quantity':qty,'percent':None,'minimum':None,
            'price':None,'price_text':None,'new_customer':False,'expires':end.date().isoformat(),'expires_at':end.astimezone(timezone.utc).isoformat(),
            'source_id':'coupons_pr','source':SOURCES['coupons_pr'],'image':c.get('image',''),'image_kind':'merchant_product',
            'conditions':[f'Compra {qty} producto(s) elegible(s). No es el precio del producto; es el importe del cupón.',
                'Activa el cupón en tu cuenta Walgreens antes de comprar. Guardarlo en Peseteando no lo activa.',
                'La publicación no confirma inventario, disponibilidad en tu cuenta ni el resultado de una compra.'],
            'instructions':['Abre Walgreens y busca el cupón por el nombre del producto.','Pulsa Clip o Agregar en tu cuenta myWalgreens antes de pagar.',
                'Compra los tamaños y cantidades elegibles y da tu número de myWalgreens en caja. Revisa el recibo.'],
            'channels':['store'],'requires_activation':True,'pr_status':'official_pr' if regional else 'unverified',
            'pr_label':'Catálogo oficial PR' if regional else 'Sin verificar en PR',
            'pr_note':'Cupón de Walgreens, no de fabricante nacional, publicado con tienda y contexto PR y canje POS. Confirmar elegibilidad en tu cuenta y sucursal.' if regional else 'La fuente no confirmó un contexto de tienda de Puerto Rico.',
            'verification_level':'official_pr_catalog' if regional else 'official_source_only','redemption_tested':False,'stock_status':'not_checked',
            'reference_store':context.get('storeNumber'),'checked_at':now.isoformat(),'evidence_hash':hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()
        })
    return list({o['id']:o for o in offers}.values())

def policy_checks(markups=None):
    urls={'help':'https://www.walgreens.com/topic/help/shophelp/coupons_help.jsp','policy':'https://www.walgreens.com/topic/help/generalhelp/coupon_policy_main.jsp'}
    states={}
    for key,url in urls.items():
        try:
            page=markups[key] if markups else fetch(url)
            doc=html.fromstring(page)
            for tag in doc.xpath('//script|//style'):tag.drop_tree()
            body=clean(doc.text_content())
            if key=='help':ok=bool(re.search(r'National manufacturer coupons will only be available for online redemption in Puerto Rico stores',body,re.I))
            else:ok='must be clipped and attached' in body and 'only accept original Register Rewards' in body
            states[key]={'url':url,'status':'ok' if ok else 'review_required'}
        except Exception:states[key]={'url':url,'status':'error'}
    return states

def refresh(fixtures=None):
    out=ROOT/'offers.json';old=json.loads(out.read_text()) if out.exists() else {};now=datetime.now(timezone.utc)
    offers=[];states=[];failed=False
    fixture_mode=fixtures is not None
    for sid,url in SOURCES.items():
        try:
            extra={}
            if sid=='weekly_pr':found,extra=load_weekly(fixtures=fixture_mode,now=now)
            else:
                markup=Path(fixtures[sid]).read_text() if fixture_mode else fetch(url)
                found=parse(sid,markup,now)
            if not found:raise ValueError('No hay ofertas vigentes legibles')
            offers+=found;states.append({'id':sid,'url':url,'status':'ok','checked_at':now.isoformat(),'count':len(found),**extra})
        except Exception as exc:
            failed=True;retained=[]
            for o in old.get('offers',[]):
                try:
                    if o.get('source_id')==sid and datetime.fromisoformat(o['expires_at'])>=now and datetime.fromisoformat(o['checked_at'])>=now-timedelta(hours=48):retained.append(o)
                except (KeyError,ValueError):pass
            offers+=retained;states.append({'id':sid,'url':url,'status':'error','count':len(retained)})
            print(f'::warning::Fuente {sid}: {type(exc).__name__}; se conservaron {len(retained)} ofertas recientes')
    checks=policy_checks({k:Path('/tmp/pr-'+k+'.html').read_text() for k in ['help','policy']} if fixture_mode else None)
    if any(s['status']!='ok' for s in checks.values()):
        failed=True
        # A changed PR exception requires human review before digital coupons regain local verification.
        for o in offers:
            if o.get('source_id')=='coupons_pr':o.update(pr_status='unverified',pr_label='Sin verificar en PR',pr_note='Las políticas oficiales cambiaron o no pudieron comprobarse. Se requiere revisar la aplicación en PR.')
    # Link exact coupon identities; never use fuzzy brand matching to combine savings.
    indexed={o['coupon_id']:o for o in offers if o.get('coupon_id')}
    for o in offers:
        if o.get('coupon_ids'):
            matches=[indexed[i] for i in o['coupon_ids'] if i in indexed]
            if matches:o['activation_url']=matches[0]['source']
    unique={o['id']:o for o in offers}
    old_ids={o['id'] for o in old.get('offers',[])}
    current_ids=set(unique)
    data={'schema_version':2,'updated':now.isoformat(),'source_status':'partial_error' if failed else 'ok',
          'sources':states,'policy_checks':checks,'offers':list(unique.values()),
          'changes':{'added':len(current_ids-old_ids),'removed':len(old_ids-current_ids)},
          'verification_note':'Verificación documental; sin compras de prueba ni consulta de inventario.'}
    out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(f'Ofertas: {len(unique)}; verificadas PR: {sum(o["pr_status"]=="official_pr" for o in offers)}; fuentes: {sum(s["status"]=="ok" for s in states)}/{len(states)}')
    return failed

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixtures',action='store_true');args=p.parse_args()
    fixtures={'walgreens':'/tmp/pr-promos.html','photo':'/tmp/photo.html','coupons_pr':'/tmp/pr-coupons.html'} if args.fixtures else None
    raise SystemExit(1 if refresh(fixtures) else 0)

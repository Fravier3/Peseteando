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

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'walgreens': 'https://www.walgreens.com/promotion/offer-details',
    'photo': 'https://photo.walgreens.com/store/deals',
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
                      'No se combina con otros códigos en el mismo artículo. Revisa las exclusiones en la fuente oficial.']
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
        offers.append({
            'id': source_id + '-' + code, 'code': code, 'title': name, 'official_title': title,
            'store': 'Walgreens Photo' if source_id == 'photo' else 'Walgreens',
            'category': CATEGORY[category], 'category_id': category, 'discount': discount,
            'percent': int(percent[1]) if percent else None, 'minimum': float(minimum[1]) if minimum else None,
            'new_customer': new_customer, 'expires': end.date().isoformat(),
            'expires_at': end.astimezone(timezone.utc).isoformat(),
            'source_id': source_id, 'source': SOURCES[source_id] + ('#'+code if source_id == 'photo' else ''),
            'image': image, 'conditions': conditions,
            'pr_status': 'pending_checkout', 'pr_label': 'Confirmar en PR',
            'pr_note': 'La fuente no excluye expresamente a Puerto Rico. Su aceptación para tu tienda o dirección de PR aún no se ha comprobado en el carrito.',
            'checked_at': now.isoformat(), 'evidence_hash': hashlib.sha256((title+terms).encode()).hexdigest(),
        })
    return list({o['id']: o for o in offers}.values())

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'PeseteandoPR/1.0 (+https://fravier3.github.io/Peseteando/)'})
    with urllib.request.urlopen(req, timeout=30) as response:
        if 'html' not in response.headers.get('Content-Type', ''): raise ValueError('Respuesta inesperada')
        return response.read(4_000_000).decode('utf-8')

def refresh(fixtures=None):
    out = ROOT / 'offers.json'
    old = json.loads(out.read_text()) if out.exists() else {}
    now = datetime.now(timezone.utc)
    offers, states, failed = [], [], False
    for sid, url in SOURCES.items():
        try:
            markup = Path(fixtures[sid]).read_text() if fixtures else fetch(url)
            found = parse(sid, markup, now)
            if not found: raise ValueError('No se encontraron códigos vigentes con términos y fecha legibles')
            offers += found
            states.append({'id': sid, 'url': url, 'status': 'ok', 'checked_at': now.isoformat(), 'count': len(found)})
        except Exception as e:
            failed = True
            # Keep only recently verified, still-active data, with its original checked_at.
            retained = []
            for o in old.get('offers', []):
                try:
                    if o.get('source_id') == sid and datetime.fromisoformat(o['expires_at']) >= now and datetime.fromisoformat(o['checked_at']) >= now-timedelta(hours=48): retained.append(o)
                except (KeyError,ValueError): pass
            offers += retained
            states.append({'id': sid, 'url': url, 'status': 'error', 'count': len(retained)})
            print(f'::warning::Fuente {sid}: {type(e).__name__}; {len(retained)} códigos recientes conservados')
    data = {'schema_version': 1, 'updated': now.isoformat(), 'source_status': 'partial_error' if failed else 'ok',
            'sources': states, 'offers': list({o['id']:o for o in offers}.values())}
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    print(f'Códigos publicados: {len(data["offers"])}; fuentes correctas: {sum(s["status"]=="ok" for s in states)}/{len(states)}')
    return failed

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--fixtures', action='store_true'); args=p.parse_args()
    raise SystemExit(1 if refresh({'walgreens':'/tmp/promos.html','photo':'/tmp/photo.html'} if args.fixtures else None) else 0)

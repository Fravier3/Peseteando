export function activeOffers(offers, now=Date.now()) {
  return offers.filter(o=>o&&typeof o.id==='string'&&(o.code==null||/^[A-Z0-9]{3,24}$/.test(o.code))&&Number.isFinite(Date.parse(o.expires_at))&&Date.parse(o.expires_at)>=now&&Date.parse(o.checked_at)>=now-48*3600_000&&(!o.starts_at||Date.parse(o.starts_at)<=now));
}
export function normalizeStoreNumber(value) {
  const digits=String(value??'').trim();
  return /^\d{1,5}$/.test(digits)&&Number(digits)>0?String(Number(digits)):'';
}
export function excludedAtStore(offer,storeNumber) {
  const number=normalizeStoreNumber(storeNumber);
  return Boolean(number&&offer.retailer_id==='walgreens'&&offer.channels?.includes('store')&&Array.isArray(offer.excluded_stores)&&offer.excluded_stores.some(x=>normalizeStoreNumber(x)===number));
}
export function filteredOffers(offers,{query='',category='all',mode='all',verification='verified',savedOnly=false,saved=[],sort='recommended',storeNumber=''}={}) {
  const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const isVerified=o=>o.pr_status==='official_pr';
  const modes={store:o=>o.channels?.includes('store'),online:o=>o.channels?.includes('online'),pickup:o=>o.channels?.includes('pickup'),activate:o=>o.requires_activation};
  const list=offers.filter(o=>!excludedAtStore(o,storeNumber)&&(verification==='all'||(verification==='unverified'?!isVerified(o):isVerified(o)))&&(mode==='all'||modes[mode]?.(o))&&(category==='all'||o.category===category)&&(!savedOnly||saved.includes(o.id))&&norm([o.title,o.official_title,o.presentation,o.code,o.store,o.category].join(' ')).includes(norm(query.trim())));
  const rank=o=>o.kind==='weekly_ad'?0:o.kind==='digital_coupon'?1:2;
  return list.sort((a,b)=>sort==='expiry'?Date.parse(a.expires_at)-Date.parse(b.expires_at):sort==='discount'?(b.percent||0)-(a.percent||0):rank(a)-rank(b)||a.title.localeCompare(b.title,'es'));
}
export function usageLabels(o){
  const labels=[];
  if(o.channels?.includes('store'))labels.push('Usar en tienda');
  if(o.channels?.includes('pickup'))labels.push('Recoger en tienda');
  else if(o.channels?.includes('online'))labels.push('Comprar online');
  if(o.requires_activation)labels.push('Activar cupón');
  if(o.channels?.includes('photo_kiosk'))labels.push('Kiosco de fotos');
  return labels;
}

export function activeOffers(offers, now = Date.now()) {
  return offers.filter(o => /^[A-Z0-9]{3,24}$/.test(o.code || '') && Number.isFinite(Date.parse(o.expires_at)) && Date.parse(o.expires_at) >= now && Date.parse(o.checked_at) >= now - 48 * 3600_000);
}
export function filteredOffers(offers, {query='', category='all', savedOnly=false, saved=[], sort='recommended'}={}) {
  const norm = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  let list = offers.filter(o => (category==='all' || o.category_id===category) && (!savedOnly || saved.includes(o.id)) && norm([o.title,o.official_title,o.code,o.store,o.category].join(' ')).includes(norm(query.trim())));
  return list.sort((a,b) => sort==='expiry' ? Date.parse(a.expires_at)-Date.parse(b.expires_at) : sort==='discount' ? (b.percent||0)-(a.percent||0) : (a.category_id==='general'?-1:1)-(b.category_id==='general'?-1:1) || (b.percent||0)-(a.percent||0));
}

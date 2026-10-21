import {activeOffers, filteredOffers} from './catalog.mjs';
const $=id=>document.getElementById(id);
const state={data:null,offers:[],category:'all',query:'',savedOnly:false,sort:'recommended'};
let saved=[];try{const x=JSON.parse(localStorage.getItem('peseteando.saved.v1')||'[]');if(Array.isArray(x))saved=x.filter(v=>typeof v==='string');}catch{}
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeURL=s=>{try{const u=new URL(s);return u.protocol==='https:'?u.href:'';}catch{return '';}};
const date=s=>new Intl.DateTimeFormat('es-PR',{month:'short',day:'numeric',timeZone:'America/Puerto_Rico'}).format(new Date(s));
let toastTimer;
function toast(message){$('toast').textContent=message;$('toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('visible'),2600);}
async function copy(code){try{await navigator.clipboard.writeText(code);toast(`Código ${code} copiado`);}catch{show(`<h2>Copia tu código</h2><p>Mantén presionado el código para copiarlo.</p><p style="font:700 24px monospace;user-select:all">${esc(code)}</p>`);}}
function show(content){$('dialog-content').innerHTML=content;if(!$('dialog').open)$('dialog').showModal();}
function toggleSaved(id){const next=saved.includes(id)?saved.filter(x=>x!==id):[...saved,id];try{localStorage.setItem('peseteando.saved.v1',JSON.stringify(next));saved=next;render();}catch{toast('No se pudo guardar en este navegador. Revisa el almacenamiento.');}}
function render(){
 state.offers=activeOffers(state.data?.offers||[]);
 const list=filteredOffers(state.offers,{...state,saved});
 $('list-title').firstChild.textContent=state.savedOnly?'Mis códigos guardados ':'Códigos disponibles ';
 $('count').textContent=list.length;
 $('saved-count').textContent=state.offers.filter(o=>saved.includes(o.id)).length;
 $('offers').setAttribute('aria-busy','false');
 $('offers').innerHTML=list.map(o=>{
  const days=Math.max(0,Math.ceil((Date.parse(o.expires_at)-Date.now())/86400000));
  const merchantDate=new Intl.DateTimeFormat('es-PR',{month:'short',day:'numeric',...(o.expires.slice(0,4)!==String(new Date().getUTCFullYear())?{year:'numeric'}:{}),timeZone:'UTC'}).format(new Date(o.expires+'T12:00:00Z'));
  const badge=days<=3?`Vence ${days===0?'hoy':days===1?'en 1 día':`en ${days} días`}`:`${merchantDate} · CT`;
  const meta=o.minimum?`Compra mínima $${o.minimum}${o.new_customer?' · Clientes nuevos':''}`:o.new_customer?'Solo clientes nuevos':o.category_id==='beauty'?'En 2 o más elegibles':'Consulta las condiciones';
  const isSaved=saved.includes(o.id);
  return `<article class="offer-card"><div class="card-visual ${esc(o.category_id)}"><span class="expiry-badge ${days<=3?'soon':''}">${esc(badge)}</span><button class="save-button ${isSaved?'is-saved':''}" data-save="${esc(o.id)}" aria-pressed="${isSaved}" aria-label="${isSaved?'Quitar de':'Añadir a'} guardados: ${esc(o.code)}">${isSaved?'♥':'♡'}</button>${safeURL(o.image)?`<img src="${esc(safeURL(o.image))}" alt="${esc(o.title)}" loading="lazy" referrerpolicy="no-referrer">`:`<div class="card-art" aria-hidden="true"><div class="bag">${o.category_id==='delivery'?'↗':o.category_id==='pickup'?'✓':o.category_id==='photo'?'▧':'%'}</div><div class="art-coin">$</div></div>`}</div><div class="card-body"><div class="merchant">${esc(o.store)}</div><h3>${esc(o.discount)} <small>${o.discount==='GRATIS'?'':'de descuento'}</small></h3><p class="offer-title">${esc(o.title)}</p><p class="offer-meta">${esc(meta)}</p><button class="code-button" data-copy="${esc(o.code)}" aria-label="Copiar código ${esc(o.code)}"><strong>${esc(o.code)}</strong><span>Copiar ⧉</span></button><div class="card-bottom"><span class="pr-label">Confirmar en PR</span><button class="details-button" data-details="${esc(o.id)}">Detalles ↗</button></div></div></article>`;
 }).join('');
 document.querySelectorAll('.card-visual img').forEach(img=>img.addEventListener('error',()=>{const fallback=document.createElement('span');fallback.textContent='Fotografía';img.replaceWith(fallback);},{once:true}));
 $('empty').hidden=list.length>0;
 $('empty-message').textContent=state.savedOnly?'Toca el corazón de un código para tenerlo a mano.':state.offers.length?'Prueba otra búsqueda o categoría.':'No hay códigos vigentes verificados recientemente. Vuelve a actualizar o consulta las fuentes oficiales.';
 $('browse').classList.toggle('active',!state.savedOnly);$('saved').classList.toggle('active',state.savedOnly);
 $('browse').setAttribute('aria-current',state.savedOnly?'false':'page');$('saved').setAttribute('aria-current',state.savedOnly?'page':'false');
}
async function load(){
 $('refresh').disabled=true;
 try{
  const r=await fetch(`./offers.json?t=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw Error('http');const data=await r.json();if(!Array.isArray(data.offers))throw Error('format');
  state.data=data;render();
  const good=data.sources?.filter(s=>s.status==='ok').map(s=>s.checked_at).filter(Boolean)||[];
  const checked=good.length?good.sort()[0]:data.offers.map(o=>o.checked_at).filter(Boolean).sort()[0];
  $('update-text').textContent=checked?`Fuentes revisadas el ${date(checked)} · Revisión diaria`:'Revisión diaria · Sin datos recientes';
  const stale=checked&&Date.now()-Date.parse(checked)>48*3600000;
  $('source-alert').hidden=data.source_status==='ok'&&!stale;
  $('source-alert').textContent=stale?'La última revisión tiene más de 48 horas. Los códigos sin revisión reciente se han ocultado.':'Una fuente no respondió. Conservamos únicamente códigos recientes que todavía no han vencido; revisa sus condiciones oficiales.';
  if(!navigator.onLine){$('source-alert').hidden=false;$('source-alert').textContent='Sin conexión. Estás viendo la última copia disponible. Necesitas internet para comprobar un código en Walgreens.';}
 }catch{
  if(state.data)render();else{$('offers').innerHTML='';$('offers').setAttribute('aria-busy','false');$('empty').hidden=false;$('empty-message').textContent='No se pudo cargar el catálogo. Usa el botón ↻ para intentar de nuevo.';}
  $('source-alert').hidden=false;$('source-alert').textContent='No se pudo descargar el catálogo. Revisa tu conexión e intenta actualizar.';$('update-text').textContent='Catálogo sin actualizar';
 }finally{$('refresh').disabled=false;}
}
function details(id){const o=state.offers.find(o=>o.id===id);if(!o)return;show(`<span class="eyebrow dark">${esc(o.store)} · ${esc(o.category)}</span><h2>${esc(o.discount)} · ${esc(o.title)}</h2><button class="code-button" data-copy="${esc(o.code)}"><strong>${esc(o.code)}</strong><span>Copiar código ⧉</span></button><p><strong>Vence:</strong> ${esc(new Intl.DateTimeFormat('es-PR',{dateStyle:'medium',timeStyle:'short',timeZone:'America/Puerto_Rico'}).format(new Date(o.expires_at)))} (hora de Puerto Rico).</p><ul>${o.conditions.map(c=>`<li>${esc(c)}</li>`).join('')}</ul><p><strong>Puerto Rico:</strong> ${esc(o.pr_note)}</p><p>Condiciones originales: ${esc(o.official_title)}</p><p>Revisado: ${esc(date(o.checked_at))}. La revisión confirma la publicación en la fuente; no una prueba de canje.</p><a href="${esc(safeURL(o.source))}" target="_blank" rel="noopener noreferrer">Ver condiciones oficiales en Walgreens ↗</a>`);}
function how(){show('<h2>Un código. Unos pesitos menos.</h2><ol><li><strong>Busca el descuento.</strong> Revisa la compra mínima, los artículos elegibles y el vencimiento.</li><li><strong>Copia el código.</strong> Usa el botón de la tarjeta.</li><li><strong>Abre Walgreens.</strong> El enlace de detalles lleva a la fuente oficial. Selecciona tu tienda o dirección de Puerto Rico.</li><li><strong>Pégalo antes de pagar.</strong> Confirma que el descuento aparezca en el total. Su aceptación depende de tu carrito y de las condiciones.</li></ol><p>Guardar un código aquí solo lo añade a tus favoritos en este dispositivo. Peseteando no activa cupones ni realiza compras.</p>');}
function sources(){show(`<h2>Fuentes y actualización</h2><p>Consultamos páginas públicas de Walgreens cada día, aproximadamente a las <strong>6:17 a. m. de Puerto Rico</strong>. GitHub puede retrasar las ejecuciones.</p>${(state.data?.sources||[]).map(s=>`<div class="source-entry"><a href="${esc(safeURL(s.url))}" target="_blank" rel="noopener noreferrer">${s.id==='photo'?'Walgreens Photo':'Promociones de Walgreens'} ↗</a><p>${s.status==='ok'?`Lectura correcta · ${s.count} códigos · ${date(s.checked_at)}`:'Última lectura fallida; se requiere revisión.'}</p></div>`).join('')}<p>Solo publicamos códigos con descuento y vencimiento explícitos. Excluimos los que indican que no aplican en PR y ocultamos los vencidos o sin revisión reciente. No hemos probado su aceptación en un carrito de Puerto Rico.</p><p>La búsqueda automática cubre estas dos páginas; puede no incluir todos los códigos existentes.</p><a href="https://github.com/Fravier3/Peseteando/actions" target="_blank" rel="noopener noreferrer">Ver ejecuciones de actualización ↗</a>`);}
$('search').addEventListener('input',e=>{state.query=e.target.value;render();});
$('sort').addEventListener('change',e=>{state.sort=e.target.value;render();});
$('categories').addEventListener('click',e=>{const b=e.target.closest('[data-category]');if(!b)return;state.category=b.dataset.category;document.querySelectorAll('[data-category]').forEach(x=>{x.classList.toggle('selected',x===b);x.setAttribute('aria-pressed',String(x===b));});render();});
document.addEventListener('click',e=>{const copyBtn=e.target.closest('[data-copy]'),saveBtn=e.target.closest('[data-save]'),detailBtn=e.target.closest('[data-details]');if(copyBtn)copy(copyBtn.dataset.copy);if(saveBtn)toggleSaved(saveBtn.dataset.save);if(detailBtn)details(detailBtn.dataset.details);});
$('refresh').onclick=()=>{load();if('serviceWorker'in navigator)navigator.serviceWorker.getRegistration().then(r=>r?.update());};
$('browse').onclick=()=>{state.savedOnly=false;render();};$('saved').onclick=()=>{state.savedOnly=true;render();};
$('reset').onclick=()=>{state.savedOnly=false;state.query='';state.category='all';$('search').value='';document.querySelectorAll('[data-category]').forEach(b=>{const selected=b.dataset.category==='all';b.classList.toggle('selected',selected);b.setAttribute('aria-pressed',String(selected));});render();};
$('how').onclick=how;$('help').onclick=how;$('sources').onclick=sources;
$('close-dialog').onclick=()=>$('dialog').close();$('dialog').addEventListener('click',e=>{if(e.target===$('dialog')){const r=$('dialog').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('dialog').close();}});
let installPrompt;window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e;});
$('install').onclick=async()=>{if(installPrompt){await installPrompt.prompt();installPrompt=null;}else show('<h2>Lleva tus códigos contigo</h2><p><strong>iPhone:</strong> abre esta página en Safari, toca Compartir y elige Añadir a pantalla de inicio. Si aparece, activa Abrir como app web.</p><p><strong>Android:</strong> abre el menú de Chrome y elige Instalar aplicación o Añadir a pantalla de inicio.</p><p>Los favoritos se guardan en este dispositivo. Para recibir cambios, vuelve a abrir la app con conexión a internet.</p>');};
$('offers').innerHTML=Array(3).fill('<div class="loading-card" aria-hidden="true"></div>').join('');load();
setInterval(()=>{if(state.data)render();},60_000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden){load();if('serviceWorker'in navigator)navigator.serviceWorker.getRegistration().then(r=>r?.update());}});
if('serviceWorker'in navigator){let refreshing=false;navigator.serviceWorker.addEventListener('controllerchange',()=>{if(!refreshing&&navigator.serviceWorker.controller){refreshing=true;location.reload();}});navigator.serviceWorker.register('./sw.js').then(r=>r.update()).catch(()=>{});}

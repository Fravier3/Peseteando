import {test} from 'node:test';
import assert from 'node:assert/strict';
import {activeOffers,filteredOffers,usageLabels,normalizeStoreNumber,excludedAtStore} from '../catalog.mjs';
const now=Date.parse('2026-10-21T16:00:00Z');
const item={id:'a',kind:'weekly_ad',code:null,title:'Fotografía',official_title:'Photo',store:'Walgreens',category:'Foto',channels:['store'],pr_status:'official_pr',percent:20,checked_at:'2026-10-21T10:00:00Z',expires_at:'2026-10-25T04:59:59Z'};
const online={...item,id:'b',kind:'promo_code',code:'OCT20',pr_status:'unverified',channels:['online']};
test('reject expired, stale, future-start and malformed codes; allow offers without codes',()=>assert.equal(activeOffers([item,online,{...item,expires_at:'2026-10-21T15:00:00Z'},{...item,checked_at:'2026-10-18T10:00:00Z'},{...item,starts_at:'2026-10-22T10:00:00Z'},{...item,code:'<img>'}],now).length,2));
test('unverified codes never leak into primary, store or activate filters',()=>{
 assert.deepEqual(filteredOffers([item,online]).map(o=>o.id),['a']);
 assert.equal(filteredOffers([item,online],{mode:'online'}).length,0);
 assert.equal(filteredOffers([item,online],{mode:'online',verification:'unverified'}).length,1);
 assert.equal(filteredOffers([item,online],{mode:'store',verification:'unverified'}).length,0);
});
test('search accents, presentations and codes; preserve saved identities',()=>{
 assert.equal(filteredOffers([item],{query:'fotografia'}).length,1);
 assert.equal(filteredOffers([online],{query:'oct20',verification:'unverified'}).length,1);
 assert.equal(filteredOffers([item],{savedOnly:true,saved:[]}).length,0);
 assert.equal(filteredOffers([item],{savedOnly:true,saved:['a']}).length,1);
 assert.equal(filteredOffers([item],{category:'Compra online'}).length,0);
});
test('activation and pickup are separate; photo kiosk is not general checkout',()=>{
 const photo={...online,channels:['online','photo_kiosk']};
 assert.ok(!usageLabels(photo).includes('Usar en tienda'));
 assert.deepEqual(usageLabels({...item,requires_activation:true}),['Usar en tienda','Activar cupón']);
 assert.equal(filteredOffers([item,{...item,id:'c',requires_activation:true}],{mode:'activate'}).length,1);
});
test('store exclusions match full numbers, normalize zeroes and preserve other retailers and online offers',()=>{
 const regional={...item,retailer_id:'walgreens',excluded_stores:['156','217','16409']};
 assert.equal(normalizeStoreNumber('00156'),'156');
 for(const invalid of ['0','123456','-156','156x','<img>',null])assert.equal(normalizeStoreNumber(invalid),'');
 assert.equal(excludedAtStore(regional,'00156'),true);
 assert.equal(excludedAtStore(regional,'56'),false);
 assert.equal(excludedAtStore({...regional,retailer_id:'walmart'},'156'),false);
 assert.equal(excludedAtStore({...regional,channels:['online']},'156'),false);
 assert.equal(filteredOffers([regional],{storeNumber:'156'}).length,0);
 assert.equal(filteredOffers([regional],{storeNumber:'677'}).length,1);
 assert.equal(filteredOffers([regional],{storeNumber:''}).length,1);
});
test('branch filter applies to saved offers without mutating favorites and keeps unknown restrictions visible',()=>{
 const excluded={...item,retailer_id:'walgreens',excluded_stores:['156']};
 const unknown={...excluded,id:'c',excluded_stores:undefined};
 const saved=['a','c'];
 assert.deepEqual(filteredOffers([excluded,unknown],{storeNumber:'156',savedOnly:true,saved}).map(o=>o.id),['c']);
 assert.deepEqual(saved,['a','c']);
 assert.equal(filteredOffers([excluded,unknown],{storeNumber:'',savedOnly:true,saved}).length,2);
});

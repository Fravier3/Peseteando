import {test} from 'node:test';
import assert from 'node:assert/strict';
import {activeOffers,filteredOffers} from '../catalog.mjs';
const now=Date.parse('2026-10-21T16:00:00Z');
const item={id:'a',code:'OCT20',title:'Fotografía',official_title:'Photo',store:'Walgreens',category:'Foto',category_id:'photo',percent:20,checked_at:'2026-10-21T10:00:00Z',expires_at:'2026-10-25T04:59:59Z'};
test('reject expired, stale and malformed codes',()=>assert.equal(activeOffers([item,{...item,expires_at:'2026-10-21T15:00:00Z'},{...item,checked_at:'2026-10-18T10:00:00Z'},{...item,code:'<img>'}],now).length,1));
test('search accents and codes, category and saved filters',()=>{
 assert.equal(filteredOffers([item],{query:'fotografia'}).length,1);
 assert.equal(filteredOffers([item],{query:'oct20'}).length,1);
 assert.equal(filteredOffers([item],{savedOnly:true,saved:[]}).length,0);
 assert.equal(filteredOffers([item],{savedOnly:true,saved:['a']}).length,1);
 assert.equal(filteredOffers([item],{category:'general'}).length,0);
});

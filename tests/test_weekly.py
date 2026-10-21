import unittest
from datetime import datetime,timezone
from scripts.weekly import parse_weekly,pricing
from scripts.refresh import parse_coupons
import json

NOW=datetime(2026,10,21,tzinfo=timezone.utc)
CIRC={'marketVersion':'PR','isPublished':True,'catalogId':'pr-1','startDate':'2026-10-18T00:00:00','endDate':'2026-10-24T00:00:00'}
TERMS='La membresía myWalgreens es requerida en la tienda. Este shopper no es válido en las siguientes tiendas: #156; #217. Ver detalles en el cupón.'
def offer():return {'offerVersionGroupId':15,'uniqueId':'a','pricingHeader':'Detergente, 32 oz.','pricingBody':'Artículos selectos.','pricingTemplateName':'PR Price STD_PR RR on X','imageUrl':'https://example.com/product.png','startDate':CIRC['startDate'],'endDate':CIRC['endDate'],'dataColumns':{'AdRetail':'3.99','myWalgreens':'con myWalgreens','RegisterReward':'5','LTYRewardQuantity':'4'},'offerType':'product'}
def collection(o=None):return {'catalogId':'pr-1','collectionId':'a','name':'Hogar','offers':[o or offer()]}
def coupons(state='PR',source='Walgreens IVC'):
 c={'id':'coupon-1','source':source,'redemptionType':'POS','type':'AmountOff','brandName':'Scott','description':'Scott 12 rollos','code':'THIS_IS_NOT_A_PROMO_CODE','expiryDate':'10/24/26','activeDateAsUTC':1788066000000,'offerValue':1.25,'minQty':1,'image':'https://example.com/scott.png'}
 s={'StoreLocator':{'isPrStore':state=='PR','storeAddressData':{'address':{'state':state},'storeNumber':'677'}},'CouponCard':{'recommendData':{'coupons':[c]}}}
 return '<script>window.__APP_INITIAL_STATE__ = '+json.dumps(s)+';</script>'
class RegionalTests(unittest.TestCase):
 def test_pr_required_not_continental(self):
  with self.assertRaises(ValueError):parse_weekly({**CIRC,'marketVersion':'US'},[collection()],TERMS,NOW)
  with self.assertRaises(ValueError):parse_weekly(CIRC,[{**collection(),'catalogId':'us'}],TERMS,NOW)
 def test_expiry_and_future_circular(self):
  with self.assertRaises(ValueError):parse_weekly(CIRC,[collection()],TERMS,datetime(2026,10,25,4,tzinfo=timezone.utc))
  with self.assertRaises(ValueError):parse_weekly(CIRC,[collection()],TERMS,datetime(2026,10,17,tzinfo=timezone.utc))
 def test_regional_price_not_reduced_by_reward(self):
  o=parse_weekly(CIRC,[collection()],TERMS,NOW)[0]
  self.assertEqual(o['price'],3.99);self.assertIn('$5',o['reward']);self.assertIsNone(o['code'])
  self.assertEqual(o['pr_status'],'official_pr');self.assertFalse(o['redemption_tested']);self.assertEqual(o['stock_status'],'not_checked')
  self.assertEqual(o['excluded_stores'],['156','217']);self.assertEqual(o['expires_at'],'2026-10-25T03:59:59+00:00')
 def test_duplicate_offers_and_teasers(self):
  self.assertEqual(len(parse_weekly(CIRC,[collection(),collection()],TERMS,NOW)),1)
  self.assertEqual(parse_weekly(CIRC,[collection({**offer(),'offerType':'teaser'})],TERMS,NOW),[])
 def test_bogo_percentage_not_full_cart_percentage(self):
  o={**offer(),'pricingTemplateName':'PR BOGO PercentOff','dataColumns':{'Quantity':'1','GetFree':'1','BOGOPercentOff':'50'}}
  price,amount,_=pricing(o);self.assertEqual(price,'Compra 1 + 1 con 50% dto.');self.assertIsNone(amount)
 def test_coupon_ids_not_codes_and_scope_required(self):
  o=parse_coupons(coupons(),NOW)[0];self.assertIsNone(o['code']);self.assertEqual(o['pr_status'],'official_pr');self.assertTrue(o['requires_activation'])
  self.assertEqual(parse_coupons(coupons(state='FL'),NOW)[0]['pr_status'],'unverified')
  self.assertEqual(parse_coupons(coupons(source="Manufacturer's Coupon"),NOW),[])
 def test_missing_terms_fail_closed(self):
  with self.assertRaises(ValueError):parse_weekly(CIRC,[collection()],'Generic conditions',NOW)
if __name__=='__main__':unittest.main()

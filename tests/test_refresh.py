import unittest
from datetime import datetime, timezone
from scripts.refresh import parse, expiry, PR_EXCLUSION

NOW=datetime(2026,10,21,tzinfo=timezone.utc)
def sample(title='20% OFF $50+ eligible items with code OCT20', terms=''):
    return '<html><h3>'+title+'</h3><p>Offer available only on Walgreens.com. '+terms+' Orders must be placed by 11:59 p.m. Central Time on October 31, 2026 to qualify.</p></html>'
class ParserTests(unittest.TestCase):
    def test_codes_and_amount_not_confused(self):
        o=parse('walgreens',sample(),NOW)[0]
        self.assertEqual((o['code'],o['discount'],o['minimum']),('OCT20','20%',50))
        self.assertEqual(o['pr_status'],'pending_checkout')
        self.assertEqual(o['expires_at'],'2026-11-01T04:59:59+00:00')
    def test_excludes_pr_not_every_us_offer_is_local(self):
        self.assertEqual(parse('walgreens',sample(terms='Not available in PR.'),NOW),[])
        self.assertTrue(PR_EXCLUSION.search('Offer excludes Puerto Rico.'))
    def test_expired_never_rolls_forward(self):
        self.assertEqual(parse('walgreens',sample().replace('2026','2025'),NOW),[])
    def test_no_code_no_explicit_year_no_offer(self):
        self.assertEqual(parse('walgreens',sample(title='Earn rewards'),NOW),[])
        self.assertEqual(parse('walgreens',sample().replace(', 2026',''),NOW),[])
    def test_december_and_dst(self):
        self.assertEqual(expiry('11:59 p.m. Central Time on December 31st, 2026').isoformat(),'2026-12-31T23:59:59-06:00')
    def test_duplicate_and_photos(self):
        self.assertEqual(len(parse('walgreens',sample()+sample(),NOW)),1)
        page='<h5>50% OFF Everything Photo</h5><p>Must use code PHOTO50 to receive a discount. Offer expires at 11:59 p.m. CT on October 24, 2026.</p>'
        self.assertEqual(parse('photo',page,NOW)[0]['code'],'PHOTO50')
    def test_lazy_image_uses_original_not_placeholder(self):
        page='<div class="tile-l3-v1"><img src="data:image/gif;base64,AA" data-pagespeed-lazy-src="https://example.com/photo.jpg"><p>Coupon code: PHOTO50</p></div><h5>50% OFF Everything Photo</h5><p>Must use code PHOTO50 to receive a discount. Offer expires at 11:59 p.m. CT on October 24, 2026.</p>'
        self.assertEqual(parse('photo',page,NOW)[0]['image'],'https://example.com/photo.jpg')
if __name__=='__main__':unittest.main()

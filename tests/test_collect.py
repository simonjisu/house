import unittest
from scripts.collect import parse_lh, parse_sh, merge

class SafetyTests(unittest.TestCase):
    def test_sh_stable_original_identifier(self):
        # Deliberately minimal synthetic parser input; never included in web data.
        row='<tbody><tr>'+''.join('<td>'+x+'</td>' for x in ['1','type','title','date','result','status','department','<a href="https://www.i-sh.co.kr/view.do?seq=123">link</a>'])+'</tr></tbody>'
        self.assertEqual(parse_sh(row)[0]['id'],'SH:123')
    def test_lh_identifiers_and_no_badge(self):
        html='<tr><td>1</td><td>행복주택</td><td><a class="wrtancInfoBtn" data-id1="123" data-id2="03" data-id3="06" data-id4="10">신혼 공고<em>1일전</em></a></td><td>경기도</td><td></td><td>2026.10.01</td><td>2026.10.14</td><td>공고중</td></tr>'
        n=parse_lh(html)[0]
        self.assertNotIn('1일전',n['title']); self.assertEqual(n['income'],None)
        self.assertIn('panId=123',n['url']); self.assertEqual(n['eligibility'],'unknown')
    def test_failure_preserves_successful_records(self):
        old=dict(id='SH:1',source='SH',published='date',hash='old',checkedAt='date',status='모집중',title='x')
        self.assertEqual(merge([old],[],[]),[old])
    def test_missing_not_cancelled_and_change_history(self):
        old=dict(id='SH:1',source='SH',published='date',hash='old',checkedAt='date',status='모집중',title='x')
        missing=merge([old],[],['SH'])[0]
        self.assertTrue(missing['missingFromLatest']); self.assertEqual(missing['status'],'모집중')
        new={**old,'hash':'new','title':'정정'}
        self.assertEqual(len(merge([old],[new],['SH'])[0]['changes']),1)
if __name__=='__main__': unittest.main()

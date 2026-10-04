import os,unittest
from unittest.mock import patch
from scripts.applyhome import parse_notice,api,collect_applyhome
from scripts.collect import notice,merge,collect_lh
class ApplyhomeTests(unittest.TestCase):
 def sample(self,**kwargs):
  return dict(HOUSE_MANAGE_NO='synthetic-house',PBLANC_NO='synthetic-notice',HOUSE_NM='합성 공공분양',RENT_SECD='0',HOUSE_SECD='01',SUBSCRPT_AREA_CODE_NM='경기',PBLANC_URL='https://www.applyhome.co.kr/',RCRIT_PBLANC_DE='2026-10-01',RCEPT_ENDDE='2026-10-20',SPSPLY_RCEPT_ENDDE='2026-10-10',PUBLIC_HOUSE_SPCLW_APPLC_AT='Y',**kwargs)
 def test_null_zero_and_independent_windows(self):
  n=parse_notice(self.sample(GNRL_RNK1_CRSPAREA_ENDDE='2026-10-14'),[dict(NWWDS_HSHLDCO=2,NWBB_HSHLDCO=0,SPSPLY_HSHLDCO=None)],notice)
  self.assertEqual(n['deadline'],'2026-10-20');self.assertEqual(n['applicationWindows']['SPSPLY_RCEPT_ENDDE'],'2026-10-10')
  self.assertEqual(n['applicationWindows']['GNRL_RNK1_CRSPAREA_ENDDE'],'2026-10-14');self.assertIsNone(n['applicationWindows']['GNRL_RNK2_ETC_GG_ENDDE'])
  self.assertEqual(n['housingModels'][0]['NWBB_HSHLDCO'],0);self.assertIsNone(n['housingModels'][0]['SPSPLY_HSHLDCO'])
  self.assertEqual(n['specialTracks'],['신혼부부 특별공급']);self.assertIsNone(n['income']);self.assertEqual(n['eligibility'],'unknown')
 def test_newborn_public_only_and_rental_distinct(self):
  row=self.sample();row.update(PUBLIC_HOUSE_SPCLW_APPLC_AT='N',RENT_SECD='1')
  n=parse_notice(row,[dict(NWBB_HSHLDCO=8)],notice);self.assertEqual(n['specialTracks'],[]);self.assertEqual(n['housingKind'],'rental')
 def test_missing_credential_no_request(self):
  with patch.dict(os.environ,{},clear=True),patch('scripts.applyhome.build_opener') as opener:
   with self.assertRaises(ValueError):api('getAPTLttotPblancDetail',{})
   opener.assert_not_called()
 def test_key_encoded_once_not_header_or_payload(self):
  from contextlib import nullcontext
  import io,json
  from urllib.parse import parse_qs,urlparse
  with patch.dict(os.environ,{'DATA_GO_KR_SERVICE_KEY':'synthetic+a/b=='}),patch('scripts.applyhome.build_opener') as opener:
   response=io.StringIO(json.dumps({'data':[],'matchCount':0}));response.url='https://api.odcloud.kr/api/'
   opener.return_value.open.return_value=nullcontext(response)
   api('getAPTLttotPblancDetail',{'page':1})
   req=opener.return_value.open.call_args[0][0]
   self.assertEqual(parse_qs(urlparse(req.full_url).query)['serviceKey'],['synthetic+a/b=='])
   self.assertNotIn('Authorization',req.headers)
 def test_feed_failure_preserves_sale_records(self):
  old=notice('LH','synthetic','합성 분양','분양주택','서울','2026-10-01','공고중','https://apply.lh.or.kr/')
  old['feed']='LH분양';self.assertFalse(merge([old],[],['LH'])[0]['missingFromLatest'])
  self.assertTrue(merge([old],[],['LH분양'])[0]['missingFromLatest'])
 def test_unconnected_main_preserves_previous_data(self):
  from tempfile import TemporaryDirectory
  from pathlib import Path
  from scripts import collect
  import json
  with TemporaryDirectory() as root,patch.object(collect,'DATA',Path(root)/'notices.json'),patch.dict(os.environ,{},clear=True),patch.object(collect,'collect_lh',return_value=([],{})),patch.object(collect,'collect_sh',return_value=([],{})):
   self.assertEqual(collect.main(),0)
   payload=json.loads((Path(root)/'notices.json').read_text())
   self.assertEqual(payload['sources']['청약홈']['state'],'unconnected')
   self.assertFalse(payload['sources']['청약홈']['ok'])
if __name__=='__main__':unittest.main()

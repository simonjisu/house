"""Optional official API adapter. Credential is normalized, decoded at most once and URL-encoded once, never included in payload/logs."""
import hashlib,json,os,re
from datetime import datetime,timedelta,timezone
from urllib.parse import urlencode,urlparse,unquote
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError
BASE='https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/'
WINDOW_FIELDS=['RCEPT_BGNDE','RCEPT_ENDDE','SPSPLY_RCEPT_BGNDE','SPSPLY_RCEPT_ENDDE']+[
 f'GNRL_RNK{rank}_{region}_{edge}' for rank in (1,2) for region in ('CRSPAREA','ETC_GG','ETC_AREA') for edge in ('RCPTDE','ENDDE')]
CODE_FIELDS=['HOUSE_SECD','HOUSE_DTL_SECD','RENT_SECD','PUBLIC_HOUSE_SPCLW_APPLC_AT']
MODEL_FIELDS=['MODEL_NO','HOUSE_TY','SUPLY_AR','NWWDS_HSHLDCO','NWBB_HSHLDCO','SPSPLY_HSHLDCO','LTTOT_TOP_AMOUNT']
class ApplyhomeError(ValueError):
 def __init__(self,code):
  self.safe_code=code
  super().__init__(code)

def normalize_key(raw):
 # API tokens have no whitespace. Accept pasted line wrapping and either portal representation.
 key=''.join(raw.split())
 if re.search(r'%[0-9A-Fa-f]{2}',key):key=unquote(key)
 if re.search(r'%[0-9A-Fa-f]{2}',key):raise ApplyhomeError('DOUBLE_ENCODED_KEY_INPUT')
 if not key:raise ApplyhomeError('MISSING_KEY_INPUT')
 return key

def api(endpoint,params):
 if endpoint not in ('getAPTLttotPblancDetail','getAPTLttotPblancMdl'):raise ValueError('Unsupported endpoint')
 key=normalize_key(os.environ.get('DATA_GO_KR_SERVICE_KEY',''))
 request=Request(BASE+endpoint+'?'+urlencode({**params,'serviceKey':key}),headers={'Accept':'application/json'})
 class NoRedirect(HTTPRedirectHandler):
  def redirect_request(self,*args,**kwargs):raise ValueError('API redirect prohibited')
 try:
  with build_opener(NoRedirect()).open(request,timeout=40) as response:
   if urlparse(response.url).hostname!='api.odcloud.kr':raise ApplyhomeError('UNEXPECTED_REDIRECT')
   value=json.load(response)
 except HTTPError as error:
  # Never log exception text, request URL, body or key. Numeric HTTP status only.
  error.close()
  raise ApplyhomeError('HTTP_'+str(error.code)+'_'+endpoint) from None
 if not isinstance(value.get('data'),list) or not isinstance(value.get('matchCount'),int):raise ApplyhomeError('API_SCHEMA_CHANGED_'+endpoint)
 return value

def parse_notice(row,models,make_notice):
 ident=[str(row.get(k) or '') for k in ('HOUSE_MANAGE_NO','PBLANC_NO')]
 if not all(ident):raise ValueError('Missing identity')
 url=row.get('PBLANC_URL') or ''
 if urlparse(url).scheme!='https' or urlparse(url).hostname not in ('www.applyhome.co.kr','applyhome.co.kr'):raise ValueError('Unexpected original URL')
 kind='분양' if str(row.get('RENT_SECD'))=='0' else '분양전환 임대' if str(row.get('RENT_SECD'))=='1' else '분류 확인 필요'
 n=make_notice('청약홈',':'.join(ident),row.get('HOUSE_NM') or '공고명 미확인',kind,row.get('SUBSCRPT_AREA_CODE_NM') or '지역 미확인',row.get('RCRIT_PBLANC_DE'),
 '접수기간 원문 확인',url,row.get('RCEPT_ENDDE'))
 n.update(housingKind='sale' if kind=='분양' else 'rental' if kind=='분양전환 임대' else 'unknown',
  officialCodes={k:row.get(k) for k in CODE_FIELDS},applicationWindows={k:row.get(k) for k in WINDOW_FIELDS},
  housingModels=[{k:m.get(k) for k in MODEL_FIELDS} for m in models],address=row.get('HSSPLY_ADRES'),
  deadlineMeaning='청약홈 전체 접수 종료일 · 특별공급/지역별 일반공급 기간은 별도',
  evidence='청약홈 공식 API 메타데이터 · 특별공급 배정 수는 자격 확정 아님 · 원문/소득표 미검토')
 n['specialTracks']=[]
 def positive(value):
  try:return float(value)>0
  except (ValueError,TypeError):return False
 if any(positive(m.get('NWWDS_HSHLDCO')) for m in models):n['specialTracks'].append('신혼부부 특별공급')
 if row.get('PUBLIC_HOUSE_SPCLW_APPLC_AT')=='Y' and any(positive(m.get('NWBB_HSHLDCO')) for m in models):n['specialTracks'].append('신생아 특별공급 (공공)')
 n['hash']=hashlib.sha256(json.dumps({k:v for k,v in n.items() if k not in ('checkedAt','lastSeenAt','hash')},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
 return n

def collect_applyhome(make_notice):
 today=datetime.now(timezone(timedelta(hours=9))).date();rows=[];complete=False
 params={'perPage':100,'cond[RCRIT_PBLANC_DE::GTE]':(today-timedelta(days=60)).isoformat(),'cond[RCRIT_PBLANC_DE::LTE]':today.isoformat()}
 for page in range(1,6):
  value=api('getAPTLttotPblancDetail',{**params,'page':page});rows.extend(value['data'])
  if page*100>=value['matchCount']:complete=True;break
 notices=[];models_complete=True
 for row in rows:
  if not any(r in (row.get('SUBSCRPT_AREA_CODE_NM') or '') for r in ('서울','경기')):continue
  if str(row.get('HOUSE_SECD')) not in ('01','09','10'):continue
  models=[]
  for page in (1,2):
   value=api('getAPTLttotPblancMdl',{'page':page,'perPage':100,'cond[HOUSE_MANAGE_NO::EQ]':row['HOUSE_MANAGE_NO'],'cond[PBLANC_NO::EQ]':row['PBLANC_NO']});models.extend(value['data'])
   if page*100>=value['matchCount']:break
  else:models_complete=False
  notices.append(parse_notice(row,models,make_notice))
 return notices,dict(windowDays=60,pageCap=5,modelPageCap=2,completeWithinQuery=complete and models_complete,query='청약홈 APT01/민간사전09/신혼희망10 · 최근 60일 · 서울/경기 · 무순위/오피스텔 등 제외')

"""Two read-only auth probes on the documented endpoint. No credential/body/URL logging."""
import json,os,re,sys
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode
from urllib.request import Request,build_opener,HTTPRedirectHandler
if __package__:
 from .applyhome import BASE,normalize_key,ApplyhomeError
else:
 from applyhome import BASE,normalize_key,ApplyhomeError

class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise ValueError('Redirect prohibited')

def safe_error_body(raw):
 try:value=json.loads(raw)
 except (ValueError,UnicodeError):return {'category':'NON_JSON_ERROR'}
 if not isinstance(value,dict):return {'category':'UNKNOWN_ERROR'}
 code=value.get('code',value.get('errorCode'))
 if isinstance(code,int) and not isinstance(code,bool) and abs(code)<1000:out={'apiCode':code}
 elif isinstance(code,str) and code in ('SERVICE_KEY_IS_NULL','PERMISSION_DENIED','SERVICE_ACCESS_DENIED_ERROR','SERVICE_KEY_IS_NOT_REGISTERED_ERROR','DEADLINE_HAS_EXPIRED_ERROR'):out={'apiCode':code}
 else:out={}
 message=str(value.get('msg',value.get('message',''))).lower()
 # Return fixed labels only; never return server text, which could contain a credential.
 if '등록되지' in message or 'not registered' in message:out['category']='UNREGISTERED_KEY'
 elif '만료' in message or 'expired' in message:out['category']='EXPIRED_KEY'
 elif '권한' in message or 'permission' in message or 'access denied' in message:out['category']='ACCESS_DENIED'
 elif '인증' in message or 'authentication' in message or 'unauthorized' in message:out['category']='AUTHENTICATION_ERROR'
 else:out['category']='UNKNOWN_ERROR'
 return out

def probe(mode,key):
 params={'page':1,'perPage':1};headers={'Accept':'application/json'}
 if mode=='query':params['serviceKey']=key
 elif mode=='header':headers['Authorization']=key
 else:raise ValueError('Unknown auth scheme')
 req=Request(BASE+'getAPTLttotPblancDetail?'+urlencode(params),headers=headers,method='GET')
 try:
  with build_opener(NoRedirect()).open(req,timeout=30) as response:
   value=json.load(response)
   return {'http':response.status,'schemaValid':isinstance(value.get('data'),list) and isinstance(value.get('matchCount'),int)}
 except HTTPError as error:
  result={'http':error.code,**safe_error_body(error.read(4096))};error.close();return result
 except URLError:return {'category':'NETWORK_ERROR'}
 except Exception:return {'category':'UNEXPECTED_RESPONSE'}

def main():
 key=os.environ.get('DATA_GO_KR_SERVICE_KEY','')
 report={'configured':bool(key),'surroundingWhitespace':key!=key.strip(),'containsPercentEscapes':bool(re.search(r'%[0-9A-Fa-f]{2}',key)),'containsLineBreak':any(c in key for c in '\r\n'),'surroundingQuotes':len(key)>1 and key[0]==key[-1] and key[0] in "\"'"}
 if key:
  try:
   normalized=normalize_key(key)
   report['normalizationApplied']=key!=normalized
   report['query']=probe('query',normalized)
   report['header']=probe('header',normalized)
  except ApplyhomeError as error:report['normalizationError']=error.safe_code
 print('Applyhome auth diagnostics: '+json.dumps(report,sort_keys=True))
 return 0
if __name__=='__main__':sys.exit(main())

"""Safe aggregate source diagnostics and protected-DB round-trip verification. No keys/URLs/records printed."""
import json,sys
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.request import Request,urlopen
if __package__:
 from .sync_supabase import config,PATH
else:
 from sync_supabase import config,PATH

def valid_date(value):
 if value is None or value=='':return True
 try:return date.fromisoformat(value).isoformat()==value
 except (ValueError,TypeError):return False

def summary(payload):
 rows=payload['notices'];out={}
 for name,s in payload['sources'].items():
  matching=[n for n in rows if n.get('feed',n['source'])==name]
  out[name]={'ok':s.get('ok',False),'state':s.get('state'),'error':s.get('error'),'freshCount':s.get('count'),
   'retainedCount':len(matching),'latestPresentCount':sum(not n.get('missingFromLatest') for n in matching),'completeWithinQuery':s.get('scope',{}).get('completeWithinQuery')}
 apt=[n for n in rows if n['source']=='청약홈']
 models=[m for n in apt for m in n.get('housingModels',[])]
 report={'sources':out,'total':len(rows),'applyhome':{'regions':dict(Counter(n['region'] for n in apt)),
  'modelRows':len(models),'specialWindowRecords':sum(bool(n.get('applicationWindows',{}).get('SPSPLY_RCEPT_ENDDE')) for n in apt),
  'newlywedTrackRecords':sum('신혼부부 특별공급' in n.get('specialTracks',[]) for n in apt),
  'publicNewbornTrackRecords':sum('신생아 특별공급 (공공)' in n.get('specialTracks',[]) for n in apt),
  'invalidDates':sum(not valid_date(v) for n in apt for v in [n.get('published'),n.get('deadline'),*n.get('applicationWindows',{}).values()]),
  'overallDeadlineMatches':sum(n.get('deadline')==n.get('applicationWindows',{}).get('RCEPT_ENDDE') for n in apt),
  'separateSpecialDeadlineRecords':sum(bool(n.get('applicationWindows',{}).get('SPSPLY_RCEPT_ENDDE')) and n['deadline']!=n['applicationWindows']['SPSPLY_RCEPT_ENDDE'] for n in apt),
  'counts':{field:{'null':sum(m.get(field) is None for m in models),'zero':sum(m.get(field) in (0,'0') for m in models),'positive':sum(positive(m.get(field)) for m in models)} for field in ('NWWDS_HSHLDCO','NWBB_HSHLDCO','SPSPLY_HSHLDCO')},
  'allIncomeUnknown':all(n.get('eligibility')=='unknown' and n.get('income') is None for n in rows)}}
 return report

def positive(value):
 try:return float(value)>0
 except (ValueError,TypeError):return False

def main():
 expected=json.loads(PATH.read_text());url,headers=config()
 with urlopen(Request(url+'/rest/v1/house_snapshot?id=eq.current&select=payload',headers=headers),timeout=30) as response:rows=json.load(response)
 if len(rows)!=1 or rows[0]['payload']!=expected:raise ValueError('Protected DB round-trip mismatch')
 report=summary(rows[0]['payload'])
 print('Source verification: '+json.dumps(report,ensure_ascii=False,sort_keys=True))
 print('Protected DB round-trip verified')
 if report['applyhome']['invalidDates']:raise ValueError('Invalid application date')
if __name__=='__main__':
 try:main()
 except Exception as error:
  print('Snapshot verification failed: '+type(error).__name__,file=sys.stderr);sys.exit(1)

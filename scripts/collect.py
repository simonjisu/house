"""Public metadata only. Never fetch SH originals, attachments or login URLs."""
import hashlib, json, os, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'runtime/notices.json'
UA = 'HouseNoticeCollector/1.0 (+https://github.com/simonjisu/house)'
LH = 'https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do'
SH = 'https://housing.seoul.go.kr/site/main/sh/publicLease/list'
NOW = lambda: datetime.now(timezone.utc).isoformat()

def request(url, fields=None):
    if urlparse(url).hostname not in {'apply.lh.or.kr', 'housing.seoul.go.kr'}:
        raise ValueError('Host not allowed')
    if any(x in url for x in ('lhFile.do', '/login/', 'NetFunnel')):
        raise ValueError('Forbidden path')
    req = Request(url, data=urlencode(fields).encode() if fields is not None else None,
                  headers={'User-Agent': UA})
    with urlopen(req, timeout=40) as response:
        if urlparse(response.url).hostname != urlparse(url).hostname:
            raise ValueError('Unexpected redirect')
        return response.read().decode('utf-8', errors='replace')

def check_robots(url):
    origin = 'https://' + urlparse(url).hostname
    raw = request(origin + '/robots.txt').replace('\\r\\n', '\n')
    if not raw.strip() or '<html' in raw.lower():
        raise ValueError('Robots unavailable')
    parser = RobotFileParser(); parser.parse(raw.splitlines())
    if not parser.can_fetch(UA, url):
        raise ValueError('Robots denied')

def text(node):
    return ' '.join(node.stripped_strings)

def notice(source, ident, title, kind, region, published, status, url, deadline=None):
    value = dict(id=source+':'+ident, source=source, title=title, type=kind,
                 region=region, published=published, status=status, url=url,
                 deadline=deadline, deadlineMeaning='목록 마감일 (접수시각 미확인)' if deadline else None,
                 audience=[x for x in ('신혼', '신생아') if x in title],
                 eligibility='unknown', income=None,
                 evidence='공식 목록 메타데이터 · 첨부/소득표 미검토',
                 checkedAt=NOW(), lastSeenAt=NOW(), missingFromLatest=False)
    content = {k:v for k,v in value.items() if k not in ('checkedAt','lastSeenAt')}
    value['hash'] = hashlib.sha256(json.dumps(content,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return value

def parse_lh(html):
    soup = BeautifulSoup(html, 'html.parser'); result=[]
    for link in soup.select('a.wrtancInfoBtn'):
        cells=link.find_parent('tr').find_all('td', recursive=False)
        if len(cells)<8: raise ValueError('LH table changed')
        title=BeautifulSoup(str(link),'html.parser')
        for badge in title.select('em'): badge.decompose()
        query=dict(zip(('panId','ccrCnntSysDsCd','uppAisTpCd','aisTpCd'),[link.get('data-id'+str(i)) for i in range(1,5)]))
        if not all(query.values()): raise ValueError('LH identifiers missing')
        result.append(notice('LH', ':'.join(query.values()), text(title),text(cells[1]),text(cells[3]),
            text(cells[5]),text(cells[7]),'https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancInfo.do?'+urlencode(query),text(cells[6])))
    return result

def parse_sh(html):
    soup=BeautifulSoup(html,'html.parser'); result=[]
    for row in soup.select('tbody tr'):
        link=row.select_one('a[href*="i-sh.co.kr"][href*="seq="]')
        if not link: continue
        cells=row.find_all('td',recursive=False)
        if len(cells)<8: raise ValueError('SH table changed')
        ident=parse_qs(urlparse(link['href']).query).get('seq',[None])[0]
        if not ident: raise ValueError('SH identifier missing')
        n=notice('SH',ident,text(cells[2]),text(cells[1]),'서울특별시',text(cells[3]),text(cells[5]),link['href'])
        n['announcementDate']=text(cells[4])
        stable={k:v for k,v in n.items() if k not in ('checkedAt','lastSeenAt','hash')}
        n['hash']=hashlib.sha256(json.dumps(stable,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        result.append(n)
    return result

def collect_lh():
    check_robots(LH); initial=request(LH+'?mi=1026')
    soup=BeautifulSoup(initial,'html.parser')
    form=soup.select_one('input[name="currPage"]').find_parent('form')
    fields={}
    for node in form.select('input[name], select[name]'):
        if node.name=='select':
            option=node.select_one('option[selected]') or node.select_one('option')
            fields[node['name']]=option.get('value','') if option else ''
        else: fields[node['name']]=node.get('value','')
    today=datetime.now(timezone(timedelta(hours=9))).date()
    fields.update(panStDt=(today-timedelta(days=60)).strftime('%Y%m%d'),panEdDt=today.strftime('%Y%m%d'),startDt=(today-timedelta(days=60)).isoformat(),endDt=today.isoformat(),
                  panSs='',listCo='100',cnpCd='',srchY='N',uppAisTpCd='061339',srchUppAisTpCd='061339',prevListCo='100')
    rows=[]; fingerprints=set(); complete=False
    for page in range(1,6):
        fields.update(currPage=str(page),minSn=str((page-1)*100),maxSn=str(page*100))
        response=request(LH,fields); parsed=parse_lh(response)
        if not parsed:
            if page==1: raise ValueError('LH empty: requires review')
            complete=True; break
        fingerprint=tuple(n['id'] for n in parsed)
        if fingerprint in fingerprints: raise ValueError('LH pagination repeated')
        fingerprints.add(fingerprint); rows.extend(parsed)
        if len(parsed)<100: complete=True; break
        time.sleep(1)
    return [n for n in rows if any(r in n['region'] for r in ('서울','경기','전국'))],dict(windowDays=60,pageCap=5,completeWithinQuery=complete,query='임대/매입/전세임대 · 전국조회 후 서울/경기/전국 필터 · 모든 목록 상태')

def collect_sh():
    check_robots(SH); first=request(SH)
    soup=BeautifulSoup(first,'html.parser')
    pages=[int(parse_qs(urlparse(a['href']).query).get('cp',['1'])[0]) for a in soup.select('.paging a[href]')]
    last=max(pages or [1]); rows=parse_sh(first)
    if not rows: raise ValueError('SH empty: requires review')
    seen={tuple(n['id'] for n in rows)}
    for page in range(2,min(last,10)+1):
        time.sleep(1); parsed=parse_sh(request(SH+'?'+urlencode(dict(cp=page,supplyType='publicLease'))))
        fingerprint=tuple(n['id'] for n in parsed)
        if not parsed or fingerprint in seen: raise ValueError('SH pagination invalid')
        seen.add(fingerprint); rows.extend(parsed)
    return rows,dict(pageCap=10,completeWithinQuery=last<=10,query='서울시 SH 공공임대 미러 · 첨부/분양/기타 공지 제외')

def merge(old, fresh, successful):
    by_id={n['id']:dict(n) for n in old}; seen=set()
    for n in fresh:
        seen.add(n['id']); previous=by_id.get(n['id'])
        n['firstSeenAt']=previous.get('firstSeenAt',previous['checkedAt']) if previous else n['checkedAt']
        history=list(previous.get('changes',[])) if previous else []
        if previous and previous['hash']!=n['hash']:
            history.append(dict(at=NOW(),previousHash=previous['hash'],status=previous['status'],title=previous['title']))
        n['changes']=history[-30:]; by_id[n['id']]=n
    for ident,n in by_id.items():
        if n['source'] in successful and ident not in seen: n['missingFromLatest']=True
    return sorted(by_id.values(),key=lambda n:n['published'],reverse=True)

def main():
    old=json.loads(DATA.read_text()) if DATA.exists() else dict(notices=[],sources={})
    fresh=[]; successful=[]; sources=dict(old.get('sources',{})); failures=[]
    for name,fn in [('LH',collect_lh),('SH',collect_sh)]:
        try:
            rows,scope=fn(); fresh.extend(rows); successful.append(name)
            sources[name]=dict(ok=True,lastAttempt=NOW(),lastSuccess=NOW(),count=len(rows),scope=scope)
        except Exception as error:
            failures.append(name)
            sources[name]={**sources.get(name,{}),'ok':False,'lastAttempt':NOW(),'error':type(error).__name__}
            print(name+' collection failed: '+type(error).__name__,file=sys.stderr)
    output=dict(updatedAt=NOW(),sources=sources,notices=merge(old['notices'],fresh,successful),
                omissions=['GH 및 기타 기관','LH 분양/토지/상가','SH 분양/기타 공지','첨부파일 및 공고별 소득표 미검토'])
    DATA.parent.mkdir(parents=True,exist_ok=True)
    temp=DATA.with_suffix('.tmp'); temp.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n'); os.replace(temp,DATA)
    print('Public notices:',len(output['notices']),'successful sources:',','.join(successful))
    return 1 if failures else 0
if __name__=='__main__': sys.exit(main())

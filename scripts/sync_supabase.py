"""Server-only snapshot sync. Secrets never enter output or generated web files."""
import base64, json, os, re, sys
from urllib.request import Request, urlopen
from pathlib import Path
PATH=Path(__file__).resolve().parents[1]/'runtime/notices.json'

def config():
    url=os.environ.get('SUPABASE_URL','').rstrip('/')
    key=os.environ.get('SUPABASE_SECRET_KEY','')
    if not re.fullmatch(r'https://[a-z0-9]+\.supabase\.co',url) or not key:
        raise ValueError('Missing server configuration')
    if key.startswith('sb_secret_'):return url,{'apikey':key,'Content-Type':'application/json'}
    try:
        part=key.split('.')[1]; claims=json.loads(base64.urlsafe_b64decode(part+'='*(-len(part)%4)))
        if claims.get('role')!='service_role':raise ValueError()
    except Exception:raise ValueError('A server secret key is required') from None
    return url,{'apikey':key,'Authorization':'Bearer '+key,'Content-Type':'application/json'}

def sync(mode):
    url,headers=config();endpoint=url+'/rest/v1/house_snapshot'
    if mode=='pull':
        req=Request(endpoint+'?id=eq.current&select=payload',headers=headers)
        with urlopen(req,timeout=30) as r:rows=json.load(r)
        if rows:
            value=rows[0]['payload']
            if not isinstance(value.get('notices'),list):raise ValueError('Invalid snapshot')
            PATH.parent.mkdir(parents=True,exist_ok=True);PATH.write_text(json.dumps(value,ensure_ascii=False))
        print('Previous protected snapshot loaded' if rows else 'No prior snapshot')
    elif mode=='push':
        value=json.loads(PATH.read_text())
        # Collector output only; never accept household profiles or credentials.
        if set(value)!={'updatedAt','sources','notices','omissions'}:raise ValueError('Unexpected payload fields')
        for n in value['notices']:
            if n.get('source') not in ('SH','LH') or n.get('eligibility')!='unknown' or n.get('income') is not None:raise ValueError('Unreviewed payload schema')
            if any(k in n for k in ('email','password','profile','household','user_id')):raise ValueError('Personal data prohibited')
        headers['Prefer']='resolution=merge-duplicates,return=minimal'
        body=json.dumps(dict(id='current',payload=value,updated_at=value['updatedAt']),ensure_ascii=False).encode()
        with urlopen(Request(endpoint+'?on_conflict=id',data=body,headers=headers,method='POST'),timeout=30) as r:r.read()
        print('Protected official metadata snapshot synced')
    else:raise ValueError('Unknown mode')
if __name__=='__main__':
    try:sync(sys.argv[1])
    except Exception:
        print('Protected sync failed; verify server Secrets, table migration and project availability.',file=sys.stderr)
        sys.exit(1)

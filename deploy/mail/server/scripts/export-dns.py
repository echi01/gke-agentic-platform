"""Export only public DKIM/SPF data; never exports a private signing key."""
import base64,json,pathlib,ssl,subprocess,urllib.request,shlex
ROOT=pathlib.Path(__file__).resolve().parents[4];FOLDER=ROOT/'deploy/mail/server';E=json.loads((FOLDER/'environment.json').read_text());BASE='https://'+E['hostname']
raw=subprocess.check_output(['gcloud','secrets','versions','access','latest','--secret=progressbar-mail-admin','--project='+E['projectId'],'--account='+E['account']],text=True);creds=json.loads(raw)
auth=base64.b64encode((creds['username']+':'+creds['password']).encode()).decode()
def call(method,args,account):
 req=urllib.request.Request(BASE+'/jmap/',data=json.dumps({'using':['urn:ietf:params:jmap:core','urn:stalwart:jmap'],'methodCalls':[[method,{'accountId':account,**args},'op']]}).encode(),headers={'Content-Type':'application/json','Authorization':'Basic '+auth})
 with urllib.request.urlopen(req,timeout=30) as r:payload=json.load(r)['methodResponses'][0]
 if payload[0]=='error':raise RuntimeError(method+' failed')
 return payload[1]
sreq=urllib.request.Request(BASE+'/jmap/session',headers={'Authorization':'Basic '+auth})
with urllib.request.urlopen(sreq,timeout=20) as r:session=json.load(r)
account=session['primaryAccounts']['urn:stalwart:jmap'];ids=call('x:Domain/query',{'filter':{'name':E['domain']}},account)['ids'];domain=call('x:Domain/get',{'ids':ids,'properties':['id','name','dnsZoneFile']},account)['list'][0]
zone=domain['dnsZoneFile'];records={};group=''
for line in zone.splitlines():
 line=line.strip()
 if not line or line.startswith(';'):continue
 group+=' '+line
 if group.count('(')>group.count(')'):continue
 fields=shlex.split(group.replace('(',' ').replace(')',' '));group=''
 if len(fields)>=4 and fields[1]=='IN' and fields[2]=='TXT':
  name=fields[0];text=''.join(fields[3:])
  if '._domainkey.' in name or name==E['hostname']+'.':
   # One DNS TXT RDATA, split into <=255-byte quoted chunks for Google.
   chunks=['"'+text[i:i+250].replace('\\','\\\\').replace('"','\\"')+'"' for i in range(0,len(text),250)]
   records[name]={'name':name,'type':'TXT','ttl':300,'rrdatas':[' '.join(chunks)]}
if len([k for k in records if '._domainkey.' in k])<1:raise RuntimeError('DKIM public keys are not ready yet; no DNS file written')
(FOLDER/'public-dns.json').write_text(json.dumps(records,indent=2)+'\n');print('Public records exported:',list(records))

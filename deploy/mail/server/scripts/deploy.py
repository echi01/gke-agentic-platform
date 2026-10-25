"""Apply the reviewed mail-only Terraform root and provision secret payloads privately."""
import json,os,pathlib,secrets,subprocess,time,concurrent.futures,sys,fcntl
ROOT=pathlib.Path(__file__).resolve().parents[4];FOLDER=ROOT/'deploy/mail/server';E=json.loads((FOLDER/'environment.json').read_text());LOGS=ROOT/'.local/mail';LOGS.mkdir(parents=True,exist_ok=True);TF=str(ROOT/'.tools/terraform')
LOCK=(LOGS/'deploy.lock').open('w');fcntl.flock(LOCK,fcntl.LOCK_EX)
CLOUD=['--project='+E['projectId'],'--account='+E['account']]
def cloud(*args,**kwargs):return subprocess.run(['gcloud',*args,*CLOUD],capture_output=True,check=True,**kwargs)
def env():return dict(os.environ,TF_IN_AUTOMATION='true',GOOGLE_OAUTH_ACCESS_TOKEN=cloud('auth','print-access-token',text=True).stdout.strip())
def tf(args,log):return subprocess.run([TF,'-chdir='+str(FOLDER),*args],env=env(),stdout=log,stderr=subprocess.STDOUT,check=True)
def credential(name):
 for _ in range(90):
  try:
   versions=json.loads(cloud('secrets','versions','list',name,'--format=json',text=True).stdout)
   if any(v.get('state')=='ENABLED' for v in versions):return cloud('secrets','versions','access','latest','--secret='+name,text=True).stdout
   value=secrets.token_urlsafe(40)
   cloud('secrets','versions','add',name,'--data-file=-',input=value.encode());return value
  except subprocess.CalledProcessError:time.sleep(3)
 raise RuntimeError('Mail secret metadata not created')
with (LOGS/'deploy.log').open('w') as log:
 tf(['init','-input=false','-no-color','-backend-config=bucket='+E['stateBucket'],'-backend-config=prefix=production/mail'],log)
 tf(['validate','-no-color'],log)
 plan=LOGS/'server.tfplan';tf(['plan','-input=false','-no-color','-out='+str(plan)],log)
 result=subprocess.run([TF,'-chdir='+str(FOLDER),'show','-json',str(plan)],env=env(),capture_output=True,check=True)
 data=json.loads(result.stdout)
 for r in data.get('resource_changes',[]):
  if r.get('mode')=='managed' and 'delete' in r['change']['actions']:
   if '--allow-instance-replace' not in sys.argv or r['address']!='google_compute_instance.mail':raise RuntimeError('Mail deployment refuses deletion/replacement; review explicitly')
 print('Reviewed mail-only plan; applying.',flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
  apply=pool.submit(tf,['apply','-input=false','-no-color',str(plan)],log)
  admin=credential('progressbar-mail-bootstrap');credential('progressbar-mail-hello')
  apply.result()
 try:
  existing=json.loads(cloud('secrets','versions','list','progressbar-mail-admin','--format=json',text=True).stdout)
  if not any(v.get('state')=='ENABLED' for v in existing):cloud('secrets','versions','add','progressbar-mail-admin','--data-file=-',input=json.dumps({'username':'admin@'+E['domain'],'password':admin}).encode())
 except subprocess.CalledProcessError:raise RuntimeError('Could not retain mail admin credential') from None
 result=subprocess.run([TF,'-chdir='+str(FOLDER),'output','-json','server'],env=env(),capture_output=True,check=True)
 output=json.loads(result.stdout);(LOGS/'server.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output),flush=True)

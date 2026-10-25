"""Save owner connection details privately on the operator's computer; never print passwords."""
import json,os,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[4];E=json.loads((ROOT/'deploy/mail/server/environment.json').read_text());OUT=ROOT/'.local/mail/connection-details.json'
def secret(n):return subprocess.check_output(['gcloud','secrets','versions','access','latest','--secret='+n,'--project='+E['projectId'],'--account='+E['account']],text=True).strip()
payload={'hostname':E['hostname'],'username':'hello@'+E['domain'],'password':secret('progressbar-mail-hello'),'imap':{'port':993,'security':'TLS'},'smtp':{'port':465,'security':'TLS','authentication':'password required'},'smtpAlternative':{'port':587,'security':'STARTTLS required'},'aliases':['support@'+E['domain'],'postmaster@'+E['domain'],'abuse@'+E['domain']],'administrator':json.loads(secret('progressbar-mail-admin')),'adminUrl':'https://'+E['hostname']+'/admin','outboundInternetDelivery':'Blocked on Google external destination port 25; allow rule already applied'}
fd=os.open(OUT,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
with os.fdopen(fd,'w') as f:json.dump(payload,f,indent=2);f.write('\n')
os.chmod(OUT,0o600);print('Private connection details saved at '+str(OUT))

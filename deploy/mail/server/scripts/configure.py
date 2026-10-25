"""Converge pinned Stalwart through its real JMAP configuration API.

Runs on the mail VM. Secret payloads stay out of Terraform state, metadata and logs.
Administration over HTTP is used only on VM loopback during a bounded recovery phase.
"""
import base64, concurrent.futures, datetime, json, os, pathlib, secrets, socket, ssl, subprocess, time, urllib.request, urllib.error
ROOT = pathlib.Path('/srv/stalwart')
PRIVATE = ROOT / 'private'
BASE = 'http://127.0.0.1:8080'

def metadata(key):
    req = urllib.request.Request('http://metadata.google.internal/computeMetadata/v1/' + key, headers={'Metadata-Flavor':'Google'})
    with urllib.request.urlopen(req, timeout=10) as r: return r.read().decode()

def secret(name, project):
    for attempt in range(12):
        try:
            token=json.loads(metadata('instance/service-accounts/default/token'))['access_token']
            req=urllib.request.Request(f'https://secretmanager.googleapis.com/v1/projects/{project}/secrets/{name}/versions/latest:access',headers={'Authorization':'Bearer '+token})
            with urllib.request.urlopen(req,timeout=20) as r: return base64.b64decode(json.load(r)['payload']['data']).decode()
        except urllib.error.HTTPError as e:
            if e.code not in (403,404): raise RuntimeError('Mail credential retrieval failed') from None
            time.sleep(10)
    raise RuntimeError('Mail credential not provisioned in Secret Manager')

def private_write(path, data):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.chmod(0o600);tmp.replace(path)

def api(method, args, password, account='d333333'):
    body={'using':['urn:ietf:params:jmap:core','urn:stalwart:jmap'],'methodCalls':[[method,{'accountId':account,**args},'op']]}
    auth=base64.b64encode(('admin:'+password).encode()).decode()
    req=urllib.request.Request(BASE+'/jmap/',data=json.dumps(body).encode(),headers={'Authorization':'Basic '+auth,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=120) as r: data=json.load(r)
    name,payload,_=data['methodResponses'][0]
    if name=='error' or any(payload.get(k) for k in ['notCreated','notUpdated','notDestroyed']):
        # Configuration errors may contain submitted secret fields: never log payloads.
        private_write(PRIVATE/'last-api-error.json',data)
        raise RuntimeError('Stalwart rejected '+method+'; inspect protected diagnostic on VM')
    return payload

def session(password):
    auth=base64.b64encode(('admin:'+password).encode()).decode()
    for _ in range(90):
        try:
            req=urllib.request.Request(BASE+'/jmap/session',headers={'Authorization':'Basic '+auth})
            with urllib.request.urlopen(req,timeout=3) as r: return json.load(r)
        except (OSError,ValueError): time.sleep(1)
    raise RuntimeError('Stalwart private management listener did not become ready')

def container(image, password=None, recovery=False):
    subprocess.run(['docker','rm','-f','progressbar-stalwart'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    command=['docker','run','-d','--name','progressbar-stalwart','--restart','unless-stopped','--network','host','--memory','1536m','--log-opt','max-size=10m','--log-opt','max-file=3','-v',str(ROOT/'config')+':/etc/stalwart','-v',str(ROOT/'data')+':/var/lib/stalwart']
    if password:
        envfile=PRIVATE/'bootstrap.env';envfile.write_text('STALWART_RECOVERY_ADMIN=admin:'+password+'\n'+('STALWART_RECOVERY_MODE=1\n' if recovery else ''));envfile.chmod(0o600);command+=['--env-file',str(envfile)]
    subprocess.run(command+[image],check=True,stdout=subprocess.DEVNULL)

def named(method, name, password):
    ids=api('x:'+method+'/query',{'filter':{'name':name}},password).get('ids',[])
    if not ids:return None
    return next((x for x in api('x:'+method+'/get',{'ids':ids},password)['list'] if x.get('name')==name),None)

def configure_objects(password, mailbox_password, domain, hostname=None):
    d=named('Domain',domain,password)
    if not d: raise RuntimeError('Expected configured mail domain missing')
    domain_id=d['id']
    cm=d.get('certificateManagement',{})
    if hostname and cm.get('@type')=='Automatic':
        cm={**cm,'subjectAlternativeNames':{hostname:True}}
        api('x:Domain/set',{'update':{domain_id:{'certificateManagement':cm,'allowRelaying':False}}},password)
    # Terraform publishes these public keys. Keep generated keys stable until
    # an operator deliberately rotates them and commits matching DNS records.
    if '._domainkey.' in d.get('dnsZoneFile','') and d.get('dkimManagement',{}).get('@type')=='Automatic':
        api('x:Domain/set',{'update':{domain_id:{'dkimManagement':{'@type':'Manual'}}}},password)
    for localpart, role, pw, aliases in [('admin','Admin',password,[]),('hello','User',mailbox_password,['support','postmaster','abuse'])]:
        old=named('Account',localpart+'@'+domain,password)
        if not old:
            # User name filters can be local-part based in registry queries.
            items=api('x:Account/get',{},password).get('list',[])
            old=next((x for x in items if x.get('domainId')==domain_id and x.get('name') in [localpart,localpart+'@'+domain]),None)
        fields={'@type':'User','name':localpart,'domainId':domain_id,'description':'Progress Bar '+('system administrator' if role=='Admin' else 'business mailbox'),'roles':{'@type':role},'permissions':{'@type':'Inherit'},'credentials':{'0':{'@type':'Password','secret':pw}},'aliases':{str(i):{'name':a,'domainId':domain_id,'enabled':True} for i,a in enumerate(aliases)}}
        if old:
            patch={k:v for k,v in fields.items() if k not in ['@type','name','domainId']}
            api('x:Account/set',{'update':{old['id']:patch}},password)
        else: api('x:Account/set',{'create':{'mailbox':fields}},password)
    # Materialize every desired listener: upstream defaults are virtual until
    # a listener collection is explicitly configured. Adding only 587 would
    # otherwise replace the virtual defaults with a one-listener collection.
    desired=[('smtp',25,'smtp',False),('submissions',465,'smtp',True),('submission',587,'smtp',False),('imaps',993,'imap',True),('https',443,'http',True)]
    for name,port,protocol,implicit in desired:
        existing=named('NetworkListener',name,password)
        fields={'name':name,'bind':{'[::]:'+str(port):True},'protocol':protocol,'useTls':True,'tlsImplicit':implicit}
        if existing:api('x:NetworkListener/set',{'update':{existing['id']:{k:v for k,v in fields.items() if k!='name'}}},password)
        else:api('x:NetworkListener/set',{'create':{name:fields}},password)
    listeners=api('x:NetworkListener/get',{},password).get('list',[])
    destroy=[x['id'] for x in listeners if x.get('name') not in {d[0] for d in desired}]
    if destroy:api('x:NetworkListener/set',{'destroy':destroy},password)
    api('x:Action/set',{'create':{'reload':{'@type':'ReloadSettings'}}},password)
    private_write(PRIVATE/'mailbox-access.json',{'server':domain,'username':'hello@'+domain,'password':mailbox_password,'adminUsername':'admin@'+domain})
    dns=api('x:Domain/get',{'ids':[domain_id],'properties':['id','name','dnsZoneFile']},password)
    private_write(PRIVATE/'domain-dns.json',dns)
    return domain_id

def probe():
    def one(pair):
        host,port=pair
        try:
            address=socket.getaddrinfo(host,port,socket.AF_INET,socket.SOCK_STREAM)[0][4]
            with socket.create_connection(address,timeout=8):return {'host':host,'port':port,'connected':True}
        except OSError as e:return {'host':host,'port':port,'connected':False,'error':type(e).__name__}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        checks=list(pool.map(one,[('gmail-smtp-in.l.google.com',25),('aspmx.l.google.com',25),('mta5.am0.yahoodns.net',25),('smtp.gmail.com',587),('www.google.com',443)]))
    return {'testedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'sendsMail':False}

def ensure_docker():
    version=subprocess.check_output(['docker','version','--format','{{.Server.Version}}'],text=True).strip()
    if int(version.split('.')[0])>=28:return
    # Debian 12's old engine cannot unpack the pinned upstream OCI layers.
    # Use Docker's signed official APT repository, not an unreviewed installer.
    script=r"""set -eu
export DEBIAN_FRONTEND=noninteractive
dpkg --configure -a >/dev/null
apt-get install -y -qq ca-certificates curl >/dev/null
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
printf 'deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable\n' > /etc/apt/sources.list.d/docker.list
apt-get update -qq
apt-get remove -y -qq docker.io containerd runc >/dev/null
apt-get install -y -qq docker-ce docker-ce-cli containerd.io >/dev/null
systemctl enable --now docker
"""
    subprocess.run(['bash','-c',script],check=True)

def ensure_certificate_job(password, domain_id, domain, hostname):
    # Bootstrap/recovery restarts can leave a one-hour lock on the initial ACME
    # task. Once the final public listeners are live, replace that interrupted
    # task only when the server still has no valid hostname certificate.
    for _ in range(15):
        try:
            with socket.create_connection(('127.0.0.1',443),timeout=2) as raw:
                with ssl.create_default_context().wrap_socket(raw,server_hostname=hostname):return
        except (OSError,ssl.SSLError):time.sleep(2)
    auth=base64.b64encode(('admin@'+domain+':'+password).encode()).decode()
    def local(method,args):
        body={'using':['urn:ietf:params:jmap:core','urn:stalwart:jmap'],'methodCalls':[[method,{'accountId':'d333333',**args},'op']]}
        req=urllib.request.Request('https://127.0.0.1/jmap/',data=json.dumps(body).encode(),headers={'Authorization':'Basic '+auth,'Content-Type':'application/json'})
        # The temporary self-signed certificate is accepted on VM loopback
        # only. Public acceptance tests always validate the CA and hostname.
        with urllib.request.urlopen(req,context=ssl._create_unverified_context(),timeout=20) as r:response=json.load(r)
        name,result,_=response['methodResponses'][0]
        if name=='error' or result.get('notCreated') or result.get('notDestroyed'):
            private_write(PRIVATE/'last-api-error.json',response);raise RuntimeError('Certificate task setup failed; inspect protected diagnostic')
        return result
    tasks=local('x:Task/get',{})['list']
    ids=[x['id'] for x in tasks if x.get('@type')=='AcmeRenewal' and x.get('domainId')==domain_id]
    now=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    local('x:Task/set',{'destroy':ids,'create':{'renewal':{'@type':'AcmeRenewal','domainId':domain_id,'status':{'@type':'Pending','due':now}}}})
    print('Certificate provisioning queued after final listener startup.',flush=True)

def main():
    PRIVATE.mkdir(parents=True,exist_ok=True);PRIVATE.chmod(0o700)
    subprocess.run(['systemctl','stop','exim4.service'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(['systemctl','mask','exim4.service'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    project=metadata('instance/attributes/mail-project');domain=metadata('instance/attributes/mail-domain');hostname=metadata('instance/attributes/mail-hostname');image=metadata('instance/attributes/mail-image')
    password=secret('progressbar-mail-bootstrap',project);mailbox_password=secret('progressbar-mail-hello',project)
    ensure_docker()
    subprocess.run(['docker','pull',image],check=True,stdout=subprocess.DEVNULL)
    if not (ROOT/'config/config.json').exists():
        container(image,password);s=session(password)
        settings={'serverHostname':hostname,'defaultDomain':domain,'requestTlsCertificate':True,'generateDkimKeys':True,'tracer':{'@type':'Stdout','enable':True,'level':'info','ansi':False}}
        result=api('x:Bootstrap/set',{'update':{'singleton':settings}},password,next(iter(s['accounts'])))
        # Save generated one-time admin credential securely until permanent convergence.
        private_write(PRIVATE/'bootstrap-result.json',result)
    container(image,password,recovery=True);session(password)
    domain_id=configure_objects(password,mailbox_password,domain,hostname)
    container(image) # No recovery environment in the live server.
    (PRIVATE/'bootstrap.env').unlink(missing_ok=True)
    ensure_certificate_job(password,domain_id,domain,hostname)
    result=probe();private_write(ROOT/'connectivity.json',result)
    print('Stalwart configuration applied; management recovery disabled. Outbound probes: '+json.dumps(result),flush=True)

if __name__=='__main__':main()

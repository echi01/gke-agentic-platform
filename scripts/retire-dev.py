"""Retire the cloud dev runtime without deleting the landing page, DNS or Git repos.

The deployment profile must be disabled in Git first. Every Terraform plan is
saved privately and audited before application. Terraform states are backed up
locally; credentials are never printed. Run data export/retirement separately.
"""
import argparse, importlib.util, json, os, pathlib, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('deployment',ROOT/'scripts/deploy-dev.py')
D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
def cleanup_api_discovery(config):
 """Remove aggregated APIs served by namespaces being retired, avoiding dead discovery."""
 env = dict(os.environ, KUBECONFIG=str(config))
 items = json.loads(subprocess.check_output(['kubectl', 'get', 'apiservices', '-o', 'json'], env=env, text=True))['items']
 for item in items:
  if item.get('spec', {}).get('service', {}).get('namespace') in ['monitoring', 'argocd', 'istio-system']:
   subprocess.run(['kubectl', 'delete', 'apiservice', item['metadata']['name']], env=env, check=True)

def main():
 os.umask(0o077)
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');p.add_argument('--backup-directory',required=True);a=p.parse_args()
 if D.PROFILE.get('runtimeEnabled',True):p.error('Disable runtimeEnabled in the committed dev profile first.')
 backup=pathlib.Path(a.backup_directory).resolve();backup.mkdir(parents=True,exist_ok=True);backup.chmod(0o700)
 def env(extra=None):
  return dict(os.environ,GOOGLE_OAUTH_ACCESS_TOKEN=D.capture(['gcloud','auth','print-access-token',*D.ACCOUNT]),TF_IN_AUTOMATION='true',**(extra or {}))
 def run(folder,args,extra=None,capture=False):
  return subprocess.run([D.TF,'-chdir='+str(folder),*args],env=env(extra),check=True,text=True,stdout=subprocess.PIPE if capture else None).stdout
 def prepare(stage,extra=None):
  folder=ROOT/'deploy/dev'/stage;run(folder,['init','-input=false','-no-color','-backend-config=backend.config'],extra)
  state=run(folder,['state','pull'],extra,True);file=backup/(stage+'.tfstate')
  if not file.exists():
   with open(file,'x',opener=lambda path,flags:os.open(path,flags,0o600)) as out:out.write(state)
  return folder,json.loads(state)
 def reconcile(stage,extra=None,destroy=False,protection=False):
  folder,state=prepare(stage,extra)
  if destroy and not state.get('resources'):print(stage+': already empty.',flush=True);return
  plan=backup/(stage+('-destroy' if destroy else '-prepare')+'.tfplan')
  args=['plan','-input=false','-no-color','-out='+str(plan)]
  if destroy:args+=['-destroy']
  if protection:args+=['-target=module.platform.module.gke.google_container_cluster.main']
  run(folder,args,extra)
  changes=json.loads(run(folder,['show','-json',str(plan)],extra,True)).get('resource_changes',[])
  for change in changes:
   actions=change['change']['actions']
   if actions==['no-op'] or actions==['read']:continue
   if destroy and actions!=['delete']:raise RuntimeError('Unexpected non-destroy action in '+stage)
   if change['type'] in ['github_repository','google_dns_managed_zone','google_dns_record_set','google_firebase_hosting_site','google_identity_platform_config']:raise RuntimeError('Protected resource would change: '+change['address'])
   if protection and not (change['type']=='google_container_cluster' and actions==['update']):raise RuntimeError('Unexpected cluster preparation change.')
  if a.apply:run(folder,['apply','-input=false','-no-color',str(plan)],extra)
 config_dir=backup/'connection';config_dir.mkdir(exist_ok=True)
 config,tunnel,log=D.kubeconfig(config_dir)
 extra={'TF_VAR_kubeconfig_path':str(config)}
 try:
  reconcile('gke',protection=True)
  for stage in ['workloads','addons','cluster-bootstrap']:
   if stage == 'cluster-bootstrap' and a.apply:cleanup_api_discovery(config)
   reconcile(stage,extra,destroy=True)
  reconcile('automation',destroy=True)
 finally:
  tunnel.terminate();tunnel.wait(timeout=15);log.close()
 reconcile('gke',destroy=True)
 # Reconcile retired bootstrap maps; repository resources remain protected.
 reconcile('bootstrap',{'GITHUB_TOKEN':D.capture(['gh','auth','token'])})
 print('Cloud dev runtime retired; live hosting, DNS and repository source are preserved.',flush=True)
if __name__=='__main__':main()

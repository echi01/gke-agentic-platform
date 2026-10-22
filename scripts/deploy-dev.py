"""Reconcile the committed dev configuration; credentials are injected at runtime.

One-time trusted bootstrap: backend -> gke -> dns -> bootstrap -> automation.
Ongoing GitHub workflow: gke -> dns -> cluster bootstrap -> add-ons -> application
resources -> workload registration. Google DNS records are managed by Terraform.
"""
import argparse, base64, json, os, pathlib, shutil, socket, ssl, subprocess, tempfile, time, urllib.request
ROOT = pathlib.Path(__file__).resolve().parents[1]
PROFILE = json.loads((ROOT / 'deploy/dev/environment.json').read_text())
TF = os.environ.get('TERRAFORM') or shutil.which('terraform') or str(ROOT / '.tools/terraform')
KUBECTL = os.environ.get('KUBECTL') or shutil.which('kubectl') or str(ROOT / '.tools/kubectl')
ACCOUNT = [] if os.environ.get('GITHUB_ACTIONS') == 'true' else ['--account=' + PROFILE['googleAccount']]
PROJECT = ['--project=' + PROFILE['projectId']]

def capture(args):
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError('Authentication or prerequisite unavailable for ' + args[0] + '; inspect privately. No credential payload was logged.')
    return result.stdout.strip()

def cloud(*args):
    return capture(['gcloud', *args, *PROJECT, *ACCOUNT])

def secret(name):
    return cloud('secrets', 'versions', 'access', 'latest', '--secret=' + name)

def terraform(folder, apply, extra_env=None):
    def environment():
        env = dict(os.environ, TF_IN_AUTOMATION='true', GOOGLE_OAUTH_ACCESS_TOKEN=capture(['gcloud', 'auth', 'print-access-token', *ACCOUNT]))
        env.update(extra_env or {})
        return env
    base = [TF, '-chdir=' + str(folder)]
    subprocess.run(base + ['init', '-input=false', '-no-color', '-backend-config=backend.config'], env=environment(), check=True)
    # Use a protected temporary directory: plan files can contain sensitive state.
    with tempfile.TemporaryDirectory(prefix='platform-plan-') as temporary:
        os.chmod(temporary, 0o700)
        plan = str(pathlib.Path(temporary) / 'reconcile.tfplan')
        subprocess.run(base + ['plan', '-input=false', '-no-color', '-out=' + plan], env=environment(), check=True)
        if apply:
            subprocess.run(base + ['apply', '-input=false', '-no-color', plan], env=environment(), check=True)

def kubeconfig(folder):
    cluster = json.loads(cloud('container', 'clusters', 'describe', 'platform-dev', '--region=' + PROFILE['region'], '--format=json'))
    endpoint = cluster['privateClusterConfig']['privateEndpoint']
    # Reserve a local port, avoiding any existing development application port.
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
    path = folder / 'kubeconfig'
    plugin = shutil.which('gke-gcloud-auth-plugin')
    if not plugin:
        sdk_plugin = pathlib.Path(shutil.which('gcloud') or '/missing/gcloud').resolve().parent / 'gke-gcloud-auth-plugin'
        if sdk_plugin.is_file(): plugin = str(sdk_plugin)
    if not plugin:
        raise RuntimeError('Install the official gke-gcloud-auth-plugin before deploying.')
    config = {'apiVersion': 'v1', 'kind': 'Config', 'current-context': 'platform-dev', 'clusters': [{'name': 'platform-dev', 'cluster': {'server': f'https://127.0.0.1:{port}', 'tls-server-name': endpoint, 'certificate-authority-data': cluster['masterAuth']['clusterCaCertificate']}}], 'contexts': [{'name': 'platform-dev', 'context': {'cluster': 'platform-dev', 'user': 'deployer'}}], 'users': [{'name': 'deployer', 'user': {'exec': {'apiVersion': 'client.authentication.k8s.io/v1beta1', 'command': plugin, 'interactiveMode': 'Never', 'provideClusterInfo': True, 'env': [] if not ACCOUNT else [{'name': 'CLOUDSDK_CORE_ACCOUNT', 'value': PROFILE['googleAccount']}]}}}]}
    path.write_text(json.dumps(config)); path.chmod(0o600)
    log = open(folder / 'tunnel.log', 'w')
    tunnel = subprocess.Popen(['gcloud', 'compute', 'ssh', PROFILE['operatorName'], '--zone=' + PROFILE['operatorZone'], *PROJECT, *ACCOUNT, '--tunnel-through-iap', '--ssh-key-file=' + str(folder / 'operator-key'), '--quiet', '--', '-N', '-L', f'127.0.0.1:{port}:{endpoint}:443', '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=30'], stdout=log, stderr=log)
    for _ in range(30):
        if tunnel.poll() is not None:
            raise RuntimeError('Private operator tunnel failed; inspect its private log.')
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=1):
                return path, tunnel, log
        except OSError:
            time.sleep(1)
    tunnel.terminate(); log.close()
    raise RuntimeError('Private operator tunnel did not become available.')

def retire_superseded_sync(config, name):
    # A running Argo sync retains its original source, even after Terraform
    # promotes the parent. Retire only that obsolete operation; Argo applies Git.
    command = [KUBECTL, '--kubeconfig', str(config), '-n', 'argocd']
    app = json.loads(capture(command + ['get', 'application', name, '-o', 'json']))
    state = app.get('status', {}).get('operationState', {})
    desired = app['spec']['source']['targetRevision']
    sync = state.get('operation', {}).get('sync', {})
    running = sync.get('revision')
    superseded = running and (running != desired or (sync.get('source') and sync['source'] != app['spec']['source']))
    if app.get('operation') and state.get('phase') == 'Running' and superseded:
        patch = [{'op': 'test', 'path': '/metadata/resourceVersion', 'value': app['metadata']['resourceVersion']},
                 {'op': 'replace', 'path': '/status/operationState/phase', 'value': 'Terminating'}]
        subprocess.run(command + ['patch', 'application', name, '--type=json', '-p', json.dumps(patch)], check=True)
        print('Retired superseded sync for ' + name + '; Argo will reconcile the committed revision.')

def application_checkout(folder):
    release = json.loads((ROOT / 'deploy/dev/workloads/release.auto.tfvars.json').read_text())['workloads']['progressbar-dev']
    key = folder / 'application-key'; key.write_text(json.loads(secret('platform-dev-argocd-application'))['sshPrivateKey']); key.chmod(0o600)
    # Authenticate SSH host keys through GitHub's HTTPS API, never an unverified ssh-keyscan.
    with urllib.request.urlopen('https://api.github.com/meta', timeout=20) as response:
        metadata = json.load(response)
    known = folder / 'known_hosts'; known.write_text(''.join('github.com ' + item + '\n' for item in metadata['ssh_keys']))
    env = dict(os.environ, GIT_SSH_COMMAND=f'ssh -i {key} -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile={known}')
    checkout = folder / 'application'; checkout.mkdir()
    subprocess.run(['git', 'init', '-q', str(checkout)], check=True)
    subprocess.run(['git', '-C', str(checkout), 'fetch', '--depth=1', release['repositoryUrl'], release['revision']], env=env, check=True)
    subprocess.run(['git', '-C', str(checkout), 'checkout', '-q', 'FETCH_HEAD'], check=True)
    return checkout

def wait_for_private_ingress(config):
    # Argo must remove the public Service before Terraform releases its reserved IP.
    # Wait for Google's service controller; do not delete forwarding rules by hand.
    for _ in range(100):
        service = json.loads(capture([KUBECTL, '--kubeconfig', str(config), '-n', 'traefik', 'get', 'service', 'traefik', '-o', 'json']))
        addresses = json.loads(cloud('compute', 'addresses', 'list', '--regions=' + PROFILE['region'], '--filter=name=platform-dev-ingress', '--format=json'))
        if service['spec']['type'] == 'ClusterIP' and not any(address.get('users') for address in addresses):
            return
        time.sleep(3)
    raise RuntimeError('The service controller has not released the former public ingress. DNS/IP resources were preserved; retry after the Argo Traefik application is healthy.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--stage', choices=['gke', 'dns', 'bootstrap', 'automation', 'cluster-bootstrap', 'addons', 'application-data', 'workloads', 'all'], default='all')
    args = parser.parse_args()
    if args.stage in ['gke', 'dns', 'automation', 'bootstrap']:
        extra = {}
        if args.stage == 'bootstrap':
            if os.environ.get('GITHUB_ACTIONS') == 'true':
                raise RuntimeError('Root repository bootstrap uses an independently authenticated GitHub administrator; the deployment workflow cannot grant itself repository access.')
            extra['GITHUB_TOKEN'] = capture(['gh', 'auth', 'token'])
        if args.stage == 'dns' and args.apply and not PROFILE.get('publicIngress', True):
            addresses = json.loads(cloud('compute', 'addresses', 'list', '--regions=' + PROFILE['region'], '--filter=name=platform-dev-ingress', '--format=json'))
            if any(address.get('users') for address in addresses):
                raise RuntimeError('Run --stage all first: private ingress must reconcile before Terraform releases the external address.')
        terraform(ROOT / 'deploy/dev' / args.stage, args.apply, extra)
        return
    with tempfile.TemporaryDirectory(prefix='platform-deploy-') as temporary:
        folder = pathlib.Path(temporary); folder.chmod(0o700)
        if args.stage == 'all':
            for stage in (['gke', 'dns'] if PROFILE.get('publicIngress', True) else ['gke']):
                terraform(ROOT / 'deploy/dev' / stage, args.apply)
        config, tunnel, log = kubeconfig(folder)
        try:
            extra = {'TF_VAR_kubeconfig_path': str(config)}
            for stage in ['cluster-bootstrap', 'addons', 'application-data', 'workloads']:
                if args.stage not in ['all', stage]:
                    continue
                target = ROOT / 'deploy/dev' / stage
                if stage == 'application-data':
                    target = application_checkout(folder) / 'deploy/kubernetes/terraform/environments/dev'
                terraform(target, args.apply, extra)
                if args.apply and stage in ['addons', 'workloads']:
                    retire_superseded_sync(config, 'platform-' + stage)
                if stage == 'addons' and args.stage == 'all' and not PROFILE.get('publicIngress', True):
                    if args.apply: wait_for_private_ingress(config)
                    terraform(ROOT / 'deploy/dev/dns', args.apply)
        finally:
            tunnel.terminate()
            try: tunnel.wait(timeout=10)
            except subprocess.TimeoutExpired: tunnel.kill(); tunnel.wait()
            log.close()

if __name__ == '__main__':
    main()

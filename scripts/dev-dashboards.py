"""Open private dev dashboards over IAP and loopback-only Kubernetes port-forwards.

No DNS, public ingress, cloud load balancer or permanent kubeconfig is created.
Keep running while using the dashboards; Ctrl-C closes every child process.
"""
import argparse, importlib.util, json, os, pathlib, signal, socket, subprocess, tempfile, time
ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('dev_deploy', ROOT / 'scripts/deploy-dev.py')
DEPLOY = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(DEPLOY)
TARGETS = {
    'argocd': ('argocd', 'service/argo-cd-argocd-server', 18080, 80, '/'),
    'grafana': ('monitoring', 'service/kube-prometheus-stack-grafana', 13000, 80, '/'),
    'prometheus': ('monitoring', 'service/kube-prometheus-stack-prometheus', 19090, 9090, '/'),
    'traefik': ('traefik', 'deployment/traefik', 18081, 8080, '/dashboard/'),
    'istio': ('istio-system', 'service/kiali', 12001, 20001, '/kiali/'),
}
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', nargs='+', choices=list(TARGETS), default=list(TARGETS))
    parser.add_argument('--credentials-file', help='Optionally save ArgoCD/Grafana sign-in credentials to a new private local file; never print them.')
    args = parser.parse_args()
    for name in args.only:
        with socket.socket() as probe:
            try: probe.bind(('127.0.0.1', TARGETS[name][2]))
            except OSError: parser.error(f'{name}: localhost port {TARGETS[name][2]} is occupied; stop the earlier session first.')
    if args.credentials_file:
        path = pathlib.Path(args.credentials_file).expanduser().resolve()
        if path.exists(): parser.error('The credentials file already exists; choose a new path.')
        data = {'argocd': {'username': 'admin', 'password': DEPLOY.secret('platform-dev-argocd-admin')},
                'grafana': {'username': 'admin', 'password': DEPLOY.secret('platform-dev-grafana-admin')}}
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'x', opener=lambda p, flags: os.open(p, flags, 0o600)) as out: json.dump(data, out, indent=2)
        print('Credentials saved privately at ' + str(path), flush=True)
    processes = {}; logs = {}
    with tempfile.TemporaryDirectory(prefix='platform-dashboards-') as directory:
        folder = pathlib.Path(directory); folder.chmod(0o700)
        config, tunnel, tunnel_log = DEPLOY.kubeconfig(folder)
        def stop(_signum, _frame): raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, stop)
        try:
            for name in args.only:
                ns, target, local, remote, route = TARGETS[name]
                logs[name] = open(folder / (name + '.log'), 'w+')
                processes[name] = subprocess.Popen([DEPLOY.KUBECTL, '--kubeconfig', str(config), '-n', ns,
                    'port-forward', '--address=127.0.0.1', target, f'{local}:{remote}'], stdout=logs[name], stderr=logs[name])
            deadline = time.monotonic() + 45
            pending = set(args.only)
            while pending and time.monotonic() < deadline:
                for name in list(pending):
                    if processes[name].poll() is not None: raise RuntimeError('Port-forward failed for ' + name + '; service may not be ready.')
                    try:
                        with socket.create_connection(('127.0.0.1', TARGETS[name][2]), timeout=0.3): pending.remove(name)
                    except OSError: pass
                time.sleep(0.2)
            if pending: raise RuntimeError('Timed out waiting for: ' + ', '.join(sorted(pending)))
            print(json.dumps({name: f'http://127.0.0.1:{TARGETS[name][2]}{TARGETS[name][4]}' for name in args.only}, indent=2), flush=True)
            print('All selected tunnels are ready. Keep this command running; Ctrl-C closes them.', flush=True)
            while tunnel.poll() is None:
                for name, process in list(processes.items()):
                    if process.poll() is None: continue
                    ns, target, local, remote, route = TARGETS[name]
                    print(name + ': reconnecting after the selected pod ended.', flush=True)
                    time.sleep(3)
                    processes[name] = subprocess.Popen([DEPLOY.KUBECTL, '--kubeconfig', str(config), '-n', ns,
                        'port-forward', '--address=127.0.0.1', target, f'{local}:{remote}'], stdout=logs[name], stderr=logs[name])
                time.sleep(1)
            raise RuntimeError('The private operator connection ended. Run this command again to reconnect.')
        except KeyboardInterrupt: pass
        finally:
            for process in [*processes.values(), tunnel]:
                if process.poll() is None: process.terminate()
            for process in [*processes.values(), tunnel]:
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill(); process.wait()
            for log in [*logs.values(), tunnel_log]: log.close()
if __name__ == '__main__': main()

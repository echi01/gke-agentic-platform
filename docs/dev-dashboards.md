# Private dev dashboards

Run `python scripts/dev-dashboards.py` after the dev add-ons reconcile. Authenticate to Google as the account in `deploy/dev/environment.json`. The script makes a temporary private kubeconfig, opens the IAP operator connection, and starts Kubernetes port-forwards bound exclusively to `127.0.0.1`.

| Interface | Local URL |
| --- | --- |
| Progress Bar app | http://127.0.0.1:14173/ |
| Argo CD | http://127.0.0.1:18080/ |
| Grafana | http://127.0.0.1:13000/ |
| Prometheus | http://127.0.0.1:19090/ |
| Traefik | http://127.0.0.1:18081/dashboard/ |
| Istio (Kiali view-only UI) | http://127.0.0.1:12001/kiali/ |

Argo CD and Grafana require sign-in. Use `--credentials-file /absolute/private/new-file.json` to retrieve their passwords from Google Secret Manager without printing them. Do not commit the resulting file. Kiali and Prometheus have no public route; operator access requires Google IAM and Kubernetes port-forward permissions. Traefik's dashboard is enabled only on its unexposed `traefik` entry point, not on `web` or `websecure`. Argo CD uses HTTP inside the encrypted operator tunnel and has no public ingress.

Keep the command running. Ctrl-C closes the tunnels. The command reconnects individual forwards after pod rollouts. If the underlying IAP connection ends, restart the command. `--only grafana prometheus` opens a subset. No dashboard DNS records, public ingress, or additional cloud load balancers are created.

The dev profile now sets `publicIngress: false`: the app and every dashboard are private, Traefik is ClusterIP, and Terraform removes the former external IP and dev A record after the service controller has deleted its load balancer. No cloud load balancer is required for these port-forwards. Google compute, storage and other existing service costs still apply. The production website stays on its existing hosting and DNS records.

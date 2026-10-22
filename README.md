# GKE Agentic Platform

Reusable **Google Cloud infrastructure**, independent of any business application. Version 1.0.0. Applications supply their own repositories, images, data resources and runtime charts. No application code is embedded here.

The repository uses the structure `deploy → infrastructure → modules`. Selected upstream Helm charts and their dependencies are stored locally under `vendor/helm`, with archive checksums and expanded-source hashes in `addons.lock.json`. Both Terraform and ArgoCD use those local chart paths.

```text
deploy/{dev,staging,prod}/
  backend/                 State-storage bootstrap
  gke/                     Private regional cluster, network, registry and nodes
  addons/                  ArgoCD bootstrap and selected platform add-ons
  workloads/               Register separately owned application releases
infrastructure/
  state-backend/           State-storage composition
  gke-platform/            Cluster composition
  platform-addons/         Add-on selection and Terraform-to-Argo handoff
  workload-delivery/       Independent application-registration parent
modules/
  gke/                     Reusable Google foundation
  state-backend/           Protected GCS state
  workload-identity/       Generic keyless workload identity and annotations
  kubernetes-addons/       One local integration module per selected add-on
charts/
  argocd-application/       Parent Application bootstrap
  addons/                  Infrastructure add-on Applications
  workloads/               External application projects and registrations
  kubernetes-mcp/          Private operational MCP runtime
  agent-inference/         Optional private CPU/GPU inference runtime
vendor/helm/               Expanded upstream charts and dependency source
operations/{kubectl-ai,mcp}/
examples/training/          Bounded Kueue/JobSet GPU example
scripts/                   Integrity, validation, bootstrap credentials and labs
tests/                     Operational MCP contracts
docs/                      Ownership, deployment, operational lab and verification
```

## Platform capabilities

- Private regional GKE Standard, Dataplane V2, workload federation, dedicated node identity, autoscaling CPU nodes and optional zero-minimum GPU pool.
- Protected state, separate environment roots and deployment-stage state prefixes. Production requires three minimum CPU nodes.
- Individual add-on integrations and a shared Helm helper. Participating add-ons support direct Terraform ownership or ArgoCD ownership; ArgoCD itself always boots through Terraform.
- Separate add-ons and workload parent Applications. Each external application gets its own namespace and restricted AppProject; privileged prerequisites use a separately reviewed project/release.
- Prometheus/Grafana, Prometheus Adapter, External Secrets, Istio and cert-manager. Optional Argo Rollouts, KEDA, Kueue, JobSet and public Istio gateway.
- kubectl-ai setup and a deployed, namespace-scoped MCP server with private stdio access, fixed inspection tools, no Secret/log/shell tools and no public HTTP endpoint.
- Pinned local chart source, immutable Git revisions, CI checks/scans and a reproducible local Kubernetes lab.

See [the add-on catalogue](docs/addons.md) for enabled defaults and ownership, [deployment](docs/deployment.md) for the sequence, and [the AI operations lab](docs/ai-operations-lab.md) for kubectl-ai and MCP.

## Run checks

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.lock
.venv/bin/python scripts/install-tools.py --bin-dir .tools
PATH="$PWD/.tools:$PATH" .venv/bin/python scripts/check.py --terraform
```

Checks verify vendored source, render selected charts, test ownership boundaries and run mocked plans. They do not create cloud resources or call a model. [Verification](docs/verification.md) separates observed local results from Google acceptance still required.

Application-specific databases, business agents, APIs, evidence rules, billing and product interfaces belong to application repositories. Infrastructure deployment is not an application launch.

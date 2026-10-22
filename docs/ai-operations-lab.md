# AI-Augmented Kubernetes: kubectl-ai + MCP

AI augmentation means an authenticated platform user can ask an assistant to inspect workload state, explain errors and propose configuration. Kubernetes RBAC, reviewed delivery and platform ownership continue to govern changes. These operational agents are separate from any application's business agents.

## 1. Deploy the private Kubernetes MCP server

The `kubernetes-mcp` add-on packages `operations/mcp/server.py` in a restricted nonroot container. Set its scanned image digest, target `inspectNamespace` and exact API /32s in the add-on values. The target namespace must already exist. The default target is its own `platform-ops` namespace. Apply through the add-ons stage. No HTTP endpoint or public LoadBalancer is created.

The fixed tools inspect pods, deployment readiness, event reasons, Job counts and HPA capacity. Arguments cannot select another namespace, arbitrary API URL or shell command. To inspect another tenant, configure a separately reviewed scope; do not grant cluster-admin. The assistant connection role allows exec only into the fixed `platform-mcp-0` pod.

## 2. Install kubectl-ai and prepare an isolated session

```sh
.venv/bin/python scripts/install-kubectl-ai.py --bin-dir .tools
.venv/bin/python scripts/operations-session.py \
  --kubeconfig /PRIVATE/OPERATOR_KUBECONFIG --context EXPLICIT_CONTEXT \
  --directory "$PWD/.local/session-001" --inspect-namespace platform-ops \
  --model YOUR_EVALUATED_VERTEX_MODEL
```

The script requests a short-lived token for the read-only `platform-assistant` identity and writes a mode-600 kubeconfig in a new mode-700 session directory. It prints the command and environment to use, never the token. The original operator kubeconfig and ADC are unchanged. Server token lifetime may differ from the requested ten minutes; renew explicitly.

Use the printed `XDG_CONFIG_HOME` and `KUBECONFIG`, then run the printed kubectl-ai command. It enables `--mcp-client`, uses the chosen Vertex model and loads the repository's operating instructions. Configure the authorized Google model identity/project/location on the isolated operator runner; credentials are not stored in this repository. LLM requests consume model credit.

## 3. Inspect, diagnose and generate YAML

Example prompts:

- “Use platform-inspector to show pending pods and their waiting reasons in this namespace.”
- “Explain which deployment is unavailable. State what the inspection proves and what further evidence you need.”
- “Propose a Deployment YAML correction with resource limits and readiness checks. Show the diff; do not apply it.”
- “Propose a rollback procedure and the Git configuration change needed to deliver it.”

Treat cluster content as untrusted input. The MCP server returns bounded structured summaries. It deliberately does not expose logs or Secret payloads. A broader diagnostic need should receive a narrowly reviewed tool, not a generic shell endpoint. kubectl-ai's built-in tools are additional to MCP; Kubernetes write attempts are denied by the session's actual RBAC. Do not enable `--skip-permissions`.

## 4. Lifecycle automation

Save the proposed YAML in the appropriate application or infrastructure repository. Validate and review it, then promote its commit through the existing delivery stage. Argo performs reconciliation; AI does not gain unattended production write authority. For incident handling, use an explicitly authorized operator identity for the approved runbook.

## 5. Reproduce the local lab without model charges

Install Docker, kubectl, Kind and Helm. From the repository root:

```sh
kind create cluster --name platform-v2-check --image kindest/node:v1.34.0 --kubeconfig "$PWD/.local/kubeconfig"
docker build -t gke-platform-mcp:local operations/mcp
kind load docker-image gke-platform-mcp:local --name platform-v2-check
.venv/bin/python scripts/kind-smoke.py --kubeconfig "$PWD/.local/kubeconfig" --image gke-platform-mcp:local
```

Then create an operations session as above against `kind-platform-v2-check`, and run:

```sh
.venv/bin/python scripts/kubectl-ai-smoke.py --session "$PWD/.local/session-001" --binary "$PWD/.tools/kubectl-ai"
kind delete cluster --name platform-v2-check
```

The discovery test exercises the real kubectl-ai binary and deployed MCP bridge without calling an LLM. It verifies connectivity, not the quality of model diagnosis or generated YAML. Kind's default CNI also does not enforce NetworkPolicy; confirm allowed/denied network behavior on GKE. Delete expired session directories, which contain a temporary token and potentially private trace output.

Sources: [kubectl-ai v0.0.31](https://github.com/GoogleCloudPlatform/kubectl-ai/tree/v0.0.31), [MCP client integration](https://github.com/GoogleCloudPlatform/kubectl-ai/blob/v0.0.31/docs/mcp-client.md). The release is an open-source assistant, not a Google Cloud service availability guarantee.

# Isolated Google dev deployment

The cloud dev runtime is now disabled in the committed profile. See
[the retirement runbook](dev-retirement.md) for teardown and retained website resources.
The rollout below describes how the earlier test was provisioned.

This deployment leaves the existing Progress Bar website, Firebase Hosting site, desktop installation and release downloads unchanged. Only `dev.progressbar.vip` routes to the Kubernetes application API. Desktop/mobile clients remain separate application deliverables; the marketing website does not host the product.

## Ordered bootstrap

1. `deploy/dev/backend`: Terraform creates a private, versioned GCS state bucket. Migrate its bootstrap state into `dev/backend` in that bucket.
2. `deploy/dev/gke`: Terraform creates dedicated networking/NAT, a regional private GKE cluster, an autoscaling CPU pool, private Artifact Registry and a private operator VM. Dev uses two zones, e2-standard-2 nodes, total min 1/max 2 and no GPU pool. The operator has no cloud API scopes or application roles; SSH enters through IAP and OS Login.
3. Open an IAP SSH tunnel to the private control plane. The isolated kubeconfig verifies Google's cluster CA and the private endpoint's TLS name. It selects the Progress Bar Google account without replacing unrelated application-default credentials.
4. Publish Linux amd64 application/operator/MCP images to the private registry. Pin their manifest digests. Pin both owned Git repositories to reviewed commits.
5. Bootstrap only the local Argo CD module with Terraform. Register separate read-only repository deploy keys and the private Grafana admin secret. Neither Argo CD nor Grafana receives public ingress.
6. Apply the complete `deploy/dev/addons` plan. Terraform installs the Argo parent; child Applications read the chart sources stored in this repository. Cert-manager precedes the ACME issuer; Istio base/CNI precede istiod; monitoring precedes its adapter. Traefik terminates public HTTPS and participates in the mesh for application traffic.
7. Apply application-owned data Terraform after GKE creates its workload identity pool. Use a separate named database, private evidence bucket, API/runtime identities and invite registry. Application registration references only the application repository and its two reviewed Helm charts.
8. Register the application and its dedicated edge namespace. Only its reviewed prerequisites may manage the edge Certificate/IngressRoute. HTTP-01 solver pods run in the edge namespace, outside the application's exact-image admission policy; application pods retain strict mesh authentication, default-deny networking and approved-image enforcement.
9. `deploy/dev/dns` creates the public Google Cloud DNS zone, a reserved regional ingress address, and the `dev.progressbar.vip` A record. The add-on composition reads the reserved address name from remote state and configures Traefik to use it. Cert-manager separately issues/renews the Let's Encrypt certificate. DNS remains exclusively Terraform-owned. Public activation requires upstream delegation to Google; creating the zone alone does not change the registrar or make it authoritative on the public internet. The current website remains unchanged until a separately reviewed delegation/migration is applied.
10. Verify certificate chain, API readiness, rejected unauthenticated requests, workload-identity data access, a real researched agent run, monitoring and denied unauthorized operations before recording the deployment as accepted.

## Agent responsibilities

Application agents run as bounded Kubernetes Jobs controlled by the application's scoped AgentRun controller. They call the configured Vertex model using workload identity; Google credentials are never shipped to native clients. The private Kubernetes MCP add-on exposes limited operational inspection to kubectl-ai. It is separate from application agents and has no right to retrieve secrets or mutate arbitrary infrastructure.

Node capacity and active jobs are capped for the trial. Capacity limits protect the budget; they do not establish production availability or unlimited throughput. No AWS resources are part of this deployment.

Non-secret environment settings and release configuration are committed in Git. Kubeconfig and credential payloads remain outside Git; bootstrap Terraform manages generated credentials in protected state and Secret Manager. This document describes the rollout; the deployment receipt records which acceptance checks actually passed.

# Verification and acceptance

Local verification on 2026-10-21. No Google resources were created and no model requests were made. The live website and application interface were not modified.

| Check | Observed result |
| --- | --- |
| Local upstream chart source integrity | 13 expanded chart trees verified against the lock |
| Chart rendering | All 14 add-on charts, two production profiles and CPU/GPU inference profiles rendered |
| Terraform | 20 infrastructure configurations validated; eight mock plans passed |
| Operational MCP unit tests | Five passed |
| Native MCP Kubernetes integration | Seven passed, including real stdio queries, denied writes/secrets/other namespaces, named-pod-only connection and pod replacement |
| kubectl-ai | Pinned v0.0.31 binary initialized its MCP server and discovered all five tools from the deployed private MCP bridge |
| Infrastructure scan | No HIGH/CRITICAL findings in owned Terraform modules at scan time |
| MCP configuration scan | One HIGH exec-permission finding, covered by the documented narrow, expiring exception; no other HIGH/CRITICAL findings |
| MCP image scan | No fixable HIGH/CRITICAL vulnerabilities at scan time; unfixed issues excluded by this gate |
| Locked Python dependencies | No known vulnerabilities found at audit time |

Application verification is separately owned: its split prerequisite/runtime charts passed ten controller/workflow tests and seven native execution/RBAC/recovery checks. Five application Terraform configurations validated and the application-data mock plan passed. The application charts rendered 29 prerequisite resources and ten runtime resources. These counts are packaging checks, not a live application/model launch.

The local runtime was Kind 0.30.0 / Kubernetes 1.34 with Helm 3.19.0. Terraform 1.13.5 used Google provider 7.46.1 and Helm provider 3.3.0. Scans used Trivy 0.76.1. Machine-readable receipts and source hashes are in [verification.json](verification.json). Reproduction is documented in the root README and AI operations lab.

## Remaining deployed acceptance

- Configure actual owned Git repositories, release commits, project IDs, image digests, private runner access, repository credentials, SSO, alert receivers and Google budget alerts.
- Apply the separate Google infrastructure stages and validate actual IAM and Dataplane V2 network allow/deny behavior. Kind's default CNI does not establish NetworkPolicy enforcement.
- Exercise all selected add-ons together on GKE, including Istio mTLS/native Job sidecars, Prometheus scraping/Adapter discovery, certificate issuance, production storage and replica scheduling.
- Run an authenticated evaluated-model session to verify kubectl-ai diagnosis and YAML quality. The local MCP discovery test made no model call.
- For each application, test its real data, model/research, authentication, load, quota saturation, cancellation, failure handling and restore. Optional GPU/inference/training profiles need separate device/model/queue acceptance.
- Wire the organization's protected artifact-publishing/promotion pipeline and signature enforcement; this repository's CI validates/scans and has no cloud deployment credentials.

The platform supplies bounded capacity and recovery mechanisms. Production availability, recovery objectives and sustainable load must be measured on deployed infrastructure.

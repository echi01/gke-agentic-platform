# Deployment sequence

Use separate Google projects and protected branches per environment. Never run against an implicit Kubernetes context. All roots are independent Terraform states. No cloud apply was performed while building this repository.

1. **backend:** copy `deploy/dev/backend/terraform.tfvars.example` to a private local tfvars file, initialize, review a saved plan and apply through the platform operator. This creates the protected GCS bucket, not application storage. Migrate this bootstrap state into protected storage: add a `backend.tf` selecting GCS and run `terraform init -migrate-state` with bucket/prefix configuration. Preserve the local state securely until migration is verified; it is ignored by Git. Repeat with each environment project.
2. **gke:** configure the environment GKE root, initialize with its `state.backend.hcl.example` copied locally and real bucket. Review and apply a saved plan. Private control-plane access requires a runner/VPN on an authorized private network. Node/pod CIDRs are authorized by default; add explicitly reviewed operator CIDRs to the GKE module when a separate network is used.
3. **credentials and artifacts:** obtain cluster credentials into an explicit, separate kubeconfig using the intended Google account, project and region. Do not overwrite another account's ADC. Build/scan the MCP image from `operations/mcp`, publish it to the platform registry and supply its immutable digest and exact API endpoint /32s in `addon_values`. Configure Grafana's `grafana-admin` Secret and ArgoCD SSO/RBAC before operational UI access. UIs stay ClusterIP.
4. **addons:** set the owned infrastructure repository, a reviewed 40-character commit, selected add-on flags and values. `scripts/verify-vendor.py` must pass. Run Terraform in `deploy/dev/addons` with the dedicated kubeconfig/context. Terraform boots ArgoCD from the local chart and installs its add-ons parent. Argo reads this repository's local chart paths at the pinned commit. If the repository is private, bootstrap the repository credential as described below after Argo is installed; then reconciliation can proceed.
5. **workloads:** application owners prepare their own data resources, images, charts and release. Register only repository/path/commit/namespace/values in `deploy/dev/workloads`. The separate workload parent creates namespace boundaries and application AppProjects. Optional prerequisite charts containing CRDs, RBAC, admission or secret integration require platform-owner review. Runtime application releases cannot alter those resources.
6. **acceptance:** test GKE workload identities, allowed/denied network paths, Istio mTLS/native Job sidecars, model/API quotas, metrics discovery, autoscaling, alert delivery, upgrades and restores. Enable the optional gateway/certificates and application traffic only after these checks. Certificate issuers and DNS challenges need explicit organization/domain configuration.

The production add-on profile enables replicated Argo server/repository services with Redis HA, two Prometheus replicas with persistent volumes and three Alertmanager replicas. It is a starting configuration requiring production load, disruption, storage and restore acceptance—not a measured availability guarantee. GPU pools, inference, training and KEDA are opt-in.

## Private repository credential bootstrap

Store a JSON credential object with `username`/`password` or `sshPrivateKey` in Secret Manager. The operator must have access only to that secret and permission to create the named repository Secret in Argo's namespace.

```sh
.venv/bin/python scripts/register-repository.py \
  --kubeconfig /PRIVATE/KUBECONFIG --context EXPLICIT_CONTEXT \
  --account YOUR_GOOGLE_ACCOUNT --project YOUR_PROJECT \
  --secret YOUR_REPOSITORY_SECRET --repository YOUR_OWNED_GIT_URL
```

Preview is the default. Add `--apply` to read the credential and pass it directly to Kubernetes over stdin. The script does not print the payload or write it to local files/Terraform state. Use the same procedure for private application sources when their registration needs it.

## Promotion and recovery

Build and scan images, commit reviewed configuration/vendor source, and promote a selected commit through staging before production. The CI workflow here verifies without cloud credentials; it does not publish images or apply infrastructure. Connect the organization's protected publishing/promotion identity separately.

Argo automated pruning starts disabled. Remove resources through an explicit lifecycle change. Roll back to a reviewed compatible Git/image revision; application database migrations and restores are application-owned. Test node loss, controller replacement, queue saturation, state recovery and private operator access. GKE resource/model quotas and bounded pool/job sizes limit capacity; they do not constitute a hard financial cap. Configure Google budget/credit alerts.

## Changing installation ownership

Choose `manage_via_gitops` before first installation. Flipping it on a live release without migration can uninstall the Terraform-owned Helm release. For a transfer: freeze changes, back up state and desired resources, disable automated reconciliation/pruning, review the exact resource handoff, remove the old Terraform release from state **without destroying it**, then establish and validate the new Argo owner. Re-enable reconciliation only after ownership is unambiguous. Reverse transfers require an equally explicit adoption procedure. Never let both systems reconcile the same installation.

# Ownership and application boundary

| Owner | Resources |
| --- | --- |
| Platform Terraform | State buckets, VPC/NAT, private GKE, node pools, node identity, platform registry |
| Add-ons Terraform bootstrap | ArgoCD Helm release and parent registration |
| Argo add-ons parent | Locally vendored add-on chart manifests and operational MCP |
| Workloads registration | Dedicated tenant namespace, default deny/quota, AppProjects and pinned external release references |
| Application prerequisite release | Reviewed application CRDs, scoped service identities/RBAC, admission, external-secret bindings and application network policies |
| Application runtime release | API/services, controllers, scheduled recovery, application configuration and HPA/PDB |
| Application controllers | Their own execution resources/status, subject to application RBAC/admission |

No business database or application model prompt is embedded in the infrastructure. Generic `modules/workload-identity` returns the namespace/service-account annotation contract; callers choose narrow roles. The platform MCP has no Google service account role and no model/API credential. Operational AI uses a separately authenticated operator identity.

Namespace Pod Security, AppProject resource allowlists, RBAC and NetworkPolicy are complementary controls. An AppProject is a delivery boundary, not a sandbox for hostile code. Prerequisite charts can define cluster-scoped CRDs/admission and therefore require platform review at the exact pinned release. Keep their release permission out of application-developer Argo roles.

The tenant runtime project cannot create Secrets, service accounts, Roles, RoleBindings, Jobs or cluster resources. It can deploy the reviewed runtime using identities prepared by the prerequisite release. Upstream platform controllers have separately reviewed broader permissions. Custom charts pin their workload images; upstream add-on images follow the reviewed vendored chart versions and still need vulnerability/signature policy review before promotion.

The private MCP transport is an authenticated Kubernetes exec stream. Its service account can only read selected resource types in one configured namespace. Its response excludes Pod environment values, Secret objects, log text and free-text event bodies. kubectl-ai's upstream built-ins include bash and kubectl: scoped RBAC constrains cluster access, but does not sandbox the operator host. Run it on a trusted isolated operator runner with only necessary credentials.

The Trivy exec-privilege rule flags the MCP connection Role even though it is restricted to one named pod. `security/trivyignore.yaml` records a time-limited exception for this rendered file only. Structural tests require that exact grant, and native RBAC tests deny unrestricted exec. This is an explicit operational permission, not a claim that exec has no risk.

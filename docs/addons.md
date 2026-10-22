# Add-on catalogue

Each entry has a local module under `modules/kubernetes-addons/NAME`, local defaults, an ownership switch and an Argo configuration output. ArgoCD itself always installs directly. All other listed charts can be installed by Terraform or reconciled by Argo.

| Add-on | Version | Default | Local chart source |
| --- | --- | --- | --- |
| argo-cd | 10.10.5 | Enabled | `vendor/helm/argo-cd/10.10.5/argo-cd` |
| kube-prometheus-stack | 92.11.0 | Enabled | `vendor/helm/kube-prometheus-stack/92.11.0/kube-prometheus-stack` |
| prometheus-adapter | 5.3.0 | Enabled | `vendor/helm/prometheus-adapter/5.3.0/prometheus-adapter` |
| external-secrets | 2.13.0 | Enabled | `vendor/helm/external-secrets/2.13.0/external-secrets` |
| istio-base | 1.30.6 | Enabled | `vendor/helm/istio-base/1.30.6/base` |
| istiod | 1.30.6 | Enabled | `vendor/helm/istiod/1.30.6/istiod` |
| istio-cni | 1.30.6 | Enabled | `vendor/helm/istio-cni/1.30.6/cni` |
| istio-gateway | 1.30.6 | Opt-in | `vendor/helm/istio-gateway/1.30.6/gateway` |
| kueue | 0.20.2 | Opt-in | `vendor/helm/kueue/0.20.2/kueue` |
| jobset | 0.13.0 | Opt-in | `vendor/helm/jobset/0.13.0/jobset` |
| cert-manager | v1.21.2 | Enabled | `vendor/helm/cert-manager/v1.21.2/cert-manager` |
| argo-rollouts | 2.43.8 | Opt-in | `vendor/helm/argo-rollouts/2.43.8/argo-rollouts` |
| keda | 2.21.0 | Opt-in | `vendor/helm/keda/2.21.0/keda` |
| kubernetes-mcp | 1.0.0 | Enabled | `charts/kubernetes-mcp` |

Selected optional components have concrete roles: the gateway exposes approved services; Argo Rollouts supports canary/blue-green application releases; KEDA supports event-driven scaling; Kueue/JobSet admit grouped AI/training jobs. Their installation alone does not configure an application's Rollout, ScaledObject, model weights or training code.

The GKE service manages core cluster networking/DNS and node autoscaling; separate AWS CNI, kube-proxy, Cluster Autoscaler, Karpenter, Fargate, EMR, gaming and alternative ingress examples are absent.

Module `values_override` replaces whole top-level sections. Supply complete nested sections, including security defaults, when overriding them. Use the checked-in production profiles as examples. Keep Istio base/CNI/istiod selected together; Prometheus mesh scraping relies on that profile. Configure an actual Istio proxy digest in the istiod values and the corresponding application image policies before deploying strict application admission.

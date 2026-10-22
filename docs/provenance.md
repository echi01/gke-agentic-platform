# Source and design provenance

The deployment/composition/module organization and per-add-on handoff pattern were reviewed against `echi01/aws-blueprint` at commit `2b5890204baed3434e8ee726a94594feef3b3576`: https://github.com/echi01/aws-blueprint/tree/2b5890204baed3434e8ee726a94594feef3b3576 . No AWS deployment modules or unused example stacks are included in this Google repository.

The previous local GKE blueprint supplied the private Google foundation, security concepts, inference/training examples and operational inspection starting point. Business-specific resources were separated into the application. This repository replaces the previous combined blueprint as the reusable platform source.

Official chart metadata, versions, archive SHA256s, OCI digests where applicable, local paths and expanded-tree hashes are recorded in `addons.lock.json`. Upstream packaged source/license notices are preserved in `vendor/helm`. Record and review a new lock plus module values before upgrading.

Primary documentation used: [GKE workload identity](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/workload-identity), [ArgoCD declarative setup](https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/), [cert-manager Helm installation](https://cert-manager.io/docs/installation/helm/), [kubectl-ai](https://github.com/GoogleCloudPlatform/kubectl-ai). No provider affiliation or certification is implied.

# external-secrets

Locally maintained integration for `vendor/helm/external-secrets/2.13.0/external-secrets`. Defaults are in `values.yaml`; `values_override` replaces top-level sections, so supply a complete section when overriding nested keys.

`manage_via_gitops=true` exports the Argo handoff and skips the direct Helm release. With false, Terraform owns that release. ArgoCD itself is always bootstrapped directly. Switch ownership only through the documented migration procedure.

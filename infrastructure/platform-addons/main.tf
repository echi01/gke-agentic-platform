terraform {
  required_providers { helm = { source = "hashicorp/helm", version = "~> 3.3.0" } }
}
variable "repository_url" {
  type = string
}
variable "revision" {
  type = string
  validation {
    condition     = can(regex("^[a-f0-9]{40}$", var.revision))
    error_message = "Use an immutable reviewed infrastructure commit."
  }
}
variable "manage_via_gitops" {
  type    = bool
  default = true
}
variable "enabled_addons" {
  type    = map(bool)
  default = {}
  validation {
    condition     = alltrue([for name in keys(var.enabled_addons) : contains(["kiali", "traefik", "certificate-issuers", "kube-prometheus-stack", "prometheus-adapter", "external-secrets", "istio-base", "istiod", "istio-cni", "istio-gateway", "kueue", "jobset", "cert-manager", "argo-rollouts", "keda", "kubernetes-mcp"], name)])
    error_message = "Use a supported add-on key; ArgoCD is always bootstrapped."
  }
}
variable "addon_values" {
  type    = any
  default = {}
}
module "argo_cd" {
  source            = "../../modules/kubernetes-addons/argo-cd"
  enabled           = true
  manage_via_gitops = false
  values_override   = lookup(var.addon_values, "argo-cd", {})
}

module "cert_manager" {
  source            = "../../modules/kubernetes-addons/cert-manager"
  enabled           = lookup(var.enabled_addons, "cert-manager", true)
  manage_via_gitops = var.manage_via_gitops
  values_override   = lookup(var.addon_values, "cert-manager", {})
}

module "external_secrets" {
  source            = "../../modules/kubernetes-addons/external-secrets"
  enabled           = lookup(var.enabled_addons, "external-secrets", true)
  manage_via_gitops = var.manage_via_gitops
  values_override   = lookup(var.addon_values, "external-secrets", {})
}

module "istio_base" {
  source            = "../../modules/kubernetes-addons/istio-base"
  enabled           = lookup(var.enabled_addons, "istio-base", true)
  manage_via_gitops = var.manage_via_gitops
  values_override   = lookup(var.addon_values, "istio-base", {})
}

module "istio_cni" {
  depends_on        = [module.istio_base]
  source            = "../../modules/kubernetes-addons/istio-cni"
  enabled           = lookup(var.enabled_addons, "istio-cni", true)
  manage_via_gitops = var.manage_via_gitops
  values_override   = lookup(var.addon_values, "istio-cni", {})
}

module "istiod" {
  depends_on        = [module.istio_base, module.istio_cni]
  source            = "../../modules/kubernetes-addons/istiod"
  enabled           = lookup(var.enabled_addons, "istiod", true)
  manage_via_gitops = var.manage_via_gitops
  values_override   = lookup(var.addon_values, "istiod", {})
}

module "istio_gateway" {
  depends_on        = [module.istiod]
  source            = "../../modules/kubernetes-addons/istio-gateway"
  enabled           = lookup(var.enabled_addons, "istio-gateway", false)
  manage_via_gitops = var.manage_via_gitops
  values_override   = lookup(var.addon_values, "istio-gateway", {})
}

module "kube_prometheus_stack" {
  depends_on        = [module.istiod]
  source            = "../../modules/kubernetes-addons/kube-prometheus-stack"
  enabled           = lookup(var.enabled_addons, "kube-prometheus-stack", true)
  manage_via_gitops = var.manage_via_gitops
  values_override   = lookup(var.addon_values, "kube-prometheus-stack", {})
}

module "prometheus_adapter" {
  depends_on        = [module.kube_prometheus_stack]
  source            = "../../modules/kubernetes-addons/prometheus-adapter"
  enabled           = lookup(var.enabled_addons, "prometheus-adapter", true)
  manage_via_gitops = var.manage_via_gitops
  values_override   = lookup(var.addon_values, "prometheus-adapter", {})
}

module "argo_rollouts" {
  source            = "../../modules/kubernetes-addons/argo-rollouts"
  enabled           = lookup(var.enabled_addons, "argo-rollouts", false)
  manage_via_gitops = var.manage_via_gitops
  values_override   = lookup(var.addon_values, "argo-rollouts", {})
}

module "keda" {
  source            = "../../modules/kubernetes-addons/keda"
  enabled           = lookup(var.enabled_addons, "keda", false)
  manage_via_gitops = var.manage_via_gitops
  values_override   = lookup(var.addon_values, "keda", {})
}

module "kueue" {
  depends_on        = [module.cert_manager]
  source            = "../../modules/kubernetes-addons/kueue"
  enabled           = lookup(var.enabled_addons, "kueue", false)
  manage_via_gitops = var.manage_via_gitops
  values_override   = lookup(var.addon_values, "kueue", {})
}

module "jobset" {
  source            = "../../modules/kubernetes-addons/jobset"
  enabled           = lookup(var.enabled_addons, "jobset", false)
  manage_via_gitops = var.manage_via_gitops
  values_override   = lookup(var.addon_values, "jobset", {})
}

module "kubernetes_mcp" {
  source            = "../../modules/kubernetes-addons/kubernetes-mcp"
  enabled           = lookup(var.enabled_addons, "kubernetes-mcp", true)
  manage_via_gitops = var.manage_via_gitops
  values_override   = lookup(var.addon_values, "kubernetes-mcp", {})
}

module "traefik" {
  depends_on        = [module.istiod]
  source            = "../../modules/kubernetes-addons/traefik"
  enabled           = lookup(var.enabled_addons, "traefik", false)
  manage_via_gitops = var.manage_via_gitops
  values_override   = lookup(var.addon_values, "traefik", {})
}
module "kiali" {
  depends_on        = [module.istiod, module.kube_prometheus_stack]
  source            = "../../modules/kubernetes-addons/kiali"
  enabled           = lookup(var.enabled_addons, "kiali", false)
  manage_via_gitops = var.manage_via_gitops
  values_override   = lookup(var.addon_values, "kiali", {})
}
module "certificate_issuers" {
  depends_on        = [module.cert_manager]
  source            = "../../modules/kubernetes-addons/certificate-issuers"
  enabled           = lookup(var.enabled_addons, "certificate-issuers", false)
  manage_via_gitops = var.manage_via_gitops
  values_override   = lookup(var.addon_values, "certificate-issuers", {})
}

locals {
  addons = { for name, config in {
    "kiali"                 = module.kiali.gitops_config
    "traefik"               = module.traefik.gitops_config
    "certificate-issuers"   = module.certificate_issuers.gitops_config
    "cert-manager"          = module.cert_manager.gitops_config
    "external-secrets"      = module.external_secrets.gitops_config
    "istio-base"            = module.istio_base.gitops_config
    "istio-cni"             = module.istio_cni.gitops_config
    "istiod"                = module.istiod.gitops_config
    "istio-gateway"         = module.istio_gateway.gitops_config
    "kube-prometheus-stack" = module.kube_prometheus_stack.gitops_config
    "prometheus-adapter"    = module.prometheus_adapter.gitops_config
    "argo-rollouts"         = module.argo_rollouts.gitops_config
    "keda"                  = module.keda.gitops_config
    "kueue"                 = module.kueue.gitops_config
    "jobset"                = module.jobset.gitops_config
    "kubernetes-mcp"        = module.kubernetes_mcp.gitops_config
  } : name => config if config != null }
}
resource "helm_release" "addons_parent" {
  count     = var.manage_via_gitops ? 1 : 0
  name      = "platform-addons-root"
  namespace = "argocd"
  chart     = "${path.module}/../../charts/argocd-application"
  values = [yamlencode({ name = "platform-addons", repositoryUrl = var.repository_url,
    revision = var.revision, path = "charts/addons", createProject = true,
  parameters = { repositoryUrl = var.repository_url, revision = var.revision, addons = local.addons } })]
  depends_on = [module.argo_cd]
}
output "gitops_configuration" { value = { repositoryUrl = var.repository_url, revision = var.revision, addons = local.addons } }

resource "terraform_data" "profile" {
  input = var.enabled_addons
  lifecycle {
    precondition {
      condition     = !lookup(var.enabled_addons, "istiod", true) || (lookup(var.enabled_addons, "istio-base", true) && lookup(var.enabled_addons, "istio-cni", true))
      error_message = "The selected Istio control plane requires its base and GKE CNI integrations."
    }
  }
}

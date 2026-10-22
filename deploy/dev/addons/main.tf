terraform {
  required_version = ">= 1.8"
  required_providers {
    helm   = { source = "hashicorp/helm", version = "~> 3.3.0" }
    google = { source = "hashicorp/google", version = "~> 7.0" }
    random = { source = "hashicorp/random", version = "~> 3.7" }
  }
  backend "gcs" {}
}
variable "kubeconfig_path" {
  type = string
}
variable "kube_context" {
  type = string
}
variable "repository_url" {
  type = string
}
variable "revision" {
  type = string
}
provider "helm" {
  kubernetes = { config_path = var.kubeconfig_path, config_context = var.kube_context }
}

variable "manage_via_gitops" {
  type    = bool
  default = true
}
variable "enabled_addons" {
  type    = map(bool)
  default = {}
}
variable "addon_values" {
  type    = any
  default = {}
}
module "addons" {
  source            = "../../../infrastructure/platform-addons"
  repository_url    = var.repository_url
  revision          = var.revision
  manage_via_gitops = var.manage_via_gitops
  enabled_addons    = var.enabled_addons
  addon_values      = merge(var.addon_values, { traefik = merge(local.desired_traefik, { service = local.ingress_service }), "argo-cd" = local.argo_values })
}
output "gitops_configuration" { value = module.addons.gitops_configuration }

locals {
  environment             = jsondecode(file("${path.module}/../environment.json"))
  desired_traefik         = lookup(var.addon_values, "traefik", {})
  desired_ingress_service = lookup(local.desired_traefik, "service", {})
  ingress_service = merge(local.desired_ingress_service, {
    annotations = merge(lookup(local.desired_ingress_service, "annotations", {}), try(local.environment.publicIngress, true) ? {
      "networking.gke.io/load-balancer-ip-addresses" = data.terraform_remote_state.dns[0].outputs.dns.ingress_address_name
    } : {})
  })
}
data "terraform_remote_state" "dns" {
  count   = try(local.environment.publicIngress, true) ? 1 : 0
  backend = "gcs"
  config = {
    bucket = local.environment.stateBucket
    prefix = "dev/dns"
  }
}

# Administrative sign-in remains private behind the authenticated operator tunnel.
provider "google" {
  project = local.environment.projectId
  region  = local.environment.region
}
resource "random_password" "argo_admin" {
  length  = 32
  special = false
}
resource "google_secret_manager_secret" "argo_admin" {
  project   = local.environment.projectId
  secret_id = "platform-dev-argocd-admin"
  replication {
    auto {}
  }
}
resource "google_secret_manager_secret_version" "argo_admin" {
  secret      = google_secret_manager_secret.argo_admin.id
  secret_data = random_password.argo_admin.result
}
locals {
  desired_argo = lookup(var.addon_values, "argo-cd", {})
  argo_values = merge(local.desired_argo, {
    configs = merge(lookup(local.desired_argo, "configs", {}), {
      secret = { argocdServerAdminPassword = random_password.argo_admin.bcrypt_hash }
    })
  })
}

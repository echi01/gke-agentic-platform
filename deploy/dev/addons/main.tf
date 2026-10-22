terraform {
  required_version = ">= 1.8"
  required_providers { helm = { source = "hashicorp/helm", version = "~> 3.3.0" } }
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
  addon_values      = merge(var.addon_values, { traefik = merge(local.desired_traefik, { service = local.ingress_service }) })
}
output "gitops_configuration" { value = module.addons.gitops_configuration }

locals {
  environment             = jsondecode(file("${path.module}/../environment.json"))
  desired_traefik         = lookup(var.addon_values, "traefik", {})
  desired_ingress_service = lookup(local.desired_traefik, "service", {})
  ingress_service = merge(local.desired_ingress_service, {
    annotations = merge(lookup(local.desired_ingress_service, "annotations", {}), {
      "networking.gke.io/load-balancer-ip-addresses" = data.terraform_remote_state.dns.outputs.dns.ingress_address_name
    })
  })
}
data "terraform_remote_state" "dns" {
  backend = "gcs"
  config = {
    bucket = local.environment.stateBucket
    prefix = "dev/dns"
  }
}

terraform {
  required_providers { helm = { source = "hashicorp/helm", version = "~> 3.3.0" } }
}
locals {
  definition   = jsondecode(file("${path.module}/../../../addons.lock.json"))["external-secrets"]
  chart_values = merge(yamldecode(file("${path.module}/values.yaml")), var.values_override)
}
module "addon" {
  source            = "../helm-addon"
  enabled           = var.enabled
  manage_via_gitops = var.manage_via_gitops
  release_name      = "external-secrets"
  namespace         = "external-secrets"
  chart_path        = abspath("${path.module}/../../../${local.definition.path}")
  git_path          = local.definition.path
  chart_version     = local.definition.version
  chart_values      = local.chart_values
  sync_wave         = -10
}

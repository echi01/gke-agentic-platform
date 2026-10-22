terraform {
  required_providers { helm = { source = "hashicorp/helm", version = "~> 3.3.0" } }
}
variable "enabled" {
  type    = bool
  default = true
}
variable "manage_via_gitops" {
  type    = bool
  default = true
}
variable "release_name" {
  type = string
}
variable "namespace" {
  type = string
}
variable "chart_path" {
  type = string
}
variable "git_path" {
  type = string
}
variable "chart_version" {
  type = string
}
variable "chart_values" {
  type    = any
  default = {}
}
variable "sync_wave" {
  type    = number
  default = 0
}
resource "helm_release" "addon" {
  count             = var.enabled && !var.manage_via_gitops ? 1 : 0
  name              = var.release_name
  namespace         = var.namespace
  chart             = var.chart_path
  create_namespace  = true
  atomic            = true
  cleanup_on_fail   = true
  wait              = true
  timeout           = 900
  dependency_update = false
  values            = [yamlencode(var.chart_values)]
}
output "gitops_config" {
  value = var.enabled && var.manage_via_gitops ? {
    name    = var.release_name, namespace = var.namespace, path = var.git_path,
    version = var.chart_version, values = var.chart_values, wave = var.sync_wave
  } : null
}

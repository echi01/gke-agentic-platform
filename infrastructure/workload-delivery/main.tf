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
    error_message = "Pin the infrastructure commit."
  }
}
variable "workloads" {
  type = map(object({ repositoryUrl = string, revision = string, namespace = string,
    path = string, extensionPath = optional(string, ""), edgeNamespace = optional(string, ""), mesh = optional(bool, true),
  observerGroups = optional(list(string), []), values = optional(any, {}) }))
  default = {}
  validation {
    condition     = alltrue([for name, app in var.workloads : can(regex("^[a-f0-9]{40}$", app.revision))])
    error_message = "Pin every external application to a reviewed commit."
  }
}
resource "helm_release" "workloads_parent" {
  name      = "platform-workloads-root"
  namespace = "argocd"
  chart     = abspath("${path.module}/../../charts/argocd-application")
  values = [yamlencode({ name = "platform-workloads", repositoryUrl = var.repository_url,
  revision = var.revision, path = "charts/workloads", parameters = { workloads = var.workloads } })]
}

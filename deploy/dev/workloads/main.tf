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

variable "workloads" {
  type    = any
  default = {}
}
module "workloads" {
  source         = "../../../infrastructure/workload-delivery"
  repository_url = var.repository_url
  revision       = var.revision
  workloads      = var.workloads
}

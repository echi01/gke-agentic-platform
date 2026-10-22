terraform {
  required_providers { google = { source = "hashicorp/google", version = "~> 7.0" } }
}
variable "project_id" {
  type = string
}
variable "region" {
  type = string
}
variable "environment" {
  type = string
}
variable "name_prefix" {
  type    = string
  default = "platform"
}
variable "zones" {
  type = list(string)
}
variable "enable_gpu" {
  type    = bool
  default = false
}
variable "cpu_min_nodes" {
  type    = number
  default = 1
}
variable "cpu_max_nodes" {
  type    = number
  default = 4
}
module "gke" {
  source              = "../../modules/gke"
  project_id          = var.project_id
  region              = var.region
  environment         = var.environment
  name_prefix         = var.name_prefix
  zones               = var.zones
  cpu_min_nodes       = var.cpu_min_nodes
  cpu_max_nodes       = var.cpu_max_nodes
  machine_type        = var.machine_type
  enable_gpu          = var.enable_gpu
  gpu_machine_type    = "g2-standard-4"
  gpu_type            = "nvidia-l4"
  gpu_max_nodes       = 1
  deletion_protection = true
  node_cidr           = "10.40.0.0/20"
  pod_cidr            = "10.44.0.0/14"
  service_cidr        = "10.48.0.0/20"
  master_cidr         = "172.16.0.0/28"
}
output "platform" {
  value = { cluster_name = module.gke.cluster_name, region = var.region, registry = module.gke.registry,
  private_endpoint = module.gke.private_endpoint, project_id = var.project_id }
}

variable "enable_private_operator" {
  type    = bool
  default = false
}
module "private_operator" {
  count         = var.enable_private_operator ? 1 : 0
  source        = "../../modules/private-operator"
  project_id    = var.project_id
  name          = "${var.name_prefix}-${var.environment}"
  zone          = var.zones[0]
  network_id    = module.gke.network_id
  subnetwork_id = module.gke.subnetwork_id
}
output "private_operator" {
  value = var.enable_private_operator ? { name = module.private_operator[0].name, zone = module.private_operator[0].zone } : null
}

variable "machine_type" {
  type    = string
  default = "e2-standard-4"
}

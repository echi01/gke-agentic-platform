terraform {
  required_version = ">= 1.8"
  required_providers { google = { source = "hashicorp/google", version = "~> 7.0" } }
  backend "gcs" {}
}
variable "project_id" {
  type = string
}
variable "region" {
  type    = string
  default = "us-central1"
}
variable "zones" {
  type    = list(string)
  default = ["us-central1-a", "us-central1-b"]
}
variable "enable_gpu" {
  type    = bool
  default = false
}
provider "google" {
  project = var.project_id
  region  = var.region
}
module "platform" {
  source                  = "../../../infrastructure/gke-platform"
  project_id              = var.project_id
  region                  = var.region
  zones                   = var.zones
  environment             = "dev"
  cpu_min_nodes           = 1
  cpu_max_nodes           = 2
  enable_gpu              = var.enable_gpu
  enable_private_operator = true
  machine_type            = "e2-standard-2"
}
output "platform" { value = module.platform.platform }

output "private_operator" { value = module.platform.private_operator }

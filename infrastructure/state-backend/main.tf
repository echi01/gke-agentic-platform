terraform {
  required_providers { google = { source = "hashicorp/google", version = "~> 7.0" } }
}
variable "project_id" {
  type = string
}
variable "bucket_name" {
  type = string
}
variable "region" {
  type = string
}
module "state" {
  source      = "../../modules/state-backend"
  project_id  = var.project_id
  bucket_name = var.bucket_name
  region      = var.region
}
output "bucket" { value = module.state.bucket }

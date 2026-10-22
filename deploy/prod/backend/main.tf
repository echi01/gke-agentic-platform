terraform {
  required_version = ">= 1.8"
  required_providers { google = { source = "hashicorp/google", version = "~> 7.0" } }
  # Bootstrap once, then migrate this state to the protected bucket per the README.
}
variable "project_id" {
  type = string
}
variable "bucket_name" {
  type = string
}
variable "region" {
  type    = string
  default = "us-central1"
}
provider "google" {
  project = var.project_id
  region  = var.region
}
module "backend" {
  source      = "../../../infrastructure/state-backend"
  project_id  = var.project_id
  bucket_name = var.bucket_name
  region      = var.region
}
output "bucket" { value = module.backend.bucket }

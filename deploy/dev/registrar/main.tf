terraform {
  required_version = ">= 1.8"
  required_providers {
    google    = { source = "hashicorp/google", version = "~> 7.0" }
    namecheap = { source = "namecheap/namecheap", version = "= 2.9.5" }
  }
  backend "gcs" {}
}
locals { environment = jsondecode(file("${path.module}/../environment.json")) }
# Provider credentials are supplied by environment variables, never Git.
variable "namecheap_api_key" {
  type      = string
  sensitive = true
}
provider "namecheap" {
  use_sandbox = false
  api_key     = var.namecheap_api_key
}
provider "google" { project = local.environment.projectId }
resource "google_secret_manager_secret" "registrar" {
  project   = local.environment.projectId
  secret_id = "platform-dev-namecheap-api-key"
  replication {
    auto {}
  }
}
resource "google_secret_manager_secret_version" "registrar" {
  secret      = google_secret_manager_secret.registrar.id
  secret_data = var.namecheap_api_key
}
data "terraform_remote_state" "dns" {
  backend = "gcs"
  config = {
    bucket = local.environment.stateBucket
    prefix = "dev/dns"
  }
}
resource "namecheap_domain_records" "google_authority" {
  domain      = local.environment.parentDomain
  mode        = "OVERWRITE"
  nameservers = [for ns in data.terraform_remote_state.dns.outputs.parent_name_servers : trimsuffix(ns, ".")]
  lifecycle { prevent_destroy = true }
}
import {
  to = namecheap_domain_records.google_authority
  id = local.environment.parentDomain
}

terraform {
  required_version = ">= 1.8"
  required_providers {
    namecheap = { source = "namecheap/namecheap", version = "= 2.9.5" }
  }
  backend "gcs" {}
}
locals { environment = jsondecode(file("${path.module}/../environment.json")) }
# Provider credentials are supplied by environment variables, never Git.
provider "namecheap" { use_sandbox = false }
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

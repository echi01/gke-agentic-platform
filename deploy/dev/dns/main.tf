terraform {
  required_version = ">= 1.8"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 7.0" }
  }
  backend "gcs" {}
}
locals { environment = jsondecode(file("${path.module}/../environment.json")) }
provider "google" {
  project = local.environment.projectId
  region  = local.environment.region
}
module "dns" {
  count                  = try(local.environment.runtimeEnabled, true) ? 1 : 0
  source                 = "../../../modules/dns"
  public_ingress_enabled = try(local.environment.publicIngress, true)
  project_id             = local.environment.projectId
  region                 = local.environment.region
  name                   = "platform-dev"
  dns_name               = "${local.environment.domain}."
}
moved {
  from = module.dns
  to   = module.dns[0]
}
output "dns" { value = try(module.dns[0], null) }

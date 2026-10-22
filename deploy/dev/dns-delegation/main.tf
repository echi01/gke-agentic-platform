terraform {
  required_version = ">= 1.8"
  required_providers {
    cloudflare = { source = "cloudflare/cloudflare", version = "~> 5.24.0" }
  }
  backend "gcs" {}
}
locals { environment = jsondecode(file("${path.module}/../environment.json")) }
# The provider reads CLOUDFLARE_API_TOKEN supplied from Secret Manager at runtime.
provider "cloudflare" {}
data "terraform_remote_state" "dns" {
  backend = "gcs"
  config = {
    bucket = local.environment.stateBucket
    prefix = "dev/dns"
  }
}
data "cloudflare_zones" "parent" { name = local.environment.parentDomain }
resource "cloudflare_dns_record" "delegation" {
  for_each = toset(data.terraform_remote_state.dns.outputs.dns.name_servers)
  zone_id  = one(data.cloudflare_zones.parent.result).id
  name     = local.environment.domain
  type     = "NS"
  content  = trimsuffix(each.value, ".")
  ttl      = 300
  proxied  = false
  comment  = "Terraform: Google Cloud DNS delegation for isolated dev only"
  lifecycle {
    precondition {
      condition     = local.environment.domain == "dev.${local.environment.parentDomain}"
      error_message = "This stage may delegate only the dev child zone."
    }
  }
}

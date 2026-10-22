# Preserve the existing public website and mail when moving authority to Google.
resource "google_dns_managed_zone" "parent" {
  project     = local.environment.projectId
  name        = "progressbar-public"
  dns_name    = "${local.environment.parentDomain}."
  description = "Public domain DNS managed by Terraform on Google Cloud"
  visibility  = "public"
  depends_on  = [module.dns]
  lifecycle { prevent_destroy = true }
}
resource "google_dns_record_set" "parent" {
  for_each     = jsondecode(file("${path.module}/parent-records.json"))
  project      = local.environment.projectId
  managed_zone = google_dns_managed_zone.parent.name
  name         = each.value.name
  type         = each.value.type
  ttl          = each.value.ttl
  rrdatas      = each.value.rrdatas
}
resource "google_dns_record_set" "dev_delegation" {
  project      = local.environment.projectId
  managed_zone = google_dns_managed_zone.parent.name
  name         = "${local.environment.domain}."
  type         = "NS"
  ttl          = 300
  rrdatas      = module.dns.name_servers
}
output "parent_name_servers" { value = google_dns_managed_zone.parent.name_servers }

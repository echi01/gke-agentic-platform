mock_provider "google" {
  mock_resource "google_compute_address" {
    defaults = { address = "203.0.113.10" }
  }
}
variables {
  project_id = "demo-blueprint"
  region     = "us-central1"
  name       = "platform-dev"
  dns_name   = "dev.example.com."
}
run "stable_public_dns" {
  command = plan
  assert {
    condition     = google_dns_managed_zone.environment.visibility == "public" && google_dns_managed_zone.environment.dnssec_config[0].state == "on"
    error_message = "The application requires a public Google DNS zone with DNSSEC signing enabled."
  }
  assert {
    condition     = google_dns_record_set.ingress.type == "A" && google_dns_record_set.ingress.name == "dev.example.com."
    error_message = "The DNS record must use the configured fully qualified application hostname."
  }
}
run "reject_unqualified_name" {
  command = plan
  variables { dns_name = "dev.example.com" }
  expect_failures = [var.dns_name]
}

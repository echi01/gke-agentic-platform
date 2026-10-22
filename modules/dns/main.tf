terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 7.0" }
  }
}
variable "project_id" { type = string }
variable "region" { type = string }
variable "name" { type = string }
variable "dns_name" {
  type = string
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]+\\.$", var.dns_name))
    error_message = "Use a fully qualified DNS name with a trailing dot."
  }
}
resource "google_project_service" "dns" {
  project            = var.project_id
  service            = "dns.googleapis.com"
  disable_on_destroy = false
}
resource "google_dns_managed_zone" "environment" {
  project     = var.project_id
  name        = var.name
  dns_name    = var.dns_name
  description = "Environment DNS managed exclusively by Terraform"
  visibility  = "public"
  dnssec_config { state = "on" }
  depends_on = [google_project_service.dns]
  lifecycle { prevent_destroy = true }
}
resource "google_compute_address" "ingress" {
  project      = var.project_id
  region       = var.region
  name         = "${var.name}-ingress"
  address_type = "EXTERNAL"
  network_tier = "PREMIUM"
  lifecycle { prevent_destroy = true }
}
resource "google_dns_record_set" "ingress" {
  project      = var.project_id
  managed_zone = google_dns_managed_zone.environment.name
  name         = var.dns_name
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_address.ingress.address]
}
output "name_servers" { value = google_dns_managed_zone.environment.name_servers }
output "zone_name" { value = google_dns_managed_zone.environment.name }
output "dns_name" { value = var.dns_name }
output "ingress_ip" { value = google_compute_address.ingress.address }
output "ingress_address_name" { value = google_compute_address.ingress.name }

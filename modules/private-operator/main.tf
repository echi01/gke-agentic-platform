terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 7.0" }
  }
}
variable "project_id" { type = string }
variable "name" { type = string }
variable "zone" { type = string }
variable "network_id" { type = string }
variable "subnetwork_id" { type = string }
resource "google_project_service" "access" {
  for_each           = toset(["iap.googleapis.com", "oslogin.googleapis.com"])
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}
resource "google_service_account" "operator" {
  project    = var.project_id
  account_id = "${var.name}-operator"
}
resource "google_compute_firewall" "iap" {
  project       = var.project_id
  name          = "${var.name}-operator-iap"
  network       = var.network_id
  direction     = "INGRESS"
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["${var.name}-operator"]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}
resource "google_compute_instance" "operator" {
  project      = var.project_id
  name         = "${var.name}-operator"
  zone         = var.zone
  machine_type = "e2-micro"
  tags         = ["${var.name}-operator"]
  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 10
      type  = "pd-balanced"
    }
  }
  network_interface { subnetwork = var.subnetwork_id }
  service_account {
    email  = google_service_account.operator.email
    scopes = []
  }
  metadata = {
    enable-oslogin         = "TRUE"
    block-project-ssh-keys = "TRUE"
  }
  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }
  depends_on = [google_project_service.access, google_compute_firewall.iap]
}
output "name" { value = google_compute_instance.operator.name }
output "zone" { value = var.zone }

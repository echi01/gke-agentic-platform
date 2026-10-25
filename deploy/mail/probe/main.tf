terraform {
  required_version = ">= 1.8"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 7.0" }
  }
}
provider "google" {
  project = "project-fb85ba80-c9eb-43f0-af3"
  region  = "us-central1"
}
# Temporary connectivity probe only: no DNS changes, public inbound rules, mailbox,
# cluster, service-account roles or persistent mail server are created here.
resource "google_compute_instance" "smtp_probe" {
  name         = "progressbar-smtp-probe"
  machine_type = "e2-micro"
  zone         = "us-central1-a"
  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 10
      type  = "pd-standard"
    }
  }
  network_interface {
    network = "default"
    access_config {}
  }
  metadata = {
    enable-oslogin         = "TRUE"
    block-project-ssh-keys = "TRUE"
  }
  metadata_startup_script = file("${path.module}/probe.sh")
  labels = {
    application = "progressbar"
    purpose     = "temporary-smtp-egress-check"
  }
}
output "instance_name" { value = google_compute_instance.smtp_probe.name }

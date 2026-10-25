terraform {
  required_version = ">= 1.8"
  required_providers { google = { source = "hashicorp/google", version = "~> 7.0" } }
  backend "gcs" {}
}
locals { env = jsondecode(file("${path.module}/environment.json")) }
provider "google" {
  project = local.env.projectId
  region  = local.env.region
}
resource "google_compute_network" "mail" {
  name                    = "progressbar-mail"
  auto_create_subnetworks = false
}
resource "google_compute_subnetwork" "mail" {
  name                     = "progressbar-mail"
  region                   = local.env.region
  network                  = google_compute_network.mail.id
  ip_cidr_range            = "10.91.0.0/24"
  private_ip_google_access = true
}
resource "google_service_account" "mail" {
  account_id   = "progressbar-mail"
  display_name = "Progress Bar Stalwart server"
}
resource "google_compute_address" "mail" {
  name   = "progressbar-mail"
  region = local.env.region
}
resource "google_compute_firewall" "mail_inbound" {
  name                    = "progressbar-mail-public-protocols"
  network                 = google_compute_network.mail.name
  direction               = "INGRESS"
  source_ranges           = ["0.0.0.0/0"]
  target_service_accounts = [google_service_account.mail.email]
  allow {
    protocol = "tcp"
    ports    = ["25", "443", "465", "587", "993"]
  }
  log_config { metadata = "EXCLUDE_ALL_METADATA" }
}
resource "google_compute_firewall" "iap_ssh" {
  name                    = "progressbar-mail-iap-ssh"
  network                 = google_compute_network.mail.name
  direction               = "INGRESS"
  source_ranges           = ["35.235.240.0/20"]
  target_service_accounts = [google_service_account.mail.email]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}
# This explicitly permits TCP 25 at the VPC firewall. It cannot override a
# separate Google platform restriction, which is checked from the live VM.
resource "google_compute_firewall" "smtp_outbound" {
  name                    = "progressbar-mail-outbound-smtp"
  network                 = google_compute_network.mail.name
  direction               = "EGRESS"
  priority                = 800
  destination_ranges      = ["0.0.0.0/0"]
  target_service_accounts = [google_service_account.mail.email]
  allow {
    protocol = "tcp"
    ports    = ["25", "465", "587"]
  }
  log_config { metadata = "EXCLUDE_ALL_METADATA" }
}
resource "google_secret_manager_secret" "mail" {
  for_each  = toset(["progressbar-mail-bootstrap", "progressbar-mail-hello", "progressbar-mail-admin"])
  secret_id = each.key
  replication {
    auto {}
  }
  lifecycle { prevent_destroy = true }
}
resource "google_secret_manager_secret_iam_member" "bootstrap" {
  for_each  = toset(["progressbar-mail-bootstrap", "progressbar-mail-hello"])
  secret_id = google_secret_manager_secret.mail[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.mail.email}"
}
resource "google_compute_disk" "data" {
  name = "progressbar-mail-data"
  zone = local.env.zone
  type = "pd-standard"
  size = 20
  lifecycle { prevent_destroy = true }
}
resource "google_compute_resource_policy" "snapshots" {
  name   = "progressbar-mail-daily"
  region = local.env.region
  snapshot_schedule_policy {
    schedule {
      daily_schedule {
        days_in_cycle = 1
        start_time    = "07:00"
      }
    }
    retention_policy {
      max_retention_days    = 7
      on_source_disk_delete = "KEEP_AUTO_SNAPSHOTS"
    }
    snapshot_properties {
      storage_locations = [local.env.region]
      labels            = { application = "progressbar-mail" }
    }
  }
}
resource "google_compute_disk_resource_policy_attachment" "daily" {
  name = google_compute_resource_policy.snapshots.name
  disk = google_compute_disk.data.name
  zone = local.env.zone
}
resource "google_compute_instance" "mail" {
  name                      = "progressbar-mail"
  zone                      = local.env.zone
  machine_type              = local.env.machineType
  allow_stopping_for_update = true
  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 10
      type  = "pd-standard"
    }
  }
  attached_disk {
    source      = google_compute_disk.data.id
    device_name = "mail-data"
  }
  network_interface {
    subnetwork = google_compute_subnetwork.mail.id
    access_config {
      nat_ip                 = google_compute_address.mail.address
      public_ptr_domain_name = "${local.env.hostname}."
    }
  }
  service_account {
    email  = google_service_account.mail.email
    scopes = ["cloud-platform"]
  }
  metadata = {
    enable-oslogin         = "TRUE"
    block-project-ssh-keys = "TRUE"
    mail-project           = local.env.projectId
    mail-hostname          = local.env.hostname
    mail-domain            = local.env.domain
    mail-image             = local.env.image
    mail-configure         = filebase64("${path.module}/scripts/configure.py")
  }
  metadata_startup_script = file("${path.module}/scripts/startup.sh")
  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }
  labels = { application = "progressbar"
    component = "mail"
  environment = "production" }
  depends_on = [google_secret_manager_secret_iam_member.bootstrap, google_dns_record_set.mail_host]
}
output "server" { value = { name = google_compute_instance.mail.name, zone = local.env.zone, address = google_compute_address.mail.address, hostname = local.env.hostname, data_disk = google_compute_disk.data.name } }
resource "google_dns_record_set" "mail_host" {
  managed_zone = "progressbar-public"
  name         = "${local.env.hostname}."
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_address.mail.address]
}
# Public-only keys exported from the actual server. Root MX/TXT keep their
# existing owner in deploy/dev/dns; this map cannot replace the website records.
locals {
  public_mail_records = jsondecode(file("${path.module}/public-dns.json"))
}
resource "google_dns_record_set" "mail_public" {
  for_each     = local.public_mail_records
  managed_zone = "progressbar-public"
  name         = each.value.name
  type         = each.value.type
  ttl          = each.value.ttl
  rrdatas      = each.value.rrdatas
  lifecycle {
    precondition {
      condition     = each.value.type == "TXT" && (endswith(each.value.name, "._domainkey.${local.env.domain}.") || each.value.name == "${local.env.hostname}.")
      error_message = "Only this server's public DKIM and hostname SPF records belong in this map."
    }
  }
}
resource "google_project_iam_member" "mail_logs" {
  project = local.env.projectId
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.mail.email}"
}

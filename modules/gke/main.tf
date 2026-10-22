terraform {
  required_version = ">= 1.8"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 7.0" }
  }
}

variable "name_prefix" {
  type    = string
  default = "platform"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,15}$", var.name_prefix))
    error_message = "Use a short lowercase platform prefix."
  }
}
variable "project_id" {
  type = string
}
variable "region" {
  type = string
}
variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Use dev, staging or prod."
  }
}
variable "zones" {
  type = list(string)
  validation {
    condition     = length(var.zones) >= 2
    error_message = "Use at least two zones for regional node placement."
  }
}
variable "cpu_min_nodes" {
  type = number
}
variable "cpu_max_nodes" {
  type = number
}
variable "machine_type" {
  type = string
}
variable "enable_gpu" {
  type = bool
}
variable "gpu_machine_type" {
  type = string
}
variable "gpu_type" {
  type = string
}
variable "gpu_max_nodes" {
  type = number
}
variable "deletion_protection" {
  type = bool
}
variable "pod_cidr" {
  type = string
}
variable "service_cidr" {
  type = string
}
variable "node_cidr" {
  type = string
}
variable "master_cidr" {
  type = string
}

locals {
  name     = "${var.name_prefix}-${var.environment}"
  services = toset(["container.googleapis.com", "compute.googleapis.com", "iam.googleapis.com", "artifactregistry.googleapis.com", "secretmanager.googleapis.com", "monitoring.googleapis.com", "logging.googleapis.com", "aiplatform.googleapis.com"])
}
resource "google_project_service" "required" {
  for_each           = local.services
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}
resource "google_compute_network" "main" {
  project                 = var.project_id
  name                    = local.name
  auto_create_subnetworks = false
  depends_on              = [google_project_service.required]
}
resource "google_compute_subnetwork" "nodes" {
  project                  = var.project_id
  name                     = local.name
  region                   = var.region
  network                  = google_compute_network.main.id
  ip_cidr_range            = var.node_cidr
  private_ip_google_access = true
  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.pod_cidr
  }
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.service_cidr
  }
}
resource "google_compute_router" "main" {
  project = var.project_id
  name    = local.name
  region  = var.region
  network = google_compute_network.main.id
}
resource "google_compute_router_nat" "egress" {
  project                            = var.project_id
  name                               = local.name
  router                             = google_compute_router.main.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"
  subnetwork {
    name                    = google_compute_subnetwork.nodes.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }
  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}
resource "google_service_account" "nodes" {
  project    = var.project_id
  account_id = "${local.name}-nodes"
  depends_on = [google_project_service.required]
}
resource "google_project_iam_member" "node_runtime" {
  project = var.project_id
  role    = "roles/container.defaultNodeServiceAccount"
  member  = "serviceAccount:${google_service_account.nodes.email}"
}
resource "google_artifact_registry_repository" "images" {
  project       = var.project_id
  location      = var.region
  repository_id = local.name
  format        = "DOCKER"
  depends_on    = [google_project_service.required]
}
resource "google_artifact_registry_repository_iam_member" "node_pull" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.nodes.email}"
}
resource "google_container_cluster" "main" {
  project                  = var.project_id
  name                     = local.name
  location                 = var.region
  node_locations           = var.zones
  network                  = google_compute_network.main.id
  subnetwork               = google_compute_subnetwork.nodes.id
  remove_default_node_pool = true
  initial_node_count       = 1
  deletion_protection      = var.deletion_protection
  networking_mode          = "VPC_NATIVE"
  datapath_provider        = "ADVANCED_DATAPATH"
  enable_shielded_nodes    = true
  release_channel { channel = "REGULAR" }
  workload_identity_config { workload_pool = "${var.project_id}.svc.id.goog" }
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = true
    master_ipv4_cidr_block  = var.master_cidr
  }
  master_authorized_networks_config {
    private_endpoint_enforcement_enabled = true
    cidr_blocks {
      cidr_block   = var.node_cidr
      display_name = "private-node-and-runner-subnet"
    }
    cidr_blocks {
      cidr_block   = var.pod_cidr
      display_name = "private-workload-subnet"
    }
  }
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }
  master_auth {
    client_certificate_config { issue_client_certificate = false }
  }
  database_encryption { state = "DECRYPTED" }
  logging_config { enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"] }
  monitoring_config {
    managed_prometheus { enabled = true }
  }
  security_posture_config {
    mode               = "BASIC"
    vulnerability_mode = "VULNERABILITY_BASIC"
  }
  gateway_api_config { channel = "CHANNEL_STANDARD" }
  maintenance_policy {
    daily_maintenance_window { start_time = "03:00" }
  }
  lifecycle {
    precondition {
      condition     = var.cpu_min_nodes >= 1 && var.cpu_max_nodes >= var.cpu_min_nodes
      error_message = "CPU node bounds must be ordered and keep at least one node."
    }
    precondition {
      condition     = var.environment != "prod" || (var.cpu_min_nodes >= 3 && var.deletion_protection)
      error_message = "Production requires at least three CPU nodes and deletion protection."
    }
  }
  depends_on = [google_project_service.required, google_compute_router_nat.egress]
}
resource "google_container_node_pool" "cpu" {
  project            = var.project_id
  name               = "cpu"
  location           = var.region
  cluster            = google_container_cluster.main.name
  node_locations     = var.zones
  initial_node_count = 1
  autoscaling {
    total_min_node_count = var.cpu_min_nodes
    total_max_node_count = var.cpu_max_nodes
    location_policy      = "BALANCED"
  }
  management {
    auto_repair  = true
    auto_upgrade = true
  }
  node_config {
    machine_type    = var.machine_type
    service_account = google_service_account.nodes.email
    oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]
    image_type      = "COS_CONTAINERD"
    disk_size_gb    = 50
    labels          = { "workload-class" = "cpu" }
    workload_metadata_config { mode = "GKE_METADATA" }
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
    metadata = { "disable-legacy-endpoints" = "true" }
  }
  depends_on = [google_project_iam_member.node_runtime, google_artifact_registry_repository_iam_member.node_pull]
}
resource "google_container_node_pool" "gpu" {
  count              = var.enable_gpu ? 1 : 0
  project            = var.project_id
  name               = "gpu"
  location           = var.region
  cluster            = google_container_cluster.main.name
  node_locations     = var.zones
  initial_node_count = 0
  autoscaling {
    total_min_node_count = 0
    total_max_node_count = var.gpu_max_nodes
    location_policy      = "ANY"
  }
  management {
    auto_repair  = true
    auto_upgrade = true
  }
  node_config {
    machine_type    = var.gpu_machine_type
    service_account = google_service_account.nodes.email
    oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]
    image_type      = "COS_CONTAINERD"
    disk_size_gb    = 100
    labels          = { "workload-class" = "gpu" }
    taint {
      key    = "nvidia.com/gpu"
      value  = "present"
      effect = "NO_SCHEDULE"
    }
    guest_accelerator {
      type  = var.gpu_type
      count = 1
      gpu_driver_installation_config { gpu_driver_version = "DEFAULT" }
    }
    workload_metadata_config { mode = "GKE_METADATA" }
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
    metadata = { "disable-legacy-endpoints" = "true" }
  }
}
output "cluster_name" { value = google_container_cluster.main.name }
output "region" { value = var.region }
output "registry" { value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}" }
output "private_endpoint" { value = google_container_cluster.main.private_cluster_config[0].private_endpoint }

output "network_id" { value = google_compute_network.main.id }
output "subnetwork_id" { value = google_compute_subnetwork.nodes.id }

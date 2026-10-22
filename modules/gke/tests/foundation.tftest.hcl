mock_provider "google" {}
variables {
  project_id          = "demo-blueprint"
  region              = "us-central1"
  environment         = "dev"
  zones               = ["us-central1-a", "us-central1-b"]
  cpu_min_nodes       = 1
  cpu_max_nodes       = 3
  machine_type        = "e2-standard-4"
  enable_gpu          = false
  gpu_machine_type    = "g2-standard-4"
  gpu_type            = "nvidia-l4"
  gpu_max_nodes       = 1
  deletion_protection = true
  pod_cidr            = "10.44.0.0/14"
  service_cidr        = "10.48.0.0/20"
  node_cidr           = "10.40.0.0/20"
  master_cidr         = "172.16.0.0/28"
}
run "private_identity_enabled_foundation" {
  command = plan
  assert {
    condition     = google_container_cluster.main.private_cluster_config[0].enable_private_nodes && google_container_cluster.main.private_cluster_config[0].enable_private_endpoint && google_container_cluster.main.workload_identity_config[0].workload_pool == "demo-blueprint.svc.id.goog"
    error_message = "Cluster must have private nodes/control plane and federated identity."
  }
  assert {
    condition     = google_container_cluster.main.datapath_provider == "ADVANCED_DATAPATH" && length(google_container_node_pool.gpu) == 0
    error_message = "Enforce network policy; do not allocate GPU pools by default."
  }
}
run "optional_gpu_capacity" {
  command = plan
  variables { enable_gpu = true }
  assert {
    condition     = google_container_node_pool.gpu[0].autoscaling[0].total_min_node_count == 0 && google_container_node_pool.gpu[0].node_config[0].guest_accelerator[0].count == 1
    error_message = "GPU pool must be explicit, bounded, and scale from zero."
  }
}
run "reject_inverted_capacity" {
  command = plan
  variables { cpu_max_nodes = 0 }
  expect_failures = [google_container_cluster.main]
}
run "reject_underprovisioned_production" {
  command = plan
  variables { environment = "prod" }
  expect_failures = [google_container_cluster.main]
}

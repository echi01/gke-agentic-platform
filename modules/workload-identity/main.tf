terraform {
  required_providers { google = { source = "hashicorp/google", version = "~> 7.0" } }
}
variable "project_id" {
  type = string
}
variable "account_id" {
  type = string
}
variable "namespace" {
  type = string
}
variable "kubernetes_service_account" {
  type = string
}
variable "project_roles" {
  type    = set(string)
  default = []
}
resource "google_service_account" "workload" {
  project    = var.project_id
  account_id = var.account_id
}
resource "google_service_account_iam_member" "federation" {
  service_account_id = google_service_account.workload.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[${var.namespace}/${var.kubernetes_service_account}]"
}
resource "google_project_iam_member" "roles" {
  for_each = var.project_roles
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.workload.email}"
}
output "gitops_config" {
  value = { namespace = var.namespace, serviceAccount = var.kubernetes_service_account,
  annotations = { "iam.gke.io/gcp-service-account" = google_service_account.workload.email } }
}

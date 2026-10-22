# prod: backend

Create and protect Terraform state storage.

This is an independent Terraform root. Copy its example configuration locally and follow the shared [deployment runbook](../../../docs/deployment.md). Use a reviewed saved plan and this stage's distinct state prefix. Prerequisites follow the order backend → gke → addons → workloads.

mock_provider "helm" {}
variables {
  repository_url = "https://github.com/example/platform.git"
  revision       = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  enabled_addons = { kubernetes-mcp = false }
}
run "gitops_handoff" {
  command = plan
  assert {
    condition     = length(helm_release.addons_parent) == 1 && output.gitops_configuration.addons["cert-manager"].path == "vendor/helm/cert-manager/v1.21.2/cert-manager"
    error_message = "Enabled integrations must hand local chart paths to the add-ons parent."
  }
}
run "direct_installation_has_no_gitops_parent" {
  command = plan
  variables { manage_via_gitops = false }
  assert {
    condition     = length(helm_release.addons_parent) == 0 && length(output.gitops_configuration.addons) == 0
    error_message = "Direct Terraform mode must not also create GitOps owners."
  }
}

run "reject_unknown_addon" {
  command = plan
  variables { enabled_addons = { unknown-addon = true } }
  expect_failures = [var.enabled_addons]
}
run "reject_incomplete_mesh_profile" {
  command = plan
  variables { enabled_addons = { istio-cni = false, kubernetes-mcp = false } }
  expect_failures = [terraform_data.profile]
}

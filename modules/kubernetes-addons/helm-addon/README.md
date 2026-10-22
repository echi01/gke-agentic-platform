# Shared Helm add-on contract

Direct mode creates a Helm release from `chart_path`. GitOps mode creates no Helm release and returns its local Git path, values, namespace, release name and sync wave. Disabled modules return no handoff. Chart source and version come from the reviewed root lock.

Individual modules own defaults and overrides; infrastructure compositions select modules and aggregate outputs. Identity annotations can be prepared by `modules/workload-identity` and passed explicitly into chart values. No application code or secret payload belongs in this helper.

Choose installation ownership before deployment; see the migration procedure before changing it for a live release.

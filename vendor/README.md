# Locally stored upstream chart source

`helm/` contains the selected chart source and recursively expanded chart dependencies. It is committed source, not an ignored Helm/Terraform cache. Neither deployment mode downloads chart source at deployment time. Kubernetes still pulls the chart-selected container images; an air-gapped deployment additionally needs an image mirror.

`addons.lock.json` records official origins, versions, original archive checksums, local paths and expanded-tree hashes. Run `scripts/verify-vendor.py` before release. Preserve upstream notices; make integration changes in module values rather than editing vendor source silently. The lock establishes the reviewed bytes, not a claim that every upstream controller has passed production security qualification.

For an upgrade, use `scripts/vendor-chart.py --name NAME --version VERSION --archive-sha256 REVIEWED_SHA256`. It imports and expands the new source, updates the lock and moves the previous version into ignored local history. Module paths/versions follow the lock. Review values, tests and compatibility before committing.

# Temporary Google SMTP egress probe

This Terraform state is separate from the retired GKE platform and the website/DNS state. It creates one temporary e2-micro VM, tests TCP connectivity to actual external SMTP endpoints and two controls, and emits `PB_SMTP_PROBE_RESULT` on serial output. It never sends email. Destroy it immediately after collecting the result. No mailbox service is installed unless direct outbound delivery is viable or a relay is explicitly chosen.

Run with the project's existing authenticated Google identity; inject `GOOGLE_OAUTH_ACCESS_TOKEN` into the Terraform process environment without printing it. Use `.tools/terraform init`, `plan`, and `apply` in this directory, then read serial output with `gcloud compute instances get-serial-port-output progressbar-smtp-probe --zone=us-central1-a --project=project-fb85ba80-c9eb-43f0-af3`. Finally run Terraform destroy here.

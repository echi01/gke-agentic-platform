# Google Cloud DNS through Terraform

The `modules/dns` module owns the public `dev.progressbar.vip.` zone, its A record, DNS API activation and reserved regional load-balancer address. Inputs come from the committed `deploy/dev/environment.json`. State uses the committed `backend.config` in this directory.

The add-on stage reads the reserved address resource name from this stage's remote-state output and attaches it to Traefik's Google LoadBalancer Service. The A record therefore stays stable when application pods, nodes or ingress deployments change.

Run the committed entry point from the infrastructure checkout:

```sh
python scripts/deploy-dev.py --stage dns --apply
```

Terraform owns the DNS record; no DNS controller owns or mutates it. Cert-manager and Let's Encrypt own certificate issuance/renewal independently.

## Public activation

Terraform now also owns `progressbar-public`, the parent `progressbar.vip.` zone. `parent-records.json` preserves the eleven existing website, mail and verification records in six record sets. `parent.tf` delegates `dev.progressbar.vip.` from that Google parent zone to the Google dev zone.

The new parent authoritative servers are `ns-cloud-c1.googledomains.com` through `ns-cloud-c4.googledomains.com`. All preserved records have been verified directly against Google. Public activation still requires the separate `deploy/dev/registrar` Terraform stage to change Namecheap's nameservers. That registrar stage requires API access and an allowlisted execution IP. No external DNS controller or Cloudflare credential is used.

## Verification

The Google DNS record and reserved address have been applied through Terraform. A subsequent real plan reports no changes. An independent query to Google's authoritative nameservers returns the same address as the reserved Compute Engine address. The DNS module also checks fully qualified names with mocked Terraform plans. The existing public website's content is unchanged.

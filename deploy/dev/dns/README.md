# Google Cloud DNS through Terraform

The `modules/dns` module owns the public `dev.progressbar.vip.` zone, its A record, DNS API activation and reserved regional load-balancer address. Inputs come from the committed `deploy/dev/environment.json`. State uses the committed `backend.config` in this directory.

The add-on stage reads the reserved address resource name from this stage's remote-state output and attaches it to Traefik's Google LoadBalancer Service. The A record therefore stays stable when application pods, nodes or ingress deployments change.

Run the committed entry point from the infrastructure checkout:

```sh
python scripts/deploy-dev.py --stage dns --apply
```

Terraform owns the DNS record; no DNS controller owns or mutates it. Cert-manager and Let's Encrypt own certificate issuance/renewal independently.

## Public activation

The Google zone is created and can be queried through the Google authoritative nameservers in `dns.name_servers`. It becomes publicly authoritative only after delegation is configured upstream. The existing website's DNS and registrar configuration have not been changed by this stage. A move of the parent domain must preserve its existing website/mail records and be handled as an explicit registrar migration; it is not performed as a side effect of creating the dev zone.

## Verification

The Google DNS record and reserved address have been applied through Terraform. A subsequent real plan reports no changes. An independent query to Google's authoritative nameservers returns the same address as the reserved Compute Engine address. The DNS module also checks fully qualified names with mocked Terraform plans. The existing public website's content is unchanged.

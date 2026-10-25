# Progress Bar self-hosted mail

Stalwart Community on a dedicated Google Compute Engine VM. No Google Workspace subscription, external relay account, GKE cluster, cloud load balancer or landing-page redeployment is part of this root.

## Ownership and resources

`environment.json` selects the Google project, region, zone, hostname and immutable upstream image. Terraform uses the existing protected GCS state bucket with the independent prefix `production/mail`.

- Dedicated VPC/subnet and service identity.
- e2-small VM, separate protected 20-GB mail-data disk, 10-GB boot disk.
- Static address and `mail.progressbar.vip` A/PTR.
- Public TCP 25, 443, 465, 587 and 993, targeted only at the mail VM identity.
- SSH only through IAP; setup port 8080 is not publicly allowed.
- Explicit egress SMTP allow rule at priority 800. Google's separate platform restriction may still block outbound 25.
- Daily incremental disk snapshot schedule, seven-day retention. These are crash-consistent snapshots; no claim of a tested production restore is made.
- Secret Manager secret metadata and narrowly scoped bootstrap access. Payloads are injected outside Terraform state and never enter Git/VM metadata.

The VM, public IP, storage, snapshots and logs are billable Google resources, eligible for applicable available Cloud credits. It is not a zero-cost hosting claim. A single VM is an MVP mailbox deployment, not a high-availability mail cluster.

## Apply and converge

```sh
python3 deploy/mail/server/scripts/deploy.py
python3 deploy/mail/server/scripts/refresh.py
python3 deploy/mail/server/scripts/verify.py
```

`deploy.py` initializes Terraform, validates and reviews a plan, rejects destructive/replacement changes, applies this root, then retains credentials in Secret Manager without logging their payloads. `refresh.py` loads the applied configuration script from VM metadata over an authenticated IAP connection. It refuses to interrupt a running configuration operation.

The startup script mounts the persistent disk, starts Docker and runs the configuration service. The configuration script uses Stalwart's actual `x:Bootstrap`, `x:Account`, `x:Domain` and `x:NetworkListener` JMAP methods. It creates an owner mailbox `hello@progressbar.vip` with `support@`, `postmaster@` and `abuse@` aliases. `admin@` is a separate administrator. Unknown recipients are not catch-all relayed.

The public server starts without the recovery credential environment. Mailbox clients require TLS. Unused plaintext IMAP/POP3 and setup HTTP listeners are removed. The official pinned Stalwart image requires a modern OCI-capable engine; the script upgrades Debian 12's old Docker from Docker's signed official APT repository if needed. It also disables the fresh host image's loopback Exim service to prevent a port-25 binding conflict.

The active credentials are in Google Secret Manager:

- `progressbar-mail-admin`: administrative connection JSON.
- `progressbar-mail-hello`: owner mailbox password.
- `progressbar-mail-bootstrap`: protected bootstrap/recovery credential, also used for the converged admin credential; never present in the final container environment.

Treat `deploy.py`/IAP access as administrator operations. Customers and product agents must not receive these permissions.

## Client connection

- Host: `mail.progressbar.vip`
- Username: `hello@progressbar.vip`
- Incoming: IMAP 993, implicit TLS.
- Outgoing: SMTP 465, implicit TLS, or 587 with required STARTTLS and password authentication.
- Aliases reach that same inbox.
- Administrative interface: `https://mail.progressbar.vip/admin`.

## DNS and activation

The mail host A record is owned by this root. Root MX and SPF remain owned by `deploy/dev/dns`; do not introduce duplicate Terraform ownership. DKIM public records and hostname SPF are exported to `public-dns.json` and applied by this root. The existing DNS root now points MX to `mail.progressbar.vip`, authorizes its exact IP in SPF and publishes DMARC in monitoring mode. Firebase A/CNAME and verification records are preserved. Generated DKIM keys are held in manual management after creation, so future automatic rotation cannot silently invalidate Terraform-owned DNS; rotate keys and committed DNS together.

Incoming-mail cutover and external outbound delivery are separate. Public listeners and an SPF record do not prove internet delivery. See committed evidence for exactly which checks passed. No outside recipient was approved for a test message; live self-checks send only between this server's own mailbox and alias.

## Source and licence

Pinned upstream: `stalwartlabs/stalwart` tag v0.16.27, image digest in `environment.json`. Official source was inspected locally under ignored `.local/mail/stalwart`. Stalwart Community retains its upstream AGPL/alternative-licence terms; our orchestration does not change the server source.

References:

- https://www.stalw.art/docs/install/platform/docker/
- https://www.stalw.art/docs/configuration/declarative-deployments/
- https://docs.cloud.google.com/compute/docs/tutorials/sending-mail
- https://docs.cloud.google.com/firewall/docs/firewalls#blockedtraffic
- https://docs.docker.com/engine/install/debian/

## Deployed acceptance — 25 October 2026

Server: `34.59.12.60`, hostname `mail.progressbar.vip`. The public Let's Encrypt certificate is verified and expires 23 January 2027; Stalwart retains automatic certificate management. A bootstrap-interrupted ACME task was replaced after all final listeners were running. The configuration code handles this same initial certificate setup condition on subsequent clean deployments.

Live evidence is in `evidence/live-mail.json` and `evidence/dns-and-website.json`: all five public ports reachable; setup 8080 closed; authenticated submission delivered to the support alias; IMAP retrieved the message; unauthenticated external relay and wrong-password login were rejected. Authoritative Google DNS contains the new MX/SPF/DKIM/DMARC records, and the public landing page still returned HTTP 200. Self-checks contain no outside recipients. An external provider-to-inbox delivery and a snapshot restore have not been tested.

**Remaining provider block:** connections from this VM to Gmail and Yahoo destination TCP 25 time out, while 587 and HTTPS succeed. The explicit Google VPC egress rule is already applied. Google platform SMTP policy cannot be overridden by that rule. Incoming hosting and local mailbox delivery work; outgoing internet mail is not operational. It requires an allowed authenticated outbound relay on 465/587 or Google's removal of its project-level restriction. This deployment does not purchase Google Workspace or silently sign up for a relay.

Connection credentials are retained in Secret Manager. `python3 deploy/mail/server/scripts/export-access.py` writes them to the operator's ignored, mode-0600 `.local/mail/connection-details.json`. Do not commit, paste into chat, or expose that file to product agents. Use an IMAP client such as the phone's mail app; `/admin` is the server administration interface, not a claim of an installed webmail client.

The existing Namecheap forwarding MX records were replaced only after live mailbox checks passed. Account names other than the listed mailbox and aliases are not configured and will be rejected. The committed previous version of `deploy/dev/dns/parent-records.json` records the earlier forwarding setup.

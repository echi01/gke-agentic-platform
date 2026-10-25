# Branded Progress Bar mail — Google Cloud feasibility

The user requested open-source mail hosting on Google Cloud for branded `@progressbar.vip` sending and receiving, funded by Cloud credit rather than a Workspace subscription.

## Live result: direct outbound delivery is blocked

On 25 October 2026, Terraform created a temporary e2-micro Debian VM in this actual project. From that VM:

- `smtp.gmail.com:587` connected.
- `www.google.com:443` connected.
- Gmail MX, Google Workspace MX and Yahoo MX on port 25 all timed out.
- No explicit VPC egress firewall rule was present on the default network. The result is consistent with Google's documented default restriction on external SMTP port 25.

Raw receipt: `probe/evidence/2026-10-25-connectivity.json`. Terraform destroyed the probe afterwards: **1 created, 1 destroyed**. No DNS records, mailbox accounts, GKE resources, load balancers or persistent server were created. The existing landing page remains unchanged.

The VM only opened TCP connections; it sent no email. This tests network feasibility, not mailbox delivery or sender reputation.

## Viable architecture

Stalwart Community Edition on a small persistent Google VM can provide SMTP submission, IMAP/JMAP, local mailboxes, DKIM signing and ACME TLS. A dedicated public IP, `mail.progressbar.vip` A/PTR records, root MX, SPF, DKIM and DMARC are part of a real deployment. Google credits can cover eligible compute/disk/IP charges. They do not cover Google Workspace subscriptions.

While the project restriction remains, internet delivery needs an authenticated outbound relay on port 587/465. A free-tier relay is an option; provider approval, quota and account configuration must be checked. Without that relay or Google lifting the block, do not deploy an inbound-only server and call sending complete. Do not change the domain's MX until the chosen mailbox service is ready to receive mail.

The user has been asked to choose between self-hosted Stalwart plus a free outbound relay, or waiting for Google to lift the restriction. No relay account, subscription or support request was created.

Mailcheap currently supports SES and PostShiba rather than arbitrary SMTP. Connecting it to a self-hosted mail server requires a real provider/SMTP integration; merely changing a URL is not sufficient. The application repository's working Mailcheap integration is currently draft-only.

## Reproduce the temporary check

From the infrastructure repository root, with the pinned Terraform provider and a Terraform binary available:

```sh
python3 deploy/mail/probe/run.py
```

This invokes Terraform init, validate, plan, apply, observes the serial receipt, and destroys the instance in `finally`. Credentials are injected into the process environment, not placed in Git. This intentionally uses a separate local state for a disposable probe; persistent production mail infrastructure needs the repository's remote-state/IaC pattern.

## Official references

- [Google: sending email from an instance](https://docs.cloud.google.com/compute/docs/tutorials/sending-mail)
- [Google: SMTP port 25 restrictions](https://docs.cloud.google.com/firewall/docs/firewalls)
- [Stalwart Community Edition](https://stalw.art/open-source/)
- [Stalwart Docker deployment](https://www.stalw.art/docs/install/platform/docker/)
- [Stalwart outbound routing](https://stalw.art/docs/mta/outbound/routing/)
- [Brevo free-plan limits](https://help.brevo.com/hc/en-us/articles/208580669-FAQs-What-are-the-limits-of-the-Free-plan)

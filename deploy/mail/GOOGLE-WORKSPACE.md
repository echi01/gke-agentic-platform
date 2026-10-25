# Historical Google Workspace alternative — not selected

User steering on 25 October 2026: use Google's email service rather than Brevo. No Brevo account was created, no mailbox VM was provisioned, and no domain records changed during this investigation. The official Stalwart source/image were downloaded locally for evaluation only.

Google Workspace provides real branded Gmail mailboxes. This is separate from hosting Stalwart on Compute Engine. Business Starter's published US standard pricing is $8.40/user/month on the flexible plan (no annual commitment), or $7/user/month with an annual commitment, before tax. A 14-day trial is advertised; introductory offers and final checkout prices may differ. Workspace billing is separate from the Google Cloud trial-credit account.

Superseded: the user clarified they want an open-source server on Google Cloud, not Google Workspace. No paid Workspace route is authorized. Do not create a subscription, accept terms, enter payment details or switch MX while this choice is pending. The user's answer “no. real” to the test-email question does not identify or authorize a test recipient. No external test email is authorized by that answer.

## Proposed activation

1. One owner mailbox; choose its address with the user. Extra aliases may share that inbox, rather than buying extra mailboxes.
2. Use the intended Progress Bar contact identity (`pb.simon.chi@gmail.com`) for recovery/contact; do not silently use another browser's selected Google account.
3. Verify ownership with the exact Google-provided TXT token. DNS stays managed through Terraform in the existing `deploy/dev/dns` state, which already owns the root MX and TXT resources. Do not create a second Terraform owner for those records.
4. After the account and mailbox are provisioned, update the existing root MX record to the values provided by Google. Google's current setup commonly uses priority 1 `smtp.google.com.`; the actual Admin Console instruction is authoritative.
5. Update the existing single SPF record for the chosen sending services while retaining the unrelated Firebase verification TXT. Generate Google's DKIM public key, commit/publish it through Terraform, then activate signing. Add DMARC after checking the sender setup.
6. Verify Gmail login and receive/send behavior using specifically authorized recipient addresses. Inspect message headers for aligned DKIM/DMARC; DNS publication alone is not an end-to-end test.
7. Connect the campaign application separately using an approved delivery integration. Its current Mailcheap upstream supports SES/PostShiba and draft-only MCP; Workspace credentials cannot simply be dropped into that configuration.

The Firebase landing-page A/CNAME and existing certificate-verification records must remain intact. A mailbox subscription is not an unrestricted bulk-advertising service; campaign quotas and delivery integration need their own acceptance.

## References checked

- https://workspace.google.com/pricing?hl=en&region=US
- https://knowledge.workspace.google.com/admin/billing/compare-flexible-and-annual-fixed-term-payment-plans
- https://knowledge.workspace.google.com/admin/billing/set-up-google-workspace-billing
- https://docs.cloud.google.com/compute/docs/tutorials/sending-mail
- https://support.google.com/a/answer/176600

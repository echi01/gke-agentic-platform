# Retiring the Google dev environment

The committed `deploy/dev/environment.json` profile has `runtimeEnabled: false`.
The normal deployment entry point refuses to recreate the dev runtime. This does
not disable the Google project or the independent Firebase marketing website.

## Ordered teardown

1. Commit and push the disabled profile and teardown code.
2. Run `scripts/retire-dev.py --apply --backup-directory <private-local-directory>`.
   It backs up Terraform state, audits saved plans, clears the dev cluster's
   deletion protection, removes workload/add-on Helm releases, cleans aggregated
   APIs served by retiring namespaces, removes bootstrap namespaces and workflow
   identities, destroys compute/networking/registry, then removes dev deploy keys
   and dashboard secrets. GitHub repositories remain protected.
3. Apply the DNS root normally. With the runtime disabled it deletes only the dev
   child zone and delegation. The `progressbar-public` parent zone, website/mail
   records and registrar remain protected. This root must never be blanket-destroyed.
4. After the cluster is gone, run the application repository's
   `scripts/retire-cloud-dev.py --apply --backup-directory <private-local-directory>`.
   It exports the isolated database and private bucket before targeted retirement.
   Shared Firebase Authentication remains in its Terraform state.
5. Verify actual Google inventories, empty runtime Terraform states and a fresh
   HTTPS response/content hash from the public website. Record the result before
   marking the lifecycle destroyed.

Both scripts require an explicit apply flag. Plans, state and exported test data
belong in a private local directory, never in Git. The scripts use the configured
Google account without changing unrelated application-default credentials.

## Resources retained for the live website

- Firebase Hosting site and its Google-managed certificate.
- Google Cloud DNS parent zone and Namecheap delegation.
- Installer download bucket.
- Private Terraform state bucket and registrar credential in Secret Manager.
- Shared Firebase Authentication configuration and existing accounts.

Retained DNS/storage/hosting/secret usage can still incur charges. Deleting dev
compute does not make the entire Google account free. Billing reports and trial
credit balances can lag resource use; record observed amounts as provisional.

## Local reference cleanup

Only the local `aws-blueprint` reference checkout was selected for removal. A
verified Git bundle preserves its history privately. No remote GitHub repository
is deleted by the retirement scripts.

## Recreating a cloud test later

Re-enable the runtime in a reviewed commit, restore protected dev-data defaults,
then use the ordered bootstrap. Workflow federation and deploy keys must be
bootstrapped again by an authorized operator; they are deliberately removed on
retirement. Continue routine functional development on the laptop until another
cloud deployment is requested.

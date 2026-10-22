# Registrar delegation to Google

This separate Terraform stage adopts the existing registered domain and manages only its custom authoritative nameservers. Google Cloud DNS owns all records. It does not buy, transfer, cancel or renew the domain.

Prerequisite: Namecheap API access must already be enabled and the execution IPv4 address allowlisted. Supply `NAMECHEAP_USER_NAME`, `NAMECHEAP_API_USER`, `NAMECHEAP_API_KEY` and `NAMECHEAP_CLIENT_IP` through the execution environment. Never put credentials in files committed to Git, command arguments or logs.

Apply the Google DNS root first. Verify every preserved public record directly against Google's new parent authoritative nameservers before this stage. Initialize with `-backend-config=backend.config`, review a saved plan and apply that plan. The import block adopts the existing domain; the planned update must change only nameservers. Public resolver caches may continue using the previous nameservers until their delegation TTL expires.

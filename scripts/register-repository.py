"""Bootstrap private Argo repository credentials from Google Secret Manager via stdin."""
import argparse, json, subprocess
p=argparse.ArgumentParser();p.add_argument("--context",required=True);p.add_argument("--kubeconfig",required=True);p.add_argument("--account",required=True);p.add_argument("--project",required=True);p.add_argument("--secret",required=True);p.add_argument("--repository",required=True);p.add_argument("--name",default="platform-git");p.add_argument("--apply",action="store_true");a=p.parse_args()
if not a.apply:
 print("Preview: read the named Secret Manager secret and create/update one Argo repository Secret in the explicit context. No credentials read.");raise SystemExit(0)
# Secret payload is a JSON object containing username/password or sshPrivateKey.
payload=subprocess.check_output(["gcloud","secrets","versions","access","latest","--secret",a.secret,"--project",a.project,"--account",a.account],text=True)
credentials=json.loads(payload)
if not isinstance(credentials,dict) or not credentials or not set(credentials)<= {"username","password","sshPrivateKey"}:raise SystemExit("Unexpected credential schema")
if not (credentials.get("sshPrivateKey") or (credentials.get("username") and credentials.get("password"))):raise SystemExit("Incomplete repository credentials")
secret={"apiVersion":"v1","kind":"Secret","metadata":{"name":a.name,"namespace":"argocd","labels":{"argocd.argoproj.io/secret-type":"repository"}},"stringData":{"type":"git","url":a.repository,**credentials}}
# server-side avoids storing a duplicate credential in the last-applied annotation.
result=subprocess.run(["kubectl","--kubeconfig",a.kubeconfig,"--context",a.context,"apply","--server-side","--field-manager=platform-repository-bootstrap","-f","-"],input=json.dumps(secret),text=True,capture_output=True)
if result.returncode:raise SystemExit("Repository credential bootstrap failed; inspect the cluster privately.")
print("Repository credential configured; payload was not printed or written locally.")

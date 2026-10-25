"""Reload the committed configuration script from applied VM metadata through IAP."""
import json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[4];E=json.loads((ROOT/'deploy/mail/server/environment.json').read_text());key=ROOT/'.local/mail/iap-key'
command="pid=$(sudo systemctl show progressbar-mail-configure -p MainPID --value); if [ \"$pid\" != 0 ]; then echo 'Configuration is running; let it finish before refreshing.'; exit 75; fi; sudo systemctl stop progressbar-mail-configure; curl -fsS -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/mail-configure | base64 -d | sudo tee /usr/local/sbin/progressbar-mail-configure.py >/dev/null; sudo chmod 700 /usr/local/sbin/progressbar-mail-configure.py; sudo systemctl reset-failed progressbar-mail-configure; sudo systemctl start --no-block progressbar-mail-configure"
subprocess.run(['gcloud','compute','ssh','progressbar-mail','--zone='+E['zone'],'--project='+E['projectId'],'--account='+E['account'],'--tunnel-through-iap','--ssh-key-file='+str(key),'--quiet','--command='+command],check=True)
print('Applied metadata configuration queued on the server.')

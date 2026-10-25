"""Create, observe and destroy the isolated SMTP connectivity probe. Never sends mail."""
import json, os, pathlib, re, shutil, subprocess, time
ROOT = pathlib.Path(__file__).resolve().parents[3]
FOLDER = pathlib.Path(__file__).resolve().parent
PROJECT = 'project-fb85ba80-c9eb-43f0-af3'
ACCOUNT = '--account=pb.simon.chi@gmail.com'
TF = os.environ.get('TERRAFORM') or shutil.which('terraform') or str(ROOT / '.tools/terraform')
LOGS = ROOT / '.local'
LOGS.mkdir(exist_ok=True)

def environment():
    token = subprocess.check_output(['gcloud', 'auth', 'print-access-token', ACCOUNT], text=True).strip()
    return dict(os.environ, TF_IN_AUTOMATION='true', GOOGLE_OAUTH_ACCESS_TOKEN=token)

def tf(*args):
    with (LOGS / 'mail-probe-lifecycle.log').open('a') as output:
        subprocess.run([TF, '-chdir=' + str(FOLDER), *args], env=environment(), stdout=output, stderr=subprocess.STDOUT, check=True)

try:
    tf('init', '-input=false', '-no-color')
    tf('validate', '-no-color')
    tf('plan', '-input=false', '-no-color', '-out=probe.tfplan')
    tf('apply', '-input=false', '-no-color', 'probe.tfplan')
    for attempt in range(24):
        result = subprocess.run(['gcloud', 'compute', 'instances', 'get-serial-port-output', 'progressbar-smtp-probe', '--zone=us-central1-a', '--project=' + PROJECT, ACCOUNT], text=True, capture_output=True)
        matches = re.findall(r'PB_SMTP_PROBE_RESULT=(\{[^\r\n]*\})', result.stdout)
        if matches:
            data = json.loads(matches[-1])
            (LOGS / 'mail-probe-result.json').write_text(json.dumps(data, indent=2) + '\n')
            print(json.dumps(data, indent=2))
            break
        time.sleep(5)
    else:
        raise RuntimeError('Probe result not observed; check serial logs. The finally block still destroys the probe.')
finally:
    tf('destroy', '-auto-approve', '-input=false', '-no-color')

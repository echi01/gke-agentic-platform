"""Check deployable source and guard against accidental broad exposure."""
import ast,json,pathlib,subprocess
folder=pathlib.Path(__file__).resolve().parents[1];repo=folder.parents[2]
for p in (folder/'scripts').glob('*.py'):ast.parse(p.read_text())
subprocess.run(['bash','-n',str(folder/'scripts/startup.sh')],check=True)
env=json.loads((folder/'environment.json').read_text());assert '@sha256:' in env['image'];assert env['hostname']=='mail.'+env['domain']
s=(folder/'main.tf').read_text();assert '35.235.240.0/20' in s;assert '"8080"' not in s;assert 'production/mail' in (folder/'scripts/deploy.py').read_text();assert 'prevent_destroy = true' in s;assert 'secret_data' not in s
subprocess.run([str(repo/'.tools/terraform'),'-chdir='+str(folder),'validate','-no-color'],check=True)
print('Source and Terraform checks passed. Live mail checks remain separate.')

"""Import a reviewed chart version and keep its expanded source inside this repo."""
import argparse,hashlib,importlib.util,json,pathlib,re,shutil,subprocess,tempfile,tarfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--version',required=True);p.add_argument('--archive-sha256',required=True);p.add_argument('--helm',default='helm');a=p.parse_args()
lock=json.loads((ROOT/'addons.lock.json').read_text())
if a.name not in lock or 'repository' not in lock[a.name]:p.error('Select an existing upstream chart integration')
if not re.fullmatch(r'v?\d+\.\d+\.\d+',a.version) or not re.fullmatch(r'[a-f0-9]{64}',a.archive_sha256):p.error('Use an explicit stable version and reviewed archive SHA256')
e=lock[a.name];target=ROOT/'vendor/helm'/a.name/a.version
if target.exists():p.error('That version is already stored; do not overwrite reviewed source')
with tempfile.TemporaryDirectory() as tmp:
 args=[a.helm,'pull',('oci://'+e['repository']+'/'+e['chart']) if 'ociDigest' in e else e['chart'],'--version',a.version,'--destination',tmp]
 if 'ociDigest' not in e:args.extend(['--repo',e['repository']])
 result=subprocess.run(args,check=True,capture_output=True,text=True)
 archive=next(pathlib.Path(tmp).glob('*.tgz'))
 if hashlib.sha256(archive.read_bytes()).hexdigest()!=a.archive_sha256:raise SystemExit('Archive digest mismatch')
 expanded=pathlib.Path(tmp)/'expanded';expanded.mkdir()
 with tarfile.open(archive) as tar:tar.extractall(expanded,filter='data')
 while archives:=list(expanded.rglob('*.tgz')):
  for item in archives:
   with tarfile.open(item) as tar:tar.extractall(item.parent,filter='data')
   item.unlink()
 target.parent.mkdir(parents=True,exist_ok=True);shutil.move(expanded,target)
entry=dict(e,version=a.version,path=str((target/e['chart']).relative_to(ROOT)),archiveSha256=a.archive_sha256)
entry.pop('digest',None);entry.pop('release',None)
if 'ociDigest' in entry:
 digest=re.search(r'Digest: (sha256:[a-f0-9]{64})',result.stdout+result.stderr)
 if not digest:raise SystemExit('OCI digest missing; do not promote this import')
 entry['ociDigest']=digest.group(1)
spec=importlib.util.spec_from_file_location('vendor_integrity',ROOT/'scripts/verify-vendor.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
entry['treeSha256']=module.treehash(target/e['chart'])
old_path=ROOT/e['path'];history=ROOT/'.local/vendor-history'/a.name/e['version'];history.parent.mkdir(parents=True,exist_ok=True)
if old_path.parent.exists() and old_path!=target/e['chart']:
 if history.exists():raise SystemExit('Existing archive history needs review before replacing source')
 shutil.move(old_path.parent,history)
lock[a.name]=entry;(ROOT/'addons.lock.json').write_text(json.dumps(lock,indent=2)+'\n')
print('Imported reviewed local chart source. Review the diff, update values/tests and run all checks before promotion.')

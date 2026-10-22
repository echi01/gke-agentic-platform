"""Install a pinned upstream release with its published SHA256; no shell installer."""
import argparse,hashlib,json,pathlib,platform,subprocess,tarfile,tempfile
p=argparse.ArgumentParser();p.add_argument("--bin-dir",default=".tools");a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[1];lock=json.loads((root/"operations/kubectl-ai/release.lock.json").read_text())
system={"Darwin":"Darwin","Linux":"Linux"}.get(platform.system());arch={"arm64":"arm64","aarch64":"arm64","x86_64":"x86_64"}.get(platform.machine())
if not system or not arch:raise SystemExit("Use a supported Darwin/Linux arm64/x86_64 operator host")
name=f"kubectl-ai_{system}_{arch}.tar.gz";base="https://github.com/GoogleCloudPlatform/kubectl-ai/releases/download/"+lock["version"]+"/"
out=pathlib.Path(a.bin_dir).resolve();out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
 archive=pathlib.Path(tmp)/name
 subprocess.run(["curl","--fail","--silent","--show-error","--location",base+name,"--output",str(archive)],check=True)
 digest=hashlib.sha256(archive.read_bytes()).hexdigest()
 if digest!=lock["assets"][name]:raise SystemExit("kubectl-ai checksum mismatch")
 with tarfile.open(archive) as tar:tar.extractall(tmp,filter="data")
 binary=pathlib.Path(tmp)/"kubectl-ai"
 target=out/"kubectl-ai";target.write_bytes(binary.read_bytes());target.chmod(0o755)
print(target)

"""Download pinned CLI tools; verify release checksums; no cloud login or apply."""
import argparse
import hashlib
import io
import pathlib
import platform
import tarfile
import urllib.request
import zipfile

p = argparse.ArgumentParser()
p.add_argument("--bin-dir", type=pathlib.Path, required=True)
p.add_argument("--kind", action="store_true")
p.add_argument("--trivy", action="store_true")
args = p.parse_args()
system = platform.system().lower()
arch = "arm64" if platform.machine().lower() in ["aarch64", "arm64"] else "amd64"
if system not in ["linux", "darwin"]: p.error("Use Linux or macOS")
args.bin_dir.mkdir(parents=True, exist_ok=True)


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "GKEAgenticPlatform"}), timeout=60).read()


def install(name, url, checks_url, filename, archive_path=None):
    checks = fetch(checks_url).decode()
    rows = [line.split() for line in checks.splitlines() if line.strip()]
    expected = next(row[0] for row in rows if len(row) == 1 or row[-1].lstrip("*") == filename)
    raw = fetch(url)
    if hashlib.sha256(raw).hexdigest() != expected: raise RuntimeError("Release checksum mismatch")
    if filename.endswith(".zip"): binary = zipfile.ZipFile(io.BytesIO(raw)).read(archive_path)
    elif filename.endswith(".tar.gz"): binary = tarfile.open(fileobj=io.BytesIO(raw)).extractfile(archive_path).read()
    else: binary = raw
    target = args.bin_dir / name
    target.write_bytes(binary); target.chmod(0o755)
    print(name, expected)


name = f"terraform_1.13.5_{system}_{arch}.zip"
base = "https://releases.hashicorp.com/terraform/1.13.5/"
install("terraform", base + name, base + "terraform_1.13.5_SHA256SUMS", name, "terraform")
name = f"helm-v3.19.0-{system}-{arch}.tar.gz"
install("helm", "https://get.helm.sh/" + name, "https://get.helm.sh/" + name + ".sha256sum", name, f"{system}-{arch}/helm")
if args.kind:
    name = f"kind-{system}-{arch}"; url = "https://github.com/kubernetes-sigs/kind/releases/download/v0.30.0/" + name
    install("kind", url, url + ".sha256sum", name)
if args.trivy:
    name = f"trivy_0.76.1_{'macOS' if system == 'darwin' else 'Linux'}-{'ARM64' if arch == 'arm64' else '64bit'}.tar.gz"
    base = "https://github.com/aquasecurity/trivy/releases/download/v0.76.1/"
    install("trivy", base + name, base + "trivy_0.76.1_checksums.txt", name, "trivy")

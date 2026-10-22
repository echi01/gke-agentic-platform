"""Reject modified or missing vendored chart source before release/bootstrap."""
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
def treehash(folder):
 digest=hashlib.sha256()
 for p in sorted(folder.rglob("*")):
  if p.is_file():digest.update(str(p.relative_to(folder)).encode()+b"\0"+hashlib.sha256(p.read_bytes()).digest())
 return digest.hexdigest()
def verify():
 lock=json.loads((ROOT/"addons.lock.json").read_text());count=0
 for name,entry in lock.items():
  if "treeSha256" not in entry:continue
  folder=ROOT/entry["path"]
  if not (folder/"Chart.yaml").exists() or treehash(folder)!=entry["treeSha256"]:raise ValueError("Vendor integrity mismatch: "+name)
  count+=1
 return count
if __name__=="__main__": print("Verified",verify(),"local upstream chart trees")

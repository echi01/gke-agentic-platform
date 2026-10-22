"""Validate local infrastructure source; no cloud apply or model requests."""
import argparse, importlib.util, json, os, pathlib, shutil, subprocess, sys
import yaml
yaml.SafeLoader.add_constructor("tag:yaml.org,2002:value", lambda loader, node: loader.construct_scalar(node))
ROOT=pathlib.Path(__file__).resolve().parents[1]
def run(args,cwd=ROOT,capture=False):
 return subprocess.run([str(a) for a in args],cwd=cwd,check=True,text=True,stdout=subprocess.PIPE if capture else None).stdout
def binary(name):
 value=os.environ.get(name.upper()) or shutil.which(name)
 if not value and (ROOT/".tools"/name).exists():value=ROOT/".tools"/name
 if not value:raise SystemExit("Install "+name+" or set "+name.upper())
 return str(value)
def render(helm,chart,values,namespace="argocd"):
 out=ROOT/".artifacts";out.mkdir(exist_ok=True)
 file=out/(chart.name+"-values.yaml");file.write_text(yaml.safe_dump(values))
 text=run([helm,"template",chart.name,chart,"--namespace",namespace,"--kube-version","1.34.0","--include-crds","-f",file],capture=True)
 docs=[d for d in yaml.safe_load_all(text) if d]
 (out/(chart.name+"-rendered.yaml")).write_text(text)
 return docs
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--terraform",action="store_true");a=p.parse_args()
 run([sys.executable,ROOT/"scripts/verify-vendor.py"])
 run([sys.executable,"-m","unittest","discover","-s","tests","-v"])
 helm=binary("helm");lock=json.loads((ROOT/"addons.lock.json").read_text());configs={};counts={}
 for name,item in lock.items():
  vals=yaml.safe_load((ROOT/"modules/kubernetes-addons"/name/"values.yaml").read_text()) or {}
  if name=="certificate-issuers":vals.update({"email":"operator@example.com"})
  if name=="kubernetes-mcp":vals.update({"image":"registry.example/platform-mcp@sha256:"+"a"*64,"apiCidrs":["10.48.0.1/32"]})
  docs=render(helm,ROOT/item["path"],vals,name if name!="kubernetes-mcp" else "platform-ops");counts[name]=len(docs)
  if name=="kubernetes-mcp":
   exec_grants=[(d["metadata"]["name"],rule) for d in docs if d["kind"]=="Role" for rule in d["rules"] if "pods/exec" in rule.get("resources",[])]
   assert exec_grants==[("connect-platform-mcp",{"apiGroups":[""],"resources":["pods/exec"],"resourceNames":["platform-mcp-0"],"verbs":["create"]})], "Unexpected MCP execution authority"

  configs[name]={"name":name,"namespace":name,"path":item["path"],"version":item["version"],"values":vals,"wave":0}
 configs.pop("argo-cd")
 addons=render(helm,ROOT/"charts/addons",{"repositoryUrl":"https://github.com/example/platform.git","revision":"a"*40,"addons":configs})
 assert len([d for d in addons if d["kind"]=="Application"])==len(configs)
 assert all(d["spec"]["source"].get("path") and "chart" not in d["spec"]["source"] for d in addons)
 app={"repositoryUrl":"https://github.com/example/application.git","revision":"b"*40,"namespace":"example-tenant","path":"deploy/runtime","extensionPath":"deploy/prerequisites","mesh":True,"observerGroups":[],"values":{}}
 workloads=render(helm,ROOT/"charts/workloads",{"workloads":{"example":app}})
 projects={d["metadata"]["name"]:d for d in workloads if d["kind"]=="AppProject"}
 assert projects["tenant-example-runtime"]["spec"]["clusterResourceWhitelist"]==[]
 assert not any(x["kind"] in ["Secret","Role","RoleBinding","Job"] for x in projects["tenant-example-runtime"]["spec"]["namespaceResourceWhitelist"])
 assert len([d for d in workloads if d["kind"]=="Application"])==2
 for invalid in [{**app,"revision":"HEAD"},{**app,"namespace":"kube-system"}]:
  try:render(helm,ROOT/"charts/workloads",{"workloads":{"example":invalid}})
  except subprocess.CalledProcessError:pass
  else:raise AssertionError("Unsafe registration rendered")
 for gpu in [False,True]:
  docs=render(helm,ROOT/"charts/agent-inference",{"image":"registry.example/model@sha256:"+"c"*64,"gpu":gpu,"autoscaling":{"enabled":True,"maxReplicas":2}},"inference")
  sts=next(d for d in docs if d["kind"]=="StatefulSet")
  assert sts["spec"]["volumeClaimTemplates"]
  assert ("nvidia.com/gpu" in sts["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"])==gpu
 for name in ["argo-cd","kube-prometheus-stack"]:
  values=yaml.safe_load((ROOT/"deploy/prod/addons/values"/(name+".yaml")).read_text())
  render(helm,ROOT/lock[name]["path"],values,name)
 receipt={"productionProfilesRendered":2,"upstreamChartsVerified":len([v for v in lock.values() if "treeSha256" in v]),"addonChartsRendered":counts,"applicationBoundaryChecks":"passed","mcpUnitTests":5,"inferenceProfiles":2,"cloudApply":False,"modelCalls":0}
 if a.terraform:
  tf=binary("terraform")
  dirs=[ROOT/"modules/gke",ROOT/"modules/state-backend",ROOT/"modules/workload-identity",ROOT/"modules/kubernetes-addons/helm-addon",ROOT/"infrastructure/state-backend",ROOT/"infrastructure/gke-platform",ROOT/"infrastructure/platform-addons",ROOT/"infrastructure/workload-delivery"]+[ROOT/"deploy"/env/stage for env in ["dev","staging","prod"] for stage in ["backend","gke","addons","workloads"]]
  for folder in dirs:
   run([tf,"init","-backend=false","-input=false","-no-color"],folder)
   run([tf,"validate","-no-color"],folder)
   if (folder/"tests").exists():run([tf,"test","-no-color"],folder)
  receipt["terraformRootsValidated"]=len(dirs)
 (ROOT/".artifacts/checks.json").write_text(json.dumps(receipt,indent=2)+"\n")
 print(json.dumps(receipt,indent=2))

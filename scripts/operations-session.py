"""Create isolated short-lived operator configuration; never overwrites ~/.kube or ADC."""
import argparse, json, os, pathlib, subprocess, sys
import yaml
p=argparse.ArgumentParser()
p.add_argument("--kubeconfig",required=True)
p.add_argument("--context",required=True)
p.add_argument("--directory",required=True)
p.add_argument("--operations-namespace",default="platform-ops")
p.add_argument("--inspect-namespace",default="platform-ops")
p.add_argument("--model",required=True)
p.add_argument("--provider",default="vertexai")
a=p.parse_args()
d=pathlib.Path(a.directory).resolve()
if d.exists() and list(d.iterdir()):p.error("Choose a new empty session directory")
d.mkdir(parents=True,exist_ok=True);d.chmod(0o700)
k=["kubectl","--kubeconfig",str(pathlib.Path(a.kubeconfig).resolve()),"--context",a.context]
config=yaml.safe_load(subprocess.check_output(k+["config","view","--minify","--flatten","--raw"],text=True))
cluster=config["clusters"][0]
token=subprocess.check_output(k+["-n",a.operations_namespace,"create","token","platform-assistant","--duration=10m"],text=True).strip()
scoped={"apiVersion":"v1","kind":"Config","current-context":"platform-inspection","clusters":[cluster],"users":[{"name":"platform-assistant","user":{"token":token}}],"contexts":[{"name":"platform-inspection","context":{"cluster":cluster["name"],"user":"platform-assistant","namespace":a.inspect_namespace}}]}
kp=d/"kubeconfig";kp.write_text(yaml.safe_dump(scoped));kp.chmod(0o600)
xdg=d/"config";cfg=xdg/"kubectl-ai";cfg.mkdir(parents=True)
server={"servers":[{"name":"platform-inspector","command":"kubectl","args":["--kubeconfig",str(kp),"--context","platform-inspection","-n",a.operations_namespace,"exec","-i","pod/platform-mcp-0","--","python","/mcp/server.py"]}]}
(cfg/"mcp.yaml").write_text(yaml.safe_dump(server))
root=pathlib.Path(__file__).resolve().parents[1]
print(json.dumps({"sessionDirectory":str(d),"expires":"server-issued token requested for 10 minutes; renew by creating another session", "environment":{"XDG_CONFIG_HOME":str(xdg),"KUBECONFIG":str(kp)},"command":["kubectl-ai","--kubeconfig",str(kp),"--mcp-client","--llm-provider",a.provider,"--model",a.model,"--extra-prompt-paths",str(root/"operations/kubectl-ai/operating-rules.md"),"--trace-path",str(d/"trace.txt")]},indent=2))

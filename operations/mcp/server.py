"""Namespace-bound read-only MCP. No shell, arbitrary URL, Secret or log tools."""
import json, os, re, ssl, sys, urllib.request
TOKEN = "/var/run/secrets/kubernetes.io/serviceaccount/token"
CA = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
TOOLS = {
 "pods": ("Summarize pod phases and ready containers", "/api/v1/namespaces/{ns}/pods"),
 "events": ("Summarize event reasons without free-text bodies", "/api/v1/namespaces/{ns}/events"),
 "deployments": ("Summarize deployment availability", "/apis/apps/v1/namespaces/{ns}/deployments"),
 "jobs": ("Summarize job success and failure counts", "/apis/batch/v1/namespaces/{ns}/jobs"),
 "autoscalers": ("Summarize autoscaler current and desired capacity", "/apis/autoscaling/v2/namespaces/{ns}/horizontalpodautoscalers")
}
PROTOCOLS = {"2024-11-05", "2025-03-26", "2025-06-18"}
class Client:
 def __init__(self, namespace):
  if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", namespace): raise ValueError("Invalid namespace")
  self.namespace = namespace
 def query(self, path):
  with open(TOKEN) as f: token = f.read().strip()
  req = urllib.request.Request("https://kubernetes.default.svc" + path, headers={"Authorization": "Bearer " + token})
  with urllib.request.urlopen(req, context=ssl.create_default_context(cafile=CA), timeout=10) as response:
   body=response.read(1048577)
  if len(body)>1048576: raise ValueError("Response limit exceeded")
  return json.loads(body)
def reply(message, client):
 ident=message.get("id")
 if ident is None: return None
 method=message.get("method");params=message.get("params") or {}
 if method=="initialize":
  protocol=params.get("protocolVersion")
  result={"protocolVersion":protocol if protocol in PROTOCOLS else "2025-06-18", "capabilities":{"tools":{}}, "serverInfo":{"name":"platform-kubernetes-inspector","version":"1.0.0"}}
 elif method=="ping": result={}
 elif method=="tools/list":
  result={"tools":[{"name":name,"description":description,"inputSchema":{"type":"object","properties":{},"additionalProperties":False}} for name,(description,_) in TOOLS.items()]}
 elif method=="tools/call":
  name=params.get("name")
  if name not in TOOLS or params.get("arguments",{}):
   return {"jsonrpc":"2.0","id":ident,"error":{"code":-32602,"message":"Choose an inspection tool without arguments"}}
  page=client.query(TOOLS[name][1].format(ns=client.namespace)+"?limit=50")
  records=[]
  for item in page.get("items",[]):
   status=item.get("status",{})
   records.append({"name":item["metadata"]["name"],"phase":status.get("phase"),"reason":item.get("reason"),"readyReplicas":status.get("readyReplicas"),"waitingReasons":[c.get("state",{}).get("waiting",{}).get("reason") for c in status.get("containerStatuses",[]) if c.get("state",{}).get("waiting")],"readyContainers":sum(bool(c.get("ready")) for c in status.get("containerStatuses",[])),"succeeded":status.get("succeeded"),"failed":status.get("failed"),"currentReplicas":status.get("currentReplicas"),"desiredReplicas":status.get("desiredReplicas")})
  result={"content":[{"type":"text","text":json.dumps({"namespace":client.namespace,"records":records,"truncated":bool(page.get("metadata",{}).get("continue"))})}]}
 else: return {"jsonrpc":"2.0","id":ident,"error":{"code":-32601,"message":"Unknown method"}}
 return {"jsonrpc":"2.0","id":ident,"result":result}
def serve(client):
 for line in sys.stdin:
  if len(line)>65536: break
  ident=None
  try:
   message=json.loads(line);ident=message.get("id");response=reply(message,client)
  except Exception:
   response={"jsonrpc":"2.0","id":ident,"error":{"code":-32603,"message":"Inspection failed"}}
  if response is not None: print(json.dumps(response),flush=True)
if __name__=="__main__": serve(Client(os.environ["INSPECT_NAMESPACE"]))

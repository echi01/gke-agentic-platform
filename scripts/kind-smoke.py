"""Local-only MCP deployment/protocol/RBAC test; no model or cloud requests."""
import argparse,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--kubeconfig',required=True);p.add_argument('--context',default='kind-platform-v2-check');p.add_argument('--helm',default='helm');p.add_argument('--image',required=True);a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[1]
k=['kubectl','--kubeconfig',a.kubeconfig,'--context',a.context]
def run(parts,input=None,check=True):
 result=subprocess.run(parts,input=input,text=True,capture_output=True)
 if check and result.returncode:raise RuntimeError(result.stderr)
 return result
def call(messages):
 result=run(k+['-n','platform-ops','exec','-i','pod/platform-mcp-0','--','python','/mcp/server.py'],input=''.join(json.dumps(m)+'\n' for m in messages))
 return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
result=run([a.helm,'upgrade','--install','platform-mcp',str(root/'charts/kubernetes-mcp'),'--kubeconfig',a.kubeconfig,'--kube-context',a.context,'--namespace','platform-ops','--create-namespace','--set','localDevelopment=true','--set','image='+a.image,'--wait','--timeout','120s'])
checks=[]
messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}},{'jsonrpc':'2.0','method':'notifications/initialized'},{'jsonrpc':'2.0','id':2,'method':'tools/list'},{'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'pods','arguments':{}}}]
responses=call(messages)
assert responses[0]['result']['serverInfo']['name']=='platform-kubernetes-inspector'
checks.append('MCP initialization and tool discovery over private Kubernetes exec')
pods=json.loads(responses[-1]['result']['content'][0]['text'])
assert pods['namespace']=='platform-ops' and any(p['name']=='platform-mcp-0' for p in pods['records'])
checks.append('Deployed MCP process reads real namespace pod state')
invalid=call([{'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'pods','arguments':{'namespace':'kube-system'}}}])
assert invalid[0]['error']['code']==-32602
checks.append('Tool arguments cannot change namespace or invoke commands')
for sa,verb,resource,namespace,expected in [('platform-mcp','get','secrets','platform-ops','no'),('platform-mcp','create','deployments','platform-ops','no'),('platform-mcp','get','pods','kube-system','no'),('platform-assistant','create','pods/exec','platform-ops','no')]:
 # Last check uses no resourceName: an unrestricted exec grant must be absent.
 result=run(k+['auth','can-i',verb,resource if resource!='pods/exec' else 'pods',*(['--subresource=exec'] if resource=='pods/exec' else []),'-n',namespace,'--as=system:serviceaccount:platform-ops:'+sa],check=False)
 assert result.stdout.strip()==expected,result.stdout+result.stderr
checks.append('Kubernetes RBAC denies secrets, writes, other namespaces and unrestricted exec')
result=run(k+['auth','can-i','create','pods/platform-mcp-0','--subresource=exec','-n','platform-ops','--as=system:serviceaccount:platform-ops:platform-assistant'],check=False)
assert result.stdout.strip()=='yes'
checks.append('Assistant can connect only to its explicitly named MCP pod')
pod=json.loads(run(k+['get','pod','platform-mcp-0','-n','platform-ops','-o','json']).stdout)
assert pod['spec']['securityContext']['runAsNonRoot']
container=pod['spec']['containers'][0]
assert container['securityContext']['readOnlyRootFilesystem'] and container['securityContext']['capabilities']['drop']==['ALL']
checks.append('MCP runtime uses a restricted nonroot container with read-only filesystem')
run(k+['delete','pod','platform-mcp-0','-n','platform-ops','--wait=true','--timeout=60s'])
run(k+['rollout','status','statefulset/platform-mcp','-n','platform-ops','--timeout=120s'])
assert call([messages[-1]])[0].get('result')
checks.append('Replacement MCP pod accepts a new inspection session')
receipt={'passed':len(checks),'checks':checks,'cloudResourcesCreated':False,'modelCalls':0,'limitations':['Kind CNI does not prove NetworkPolicy enforcement','GKE IAM, mTLS, add-on compatibility and model reasoning require deployed acceptance']}
(root/'.artifacts/kind-smoke.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

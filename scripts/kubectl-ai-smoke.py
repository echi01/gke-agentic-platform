"""Exercise kubectl-ai and the deployed MCP bridge without any LLM request."""
import json,subprocess,os
from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('--session',required=True);p.add_argument('--binary',required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1];session=Path(a.session).resolve()
messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'blueprint-native-smoke','version':'1.0.0'}}},{'jsonrpc':'2.0','method':'notifications/initialized'},{'jsonrpc':'2.0','id':2,'method':'tools/list'}]
env=dict(os.environ,XDG_CONFIG_HOME=str(session/'config'),KUBECONFIG=str(session/'kubeconfig'))
p=subprocess.Popen([a.binary,'--mcp-server','--external-tools','--kubeconfig',str(session/'kubeconfig')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
try:out,err=p.communicate(''.join(json.dumps(x)+'\n' for x in messages),timeout=30)
except subprocess.TimeoutExpired:p.kill();out,err=p.communicate()
responses=[]
for line in out.splitlines():
 try:responses.append(json.loads(line))
 except json.JSONDecodeError:pass
result=next((x for x in responses if x.get('id')==2),None)
if not result:raise SystemExit('External discovery failed: '+err[-1500:])
names=[t['name'] for t in result['result']['tools']]
assert len(names)>=7,names
receipt={'kubectlAiVersion':'v0.0.31','externalMcpDiscovery':'passed','tools':names,'modelCalls':0}
(root/'.artifacts/kubectl-ai-external-smoke.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

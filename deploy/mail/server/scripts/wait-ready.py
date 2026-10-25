"""Bounded readiness observation, without restarting or modifying the server."""
import json,pathlib,ssl,socket,time,urllib.request,datetime
F=pathlib.Path(__file__).resolve().parents[1];E=json.loads((F/'environment.json').read_text());ctx=ssl.create_default_context();last=None
for n in range(40):
 try:
  with urllib.request.urlopen('https://'+E['hostname']+'/healthz/live',context=ctx,timeout=5) as r:
   if r.status==200:print('Public HTTPS health and certificate verified.',flush=True);break
 except (OSError,ValueError) as e:
  last=type(e).__name__
 if n%6==0:print('Waiting for public certificate/health:',last,flush=True)
 time.sleep(5)
else:raise RuntimeError('Public HTTPS readiness not observed within the bounded wait: '+str(last))

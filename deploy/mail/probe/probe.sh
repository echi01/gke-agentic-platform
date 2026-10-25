#!/bin/bash
set -eu
command -v python3 >/dev/null || (apt-get update -qq && apt-get install -y python3)
python3 - <<'PY'
import socket,json,concurrent.futures,datetime
checks=[('smtp.gmail.com',587),('www.google.com',443),('gmail-smtp-in.l.google.com',25),('aspmx.l.google.com',25),('mta5.am0.yahoodns.net',25)]
def probe(item):
 host,port=item
 try:
  ipv4=socket.getaddrinfo(host,port,socket.AF_INET,socket.SOCK_STREAM)[0][4]
  with socket.create_connection(ipv4,timeout=8):return {'host':host,'port':port,'connected':True}
 except Exception as error:return {'host':host,'port':port,'connected':False,'error':type(error).__name__}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
 result=list(pool.map(probe,checks))
print('PB_SMTP_PROBE_RESULT='+json.dumps({'testedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':result}),flush=True)
PY

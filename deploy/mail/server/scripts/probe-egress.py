"""Network-only check; no message or SMTP envelope is sent."""
import concurrent.futures,datetime,json,socket
pairs=[('gmail-smtp-in.l.google.com',25),('aspmx.l.google.com',25),('mta5.am0.yahoodns.net',25),('smtp.gmail.com',587),('www.google.com',443)]
def one(pair):
 host,port=pair
 try:
  address=socket.getaddrinfo(host,port,socket.AF_INET,socket.SOCK_STREAM)[0][4]
  with socket.create_connection(address,timeout=8):return {'host':host,'port':port,'connected':True}
 except OSError as e:return {'host':host,'port':port,'connected':False,'error':type(e).__name__}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:r=list(pool.map(one,pairs))
print(json.dumps({'testedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':r,'internetMessagesSent':0}))

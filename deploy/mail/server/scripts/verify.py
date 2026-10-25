"""Live mail acceptance. Only sends a self-check between this server's own mailboxes."""
import concurrent.futures,datetime,email.message,imaplib,json,pathlib,smtplib,socket,ssl,subprocess,time,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[4];FOLDER=ROOT/'deploy/mail/server';E=json.loads((FOLDER/'environment.json').read_text());hostname=E['hostname'];domain=E['domain'];ctx=ssl.create_default_context()
def port(n):
 try:
  with socket.create_connection((hostname,n),timeout=5):return {'port':n,'reachable':True}
 except OSError as e:return {'port':n,'reachable':False,'error':type(e).__name__}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:ports=list(pool.map(port,[25,443,465,587,993,8080]))
result={'testedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'hostname':hostname,'ports':ports,'externalRecipients':[]}
if not all(x['reachable'] for x in ports if x['port'] in [25,443,465,587,993]):
 (ROOT/'.local/mail/network-check.json').write_text(json.dumps(result,indent=2));raise RuntimeError('One or more public mail protocols are not reachable; no message sent')
assert not next(x for x in ports if x['port']==8080)['reachable'],'Private setup listener exposed'
with socket.create_connection((hostname,443),timeout=10) as raw:
 with ctx.wrap_socket(raw,server_hostname=hostname) as secured: result['tls']={'verified':True,'issuer':secured.getpeercert()['issuer'],'expires':secured.getpeercert()['notAfter']}
password=subprocess.check_output(['gcloud','secrets','versions','access','latest','--secret=progressbar-mail-hello','--project='+E['projectId'],'--account='+E['account']],text=True).strip()
subject='Progress Bar mail self-check '+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
msg=email.message.EmailMessage();msg['From']='hello@'+domain;msg['To']='support@'+domain;msg['Subject']=subject;msg.set_content('Automated operational self-check between our own branded mailbox and its support alias. No external recipient.')
with smtplib.SMTP(hostname,587,timeout=30) as smtp:smtp.ehlo();smtp.starttls(context=ctx);smtp.ehlo();smtp.login('hello@'+domain,password);smtp.send_message(msg)
result['authenticatedSubmission']=True
for _ in range(25):
 with imaplib.IMAP4_SSL(hostname,993,ssl_context=ctx,timeout=15) as im:
  im.login('hello@'+domain,password);im.select('INBOX');status,ids=im.search(None,'SUBJECT','"'+subject+'"')
  if status=='OK' and ids[0]:result['aliasDeliveryAndImapReceipt']=True;break
 time.sleep(2)
else:raise RuntimeError('Self-check message not received')
with smtplib.SMTP(hostname,25,timeout=90) as smtp:
 smtp.ehlo();smtp.mail('outside@example.org');code,_=smtp.rcpt('another@example.net');result['unauthenticatedRelayRejected']=code;assert code>=500
 smtp.rset();smtp.mail('');code,_=smtp.rcpt('support@'+domain);result['inboundAliasRecipientAccepted']=code;assert code==250
 smtp.rset();smtp.mail('');code,_=smtp.rcpt('nonexistent-acceptance-recipient@'+domain);result['unknownRecipientRejected']=code;assert code>=500
# Invalid password must fail over a correctly validated TLS connection.
try:
 with smtplib.SMTP_SSL(hostname,465,context=ctx,timeout=20) as smtp:smtp.login('hello@'+domain,'deliberately-invalid-acceptance-value')
except smtplib.SMTPAuthenticationError:result['wrongPasswordRejected']=True
else:raise RuntimeError('Invalid credentials were accepted')
path=FOLDER/'evidence/live-mail.json';path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

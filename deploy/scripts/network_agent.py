#!/usr/bin/env python3
"""Local privileged network agent. Fixed operations only; no shell or motor access."""
import argparse,base64,hmac,http.server,json,os,secrets,socketserver,subprocess,threading,time,uuid
from pathlib import Path

AP='onigiri-setup'
IP='192.168.50.1'
class Network:
 def __init__(self,config,run=None,profile=None):
  self.config=config;self.profile=Path(profile or '/etc/NetworkManager/system-connections/onigiri-user.nmconnection');self.run=run or self.command;self.busy=False;self.message='';self.lock=threading.Lock();self.failed_since=None
 @staticmethod
 def command(*args):
  return subprocess.run(['nmcli','--wait','20',*args],capture_output=True,text=True,timeout=30,check=True).stdout.strip()
 def status(self):
  try:
   active=self.run('-g','GENERAL.CONNECTION','device','show',self.config['interface']).strip()
   addresses=self.run('-g','IP4.ADDRESS','device','show',self.config['interface']).splitlines()
   return dict(enabled=True,mode='setup' if active==AP else 'wifi' if active and active!='--' else 'disconnected',connection=active,addresses=addresses,setup_ssid=self.config['ssid'],setup_url='http://'+IP+':8080',busy=self.busy,message=self.message)
  except Exception:return dict(enabled=True,mode='unavailable',busy=self.busy,message='Interface Wi-Fi indisponível.',setup_ssid=self.config['ssid'],addresses=[])
 def connect(self,data):
  if not isinstance(data,dict):raise ValueError('Requisição inválida')
  ssid=data.get('ssid','');password=data.get('password','')
  if not isinstance(ssid,str) or not 1<=len(ssid.encode())<=32 or any(c in ssid for c in '\n\r\0'):raise ValueError('SSID inválido')
  if not isinstance(password,str) or not 8<=len(password)<=63 or any(c in password for c in '\n\r\0'):raise ValueError('Senha Wi-Fi deve ter de 8 a 63 caracteres')
  with self.lock:
   if self.busy:raise ValueError('Conexão em andamento')
   self.busy=True;self.message='Troca de rede agendada. Conecte seu computador à rede escolhida.'
  threading.Thread(target=self.apply,args=(ssid,password),daemon=True).start()
  return dict(accepted=True,message=self.message)
 def apply(self,ssid,password):
  time.sleep(3) # Return HTTP response before disconnecting the setup access point.
  profile=self.profile
  try:
   # Keyfile avoids Wi-Fi passwords in argv/process listings. Never log its contents.
   def escape(value):return value.replace('\\','\\\\').replace(' ','\\s')
   text=f'[connection]\nid=onigiri-user\nuuid={uuid.uuid4()}\ntype=wifi\ninterface-name={self.config["interface"]}\nautoconnect=true\nautoconnect-priority=100\n[wifi]\nmode=infrastructure\nssid={";".join(str(value) for value in ssid.encode())};\n[wifi-security]\nkey-mgmt=wpa-psk\npsk={escape(password)}\n[ipv4]\nmethod=auto\n[ipv6]\nmethod=auto\n'
   fd=os.open(profile,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
   with os.fdopen(fd,'w') as stream:stream.write(text)
   os.chmod(profile,0o600);self.run('connection','load',str(profile));self.run('connection','up','id','onigiri-user')
   self.message='Wi-Fi conectado. Acesse pelo IP da rede ou http://onigiri.local:8080.'
  except Exception:
   self.message='Não foi possível conectar. Confira rede e senha; a rede de configuração foi restaurada.'
   try:self.run('connection','up','id',AP)
   except Exception:pass
  finally:self.busy=False
 def ensure_access(self):
  if self.busy:return
  state=self.status()
  if state['mode'] in ('wifi','setup'):self.failed_since=None;return
  self.failed_since=self.failed_since or time.monotonic()
  if time.monotonic()-self.failed_since>=45:
   try:self.run('connection','up','id',AP);self.message='Rede de configuração disponível.'
   except Exception:self.message='Não foi possível iniciar a rede de configuração.'
   self.failed_since=None

def authorized(headers,config):
 expected='Basic '+base64.b64encode(('onigiri:'+config['password']).encode()).decode()
 return hmac.compare_digest(headers.get('Authorization',''),expected)

def handler(network,bootstrap=False):
 class Handler(http.server.BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def answer(self,status,data):
   body=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
  def do_GET(self):
   if bootstrap and not authorized(self.headers,network.config):
    self.send_response(401);self.send_header('WWW-Authenticate','Basic realm="Onigiri"');self.end_headers();return
   if self.path=='/api/setup/network':return self.answer(200,network.status())
   if bootstrap and self.path=='/':
    page=Path(__file__).with_name('first_access.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(page);return
   self.answer(404,{'detail':'Operação indisponível'})
  def do_POST(self):
   if bootstrap and not authorized(self.headers,network.config):return self.answer(401,{'detail':'Autenticação necessária'})
   if self.path!='/api/setup/network/connect':return self.answer(404,{'detail':'Operação indisponível'})
   try:
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=1024:raise ValueError('Requisição inválida')
    self.answer(202,network.connect(json.loads(self.rfile.read(length))))
   except (ValueError,TypeError,json.JSONDecodeError):self.answer(400,{'detail':'Confira SSID, senha e se existe uma conexão em andamento.'})
 return Handler

class UnixServer(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):daemon_threads=True

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--bootstrap',action='store_true');args=parser.parse_args()
 config=json.loads(Path('/etc/onigiri/access.json').read_text());network=Network(config)
 if args.bootstrap:
  import http.client,socket
  class Proxy:
   def __init__(self):self.config=config
   def request(self,path,data=None):
    connection=http.client.HTTPConnection('localhost');connection.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);connection.sock.settimeout(5);connection.sock.connect('/run/onigiri-network/agent.sock')
    try:
     connection.request('POST' if data is not None else 'GET',path,json.dumps(data) if data is not None else None,{'Content-Type':'application/json'})
     response=connection.getresponse();result=json.loads(response.read())
     if response.status>=400:raise ValueError('Conexão indisponível')
     return result
    finally:connection.close()
   def status(self):return self.request('/api/setup/network')
   def connect(self,data):return self.request('/api/setup/network/connect',data)
  network=Proxy()
  http.server.ThreadingHTTPServer(('0.0.0.0',8080),handler(network,True)).serve_forever();return
 path='/run/onigiri-network/agent.sock';Path(path).unlink(missing_ok=True)
 server=UnixServer(path,handler(network));import grp;os.chown(path,0,grp.getgrnam('onigiri').gr_gid);os.chmod(path,0o660)
 def watchdog():
  while True:network.ensure_access();time.sleep(5)
 threading.Thread(target=watchdog,daemon=True).start();server.serve_forever()
if __name__=='__main__':main()

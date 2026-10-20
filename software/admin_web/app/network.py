"""Narrow client for the local network agent."""
import http.client,json,os,socket
class UnixConnection(http.client.HTTPConnection):
 def connect(self):
  self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.settimeout(5);self.sock.connect(os.environ.get('ONIGIRI_NETWORK_SOCKET','/run/onigiri-network/agent.sock'))
def request(path,body=None):
 connection=UnixConnection('localhost')
 try:
  connection.request('POST' if body is not None else 'GET',path,json.dumps(body) if body is not None else None,{'Content-Type':'application/json'})
  response=connection.getresponse();data=json.loads(response.read())
  if response.status>=400:raise ValueError(data.get('detail','Falha na rede'))
  return data
 finally:connection.close()

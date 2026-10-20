import importlib.util,tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('network_agent',ROOT/'deploy/scripts/network_agent.py');agent=importlib.util.module_from_spec(spec);spec.loader.exec_module(agent)
class NetworkTests(unittest.TestCase):
 def config(self):return dict(interface='wlan0',ssid='Onigiri-Config-TEST',password='local-device-password')
 def test_status_never_returns_password(self):
  net=agent.Network(self.config(),lambda *args:agent.AP if 'GENERAL.CONNECTION' in args else '192.168.50.1/24')
  state=net.status();self.assertEqual(state['mode'],'setup');self.assertNotIn('local-device-password',json.dumps(state))
 def test_failed_connection_restores_hotspot_and_private_keyfile(self):
  calls=[]
  def run(*args):
   calls.append(args)
   if args==('connection','up','id','onigiri-user'):raise RuntimeError('bad password')
   return ''
  with tempfile.TemporaryDirectory() as folder,patch.object(agent.time,'sleep'):
   p=Path(folder)/'wifi.nmconnection';net=agent.Network(self.config(),run,p);net.busy=True;net.apply('Minha Rede;1','senha12345')
   self.assertIn(('connection','up','id',agent.AP),calls);self.assertFalse(net.busy)
   self.assertEqual(p.stat().st_mode&0o777,0o600);self.assertIn('ssid='+ ';'.join(str(value) for value in 'Minha Rede;1'.encode())+';',p.read_text())
   self.assertNotIn('senha12345',str(calls))
 def test_recovery_after_disconnection(self):
  calls=[]
  def run(*args):calls.append(args);return '--' if 'GENERAL.CONNECTION' in args else ''
  net=agent.Network(self.config(),run);net.failed_since=1
  with patch.object(agent.time,'monotonic',return_value=100):net.ensure_access()
  self.assertIn(('connection','up','id',agent.AP),calls)
 def test_rejects_keyfile_injection_and_invalid_ssid(self):
  net=agent.Network(self.config())
  for data in ({'ssid':'a\n[evil]','password':'12345678'},{'ssid':'á'*17,'password':'12345678'},{'ssid':'ok','password':'bad'},[]):
   with self.assertRaises(ValueError):net.connect(data)
 def test_browser_authentication(self):
  import base64
  config=self.config();self.assertFalse(agent.authorized({},config));self.assertTrue(agent.authorized({'Authorization':'Basic '+base64.b64encode(('onigiri:'+config['password']).encode()).decode()},config))

 def test_local_agent_client_over_unix_socket(self):
  import os,threading
  from app.network import request
  class Stub:
   config=self.config()
   def status(self):return {'enabled':True,'mode':'setup'}
   def connect(self,data):return {'accepted':True}
  with tempfile.TemporaryDirectory() as folder:
   path=str(Path(folder)/'agent.sock');server=agent.UnixServer(path,agent.handler(Stub()));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    with patch.dict(os.environ,{'ONIGIRI_NETWORK_SOCKET':path}):
     self.assertEqual(request('/api/setup/network')['mode'],'setup');self.assertTrue(request('/api/setup/network/connect',{'ssid':'Rede','password':'12345678'})['accepted'])
   finally:server.shutdown();server.server_close();thread.join()

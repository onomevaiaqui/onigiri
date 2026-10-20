import os,subprocess,tempfile,time,json,urllib.request,urllib.error,base64
from pathlib import Path
root=Path(__file__).resolve().parents[3]
with tempfile.TemporaryDirectory() as folder:
 path=Path(folder);(path/'access.json').write_text(json.dumps({'password':'test-device-only'}));env=os.environ.copy();env.update(ONIGIRI_ACCESS_FILE=str(path/'access.json'),ONIGIRI_ADMIN_DATABASE=str(path/'db.sqlite'),ONIGIRI_DESTINATIONS_FILE=str(path/'points.json'),ONIGIRI_PLATFORM_FILE=str(path/'platform.json'))
 server=subprocess.Popen([str(root/'.venv/bin/python'),'-m','uvicorn','app.main:app','--app-dir',str(root/'software/admin_web'),'--port','18087'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  for _ in range(50):
   try:urllib.request.urlopen('http://127.0.0.1:18087/api/health');break
   except OSError:time.sleep(.1)
  try:urllib.request.urlopen('http://127.0.0.1:18087/');raise AssertionError('Unauthenticated access')
  except urllib.error.HTTPError as error:assert error.code==401
  headers={'Authorization':'Basic '+base64.b64encode(b'onigiri:test-device-only').decode()}
  for endpoint in ('/','/static/setup.js','/api/platform','/api/setup/network'):
   response=urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18087'+endpoint,headers=headers));assert response.status==200
  print('PASS: painel exige credenciais do dispositivo; páginas, recursos e APIs acessíveis após autenticação')
 finally:server.terminate();server.wait(timeout=10)

import base64,hmac,json,os
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
class PanelAccess(BaseHTTPMiddleware):
 async def dispatch(self,request,call_next):
  path=Path(os.environ.get('ONIGIRI_ACCESS_FILE','/etc/onigiri/access.json'))
  if path.exists() and request.url.path!='/api/health':
   config=json.loads(path.read_text());expected='Basic '+base64.b64encode(('onigiri:'+config['password']).encode()).decode()
   if not hmac.compare_digest(request.headers.get('authorization',''),expected):return Response('Autenticação necessária',401,headers={'WWW-Authenticate':'Basic realm="Onigiri"'})
  return await call_next(request)

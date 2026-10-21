"""Identity and fixed hardware of the original Onigiri; no motor access."""
import json,os,tempfile
from pathlib import Path
from threading import RLock
FIXED={'computer':'raspberry4','chassis':'onigiri','motor_driver':'onigiri_hat','camera':'none','lidar':True}
class PlatformStore:
 def __init__(self,path):self.path=Path(path);self.lock=RLock()
 def get(self):
  with self.lock:
   saved=json.loads(self.path.read_text()) if self.path.exists() else {}
   return {**FIXED,'robot_name':saved.get('robot_name','')}
 def save(self,config):
  if any(config.get(key,value)!=value for key,value in FIXED.items()):raise ValueError('Hardware diferente do Onigiri original')
  with self.lock:
   result={**FIXED,'robot_name':config.get('robot_name','')};self.path.parent.mkdir(parents=True,exist_ok=True)
   fd,name=tempfile.mkstemp(dir=self.path.parent,prefix='.onigiri-')
   try:
    with os.fdopen(fd,'w') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    os.replace(name,self.path)
   finally:Path(name).unlink(missing_ok=True)
   return result

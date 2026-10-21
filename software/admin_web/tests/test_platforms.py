import tempfile,unittest
from pathlib import Path
from pydantic import ValidationError
from app.platforms import PlatformStore
class PlatformTests(unittest.TestCase):
 def test_fixed_hardware_and_name_persistence(self):
  with tempfile.TemporaryDirectory() as folder:
   store=PlatformStore(Path(folder)/'platform.json');self.assertEqual(store.get()['chassis'],'onigiri');store.save({'robot_name':'Recepção'});self.assertEqual(store.get()['robot_name'],'Recepção')
   with self.assertRaises(ValueError):store.save({'chassis':'other'})
 def test_api_rejects_different_hardware(self):
  from app.main import PlatformInput,app
  for data in ({'chassis':'other'},{'motor_driver':'other'},{'computer':'raspberry5'},{'camera':'other'},{'lidar':False},{'serial_port':'/dev/ttyUSB0'}):
   with self.assertRaises(ValidationError):PlatformInput(**data)
  self.assertEqual(PlatformInput(robot_name='Onigiri').chassis,'onigiri')
  paths={route.path for route in app.routes}
  self.assertFalse(any(path.startswith('/api/runtime') for path in paths));self.assertFalse(any(path.startswith('/api/sensors/camera') for path in paths))

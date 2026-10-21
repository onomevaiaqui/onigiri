import tempfile
import unittest
from pathlib import Path

from app.platforms import PlatformStore


class PlatformTests(unittest.TestCase):
    def test_migrates_original_profile_and_persists_supported_hardware(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "platform.json"
            path.write_text('{"robot_name":"Recepção","chassis":"onigiri"}')
            store = PlatformStore(path)
            self.assertEqual(store.get()["chassis"], "omniball")
            saved = store.save({**store.get(), "computer":"raspberry5", "chassis":"mecanum", "camera":"uvc"})
            self.assertEqual(saved["computer"], "raspberry5")
            self.assertEqual(store.get()["chassis"], "mecanum")

    def test_rejects_incompatible_driver_connection(self):
        with tempfile.TemporaryDirectory() as folder:
            store = PlatformStore(Path(folder) / "platform.json")
            config = {**store.get(), "motor_driver":"sabertooth2x32", "motor_connection":"i2c"}
            with self.assertRaises(ValueError):
                store.save(config)

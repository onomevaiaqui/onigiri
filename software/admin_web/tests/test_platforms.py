import tempfile
import unittest
from pathlib import Path
from app.platforms import PlatformStore, tank_tracks

class PlatformTests(unittest.TestCase):
    def test_persistence_and_original_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"hardware/platform.json"
            store=PlatformStore(path)
            self.assertEqual(store.get()["chassis"], "onigiri")
            config={"chassis":"tank", "track_separation_m":0.42,"camera":"gemini2","lidar":True}
            store.save(config)
            self.assertEqual(PlatformStore(path).get(), config)
            with self.assertRaises(ValueError): store.save({"chassis":"mecanum"})
            self.assertEqual(store.get(), config)
    def test_differential_units_and_rotation(self):
        self.assertEqual(tank_tracks(1,0,.4), {"left":1,"right":1})
        self.assertEqual(tank_tracks(0,2,.4), {"left":-.4,"right":.4})
        with self.assertRaises(ValueError): tank_tracks(0,0,0)

    def test_api_input_validation(self):
        from pydantic import ValidationError
        from app.main import PlatformInput, set_platform
        from fastapi import HTTPException
        with self.assertRaises(ValidationError): PlatformInput(track_separation_m=float('nan'))
        with self.assertRaises(ValidationError): PlatformInput(chassis='mecanum')
        with self.assertRaises(HTTPException): set_platform(PlatformInput(chassis='tank'))
        with self.assertRaises(HTTPException): set_platform(PlatformInput(motor_driver='sabertooth2x60'))
        for computer in ['raspberry4','raspberry5']:
            for driver in ['sabertooth2x32','sabertooth2x60']:
                config=PlatformInput(chassis='tank',computer=computer,motor_driver=driver,camera='gemini2')
                self.assertEqual(config.motor_driver,driver)

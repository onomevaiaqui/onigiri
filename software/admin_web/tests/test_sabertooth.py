import unittest
from app.sabertooth import motor_packet, tank_preview

class SabertoothTests(unittest.TestCase):
    def test_manufacturer_packet_example(self):
        # Manual example: address 130, command 0, value 64, checksum 66.
        self.assertEqual(motor_packet(130,1,64/127),bytes([130,0,64,66]))
    def test_reverse_and_second_motor(self):
        self.assertEqual(motor_packet(128,2,-1),bytes([128,5,127,4]))
    def test_mix_preserves_ratio_and_does_not_transmit(self):
        result=tank_preview(1,.5)
        self.assertAlmostEqual(result['left'],1/3)
        self.assertEqual(result['right'],1)
        self.assertFalse(result['transmitted'])
        self.assertEqual(tank_preview(0,1)['left'],-1)
        self.assertEqual(tank_preview(0,1)['right'],1)
        self.assertEqual(tank_preview(1,0,invert_left=True)['left'],-1)
    def test_stop_and_invalid_input(self):
        self.assertEqual(tank_preview(0,0)['packets_hex'],['80 00 00 00','80 04 00 04'])
        for args in [(127,1,0),(128,3,0),(128,1,float('nan')),(128,1,2)]:
            with self.assertRaises(ValueError): motor_packet(*args)
        with self.assertRaises(ValueError): tank_preview(float('inf'),0)

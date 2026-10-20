import struct
import unittest
import zlib
from app.camera_preview_ros import image_png, depth_png
from app.camera import CameraPreview

def pixels(png):
    offset=8;data=b''
    while offset<len(png):
        length=struct.unpack('!I',png[offset:offset+4])[0]
        if png[offset+4:offset+8]==b'IDAT':data+=png[offset+8:offset+8+length]
        offset+=12+length
    return zlib.decompress(data)

class CameraTests(unittest.TestCase):
    def test_rgb_padding_and_bgr(self):
        self.assertEqual(pixels(image_png(1,2,4,'rgb8',bytes([255,0,0,99,0,255,0,99]))),bytes([0,255,0,0,0,0,255,0]))
        self.assertEqual(pixels(image_png(1,1,3,'bgr8',bytes([0,0,255]))),bytes([0,255,0,0]))
    def test_downsample_and_reject_bad_images(self):
        png=image_png(1280,720,1280,'mono8',bytes(1280*720))
        self.assertEqual(struct.unpack('!II',png[16:24]),(640,360))
        for args in [(1,1,3,'16UC1',bytes(3)),(1,2,3,'rgb8',bytes(3)),(0,1,0,'rgb8',b'')]:
            with self.assertRaises(ValueError):image_png(*args)
    def test_disabled_preview_never_spawns(self):
        camera=CameraPreview('/missing',False)
        with self.assertRaises(ValueError):camera.start()
        self.assertFalse(camera.status()['running'])
        camera.stop()

    def test_depth_units_endianness_and_invalid_pixels(self):
        self.assertEqual(pixels(depth_png(3,1,6,'16UC1',struct.pack('<3H',0,1000,5000))),bytes([0,0,204,0]))
        self.assertEqual(pixels(depth_png(1,1,2,'16UC1',struct.pack('>H',1000),True)),bytes([0,204]))
        self.assertEqual(pixels(depth_png(2,1,8,'32FC1',struct.pack('<2f',float('nan'),1.))),bytes([0,0,204]))

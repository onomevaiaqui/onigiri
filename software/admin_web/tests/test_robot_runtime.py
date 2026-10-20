import copy,json,os,pty,sys,tempfile,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from robot_runtime.drive import wheels,DriveController
from robot_runtime.serial_driver import SerialSabertooth
from robot_runtime.stack import nav_config

class Sink:
    def __init__(self):self.values=[];self.stops=0
    def write(self,values):self.values=values
    def stop(self):self.stops+=1;self.values=[0,0]

class DriveTests(unittest.TestCase):
    def test_differential_and_mecanum(self):
        self.assertEqual(wheels('tank',1,0,2,.4,.4),[.6,1.4])
        with self.assertRaises(ValueError):wheels('independent',1,0,0,.4,.4)
        self.assertEqual(wheels('mecanum',0,1,0,.4,.4),[-1,1,1,-1])
        with self.assertRaises(ValueError):wheels('tank',0,1,0,.4,.4)
        with self.assertRaises(ValueError):wheels('mecanum',float('nan'),0,0,.4,.4)
    def test_latched_stop_and_watchdog(self):
        clock=[0.];sink=Sink();config={'chassis':'tank','track_separation_m':.4,'wheelbase_m':.4,'max_track_speed_mps':1,'power_limit':.2,'motor_inversions':[False,True]}
        driver=DriveController(sink,config,lambda:clock[0]);self.assertFalse(driver.command(1,0,0))
        driver.arm();driver.command(1,0,0);self.assertEqual(sink.values,[.2,-.2])
        clock[0]=.31;driver.tick();self.assertFalse(driver.armed);self.assertEqual(sink.values,[0,0])
        driver.stop(emergency=True)
        with self.assertRaises(ValueError):driver.arm()
        driver.release();self.assertFalse(driver.armed);driver.arm();driver.command(0,0,0)
        with self.assertRaises(ValueError):driver.command(0,1,0)
        self.assertTrue(driver.estop)
    def test_real_posix_transport_with_pseudo_terminal(self):
        master,slave=pty.openpty();os.set_blocking(master,False)
        try:
            driver=SerialSabertooth(os.ttyname(slave),9600,[128],'sabertooth2x32')
            try:
                driver.write([.5,-1]);time.sleep(.01);data=os.read(master,4096)
                self.assertIn(bytes([128,14,3,17]),data)
                self.assertIn(bytes([128,0,64,64,128,5,127,4]),data)
            finally:driver.close()
            self.assertEqual(os.read(master,4096),bytes([128,0,0,0,128,4,0,4]))
        finally:os.close(master);os.close(slave)

class NavConfigTests(unittest.TestCase):
    def test_geometry_odom_and_omnidirectional_config(self):
        import yaml
        path=Path('/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml')
        if not path.exists():self.skipTest('Nav2 não instalado')
        defaults=yaml.safe_load(path.read_text());original=copy.deepcopy(defaults)
        c={'body_width_m':.6,'body_length_m':.8,'chassis':'mecanum','max_track_speed_mps':.3}
        config=nav_config(defaults,c)
        self.assertEqual(defaults,original)
        self.assertEqual(config['bt_navigator']['ros__parameters']['odom_topic'],'/odom_rf2o')
        self.assertEqual(config['amcl']['ros__parameters']['robot_model_type'],'nav2_amcl::OmniMotionModel')
        self.assertGreater(config['controller_server']['ros__parameters']['FollowPath']['max_vel_y'],0)
        c['chassis']='tank';self.assertEqual(nav_config(defaults,c)['controller_server']['ros__parameters']['FollowPath']['max_vel_y'],0)

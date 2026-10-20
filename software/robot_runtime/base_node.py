#!/usr/bin/env python3
"""Explicit opt-in base service; never fabricates odometry from commanded PWM."""
import json
import math
import time
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from drive import DriveController
from serial_driver import SerialSabertooth

def main():
    if os.environ.get('ONIGIRI_MOTION_ENABLED')!='1':raise SystemExit('Movimento desabilitado')
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import Twist, TwistStamped
    from std_msgs.msg import Bool, String
    from sensor_msgs.msg import LaserScan
    from nav_msgs.msg import Odometry
    config_path=Path(os.environ.get('ONIGIRI_PLATFORM_FILE','/home/onigiri/onigiri/data/platform.json'))
    initial_config=config_path.read_text();config=json.loads(initial_config)
    required=['wheelbase_m','max_track_speed_mps','power_limit','motor_inversions','serial_port','serial_address','serial_baud']
    if not all(key in config for key in required):raise SystemExit('Configure dimensões, limites e canais no painel')
    if config.get('chassis') not in ('tank','mecanum'):raise SystemExit('Escolha Tank ou Mecanum para este driver; Onigiri usa o HAT original')
    if not config.get('extrinsics_measured'):raise SystemExit('Confirme a montagem e as dimensões medidas no painel')
    if config['motor_driver'] not in ('sabertooth2x32','sabertooth2x60'):raise SystemExit('Perfil sem Sabertooth')
    if not .01<=config['power_limit']<=1:raise SystemExit('Limite de potência inválido')
    addresses=[config['serial_address']]
    if config['chassis'] == 'mecanum':addresses.append(config['serial_address_2'])
    if len(addresses)==2 and config['motor_driver']=='sabertooth2x32':
        if not config.get('serial_port_2'):raise SystemExit('Dois Sabertooth USB precisam de duas portas')
        first=SerialSabertooth(config['serial_port'],config['serial_baud'],addresses[:1],config['motor_driver'])
        try:second=SerialSabertooth(config['serial_port_2'],config['serial_baud'],addresses[1:],config['motor_driver'])
        except Exception:first.close();raise
        class Dual:
            def write(self,p):first.write(p[:2]);second.write(p[2:])
            def stop(self):
                try:first.stop()
                finally:second.stop()
            def close(self):
                try:first.close()
                finally:second.close()
        sink=Dual()
    else:sink=SerialSabertooth(config['serial_port'],config['serial_baud'],addresses,config['motor_driver'])
    rgbd=not config.get('lidar',True) and config.get('camera')=='gemini2'
    if rgbd:
        pose=config.get('camera_xyz_rpy',[0.]*6)
        if abs(math.atan2(math.sin(pose[5]),math.cos(pose[5])))>.35 or abs(pose[4])>.6:
            sink.close();raise SystemExit('O perfil RGB-D de movimento exige câmera frontal; confira a orientação medida')
    controller=DriveController(sink,config)
    rclpy.init();node=Node('onigiri_base')
    status=node.create_publisher(String,'/onigiri/base/status',10)
    scan_state={'time':0.,'minimum':0.}
    def scan(msg):
        ranges=[v for v in msg.ranges if math.isfinite(v) and msg.range_min<=v<=msg.range_max]
        scan_state['time']=time.monotonic();scan_state['minimum']=min(ranges) if ranges else 0.
    node.create_subscription(LaserScan,'/scan',scan,__import__('rclpy.qos',fromlist=['qos_profile_sensor_data']).qos_profile_sensor_data)
    odometry={'time':0.,'valid':False}
    def odom(msg):
        p=msg.pose.pose.position;q=msg.pose.pose.orientation
        odometry['time']=time.monotonic()
        values=[p.x,p.y,p.z,q.x,q.y,q.z,q.w]
        covariance=[msg.pose.covariance[i] for i in (0,7,35)]
        stamp=msg.header.stamp.sec+msg.header.stamp.nanosec/1e9
        odometry['valid']=all(math.isfinite(v) for v in values) and .9<sum(v*v for v in [q.x,q.y,q.z,q.w])<1.1 and all(math.isfinite(v) and 0<=v<=.5 for v in covariance) and abs(time.time()-stamp)<.5
    node.create_subscription(Odometry,'/odom_rgbd' if rgbd else '/odom_rf2o',odom,__import__('rclpy.qos',fromlist=['qos_profile_sensor_data']).qos_profile_sensor_data)
    depth_state={'time':0.,'clear':False}
    def depth_status(msg):
        try:
            value=json.loads(msg.data);depth_state['time']=time.monotonic()
            depth_state['clear']=value.get('source')=='rgbd' and value.get('clear') is True and abs(time.time()-value.get('stamp',0))<.5
        except (ValueError,TypeError):depth_state['clear']=False
    if rgbd:node.create_subscription(String,'/onigiri/perception',depth_status,10)
    def safe_scan():
        if rgbd:return depth_state['clear'] and time.monotonic()-depth_state['time']<.5
        clearance=.5*math.hypot(config.get('body_width_m',.4),config.get('body_length_m',.4))+.1
        return time.monotonic()-scan_state['time']<.5 and scan_state['minimum']>clearance
    def safe_odom():return odometry['valid'] and time.monotonic()-odometry['time']<.5
    def velocity(msg):
        try:
            if not safe_scan() or not safe_odom():controller.stop();return
            if rgbd:
                if msg.linear.x<0 or abs(msg.linear.y)>1e-6:controller.stop();return
                controller.command(min(msg.linear.x,.1),0.,max(-.2,min(.2,msg.angular.z)))
            else:controller.command(msg.linear.x,msg.linear.y,msg.angular.z)
        except Exception as error:node.get_logger().error(str(error))
    def arm(msg):
        try:controller.arm() if msg.data else controller.stop()
        except ValueError as error:node.get_logger().error(str(error))
    def emergency(msg):
        controller.stop(emergency=True) if msg.data else controller.release()
    node.create_subscription(Twist,'/cmd_vel',velocity,10)
    node.create_subscription(TwistStamped,'/cmd_vel_stamped',lambda m:velocity(m.twist),10)
    node.create_subscription(Bool,'/onigiri/arm',arm,10)
    node.create_subscription(Bool,'/onigiri/emergency_stop',emergency,10)
    def tick():
        try:
            if config_path.read_text()!=initial_config:
                controller.stop();raise SystemExit('Configuração alterada; reinicie a base para adotar o novo perfil')
            if controller.armed and (not safe_scan() or not safe_odom()):controller.stop()
            controller.tick();msg=String();msg.data=json.dumps({'armed':controller.armed,'emergency_stop':controller.estop,'chassis':config['chassis'],'perception_source':'rgbd' if rgbd else 'lidar','perception_clear':safe_scan(),'front_only':rgbd,'lidar_clear':safe_scan() if not rgbd else False,'odometry_valid':safe_odom()});status.publish(msg)
        except Exception as error:
            controller.armed=False;node.get_logger().error(str(error))
    node.create_timer(.05,tick)
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        sink.close();node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
if __name__=='__main__':main()

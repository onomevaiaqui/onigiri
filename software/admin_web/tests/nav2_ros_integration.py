import json,math,os,signal,subprocess,tempfile,time
from pathlib import Path
import rclpy
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from lifecycle_msgs.srv import GetState
from tf2_ros import Buffer,TransformListener
root=Path(__file__).resolve().parents[3];rclpy.init();node=rclpy.create_node('onigiri_nav2_stack_test');pub=node.create_publisher(LaserScan,'/scan',10);initial=node.create_publisher(PoseWithCovarianceStamped,'/initialpose',10);navigator=ActionClient(node,NavigateToPose,'navigate_to_pose');buffer=Buffer();listener=TransformListener(buffer,node);odoms=[];node.create_subscription(Odometry,'/odom_rf2o',lambda m:odoms.append(m),10)
with tempfile.TemporaryDirectory() as directory:
 d=Path(directory);cells=bytearray([254]*200*200)
 for y in range(60,141):
  for x in range(60,141):
   if x in (60,140) or y in (60,140):cells[y*200+x]=0
 (d/'map.pgm').write_bytes(b'P5\n200 200\n255\n'+cells);(d/'map.yaml').write_text('image: map.pgm\nresolution: 0.05\norigin: [-5.0, -5.0, 0.0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.196\n')
 config={'chassis':'tank','camera':'none','lidar':True,'extrinsics_measured':True,'lidar_xyz_rpy':[0]*6,'body_width_m':.4,'body_length_m':.4,'max_track_speed_mps':.3};(d/'platform.json').write_text(json.dumps(config));env=os.environ.copy();env['ONIGIRI_PLATFORM_FILE']=str(d/'platform.json');log=(d/'log').open('w')
 process=subprocess.Popen(['/usr/bin/python3',str(root/'software/robot_runtime/stack.py'),str(d),str(d/'map.yaml')],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 try:
  deadline=time.monotonic()+22;last_initial=0;step=0
  while time.monotonic()<deadline:
   assert process.poll() is None,(d/'log').read_text()[-6000:]
   msg=LaserScan();msg.header.frame_id='laser';msg.header.stamp=node.get_clock().now().to_msg();msg.angle_min=-math.pi;msg.angle_max=math.pi;msg.angle_increment=2*math.pi/359;msg.range_min=.1;msg.range_max=10.;msg.scan_time=.1;msg.ranges=[]
   x=min(.1,step*.0005);step+=1
   for i in range(360):
    angle=-math.pi+i*msg.angle_increment;c=math.cos(angle);ss=math.sin(angle);candidates=[]
    if abs(c)>1e-8:candidates.extend(v for v in [(-2-x)/c,(2-x)/c] if v>0)
    if abs(ss)>1e-8:candidates.extend(v for v in [-2/ss,2/ss] if v>0)
    msg.ranges.append(min(candidates));pub.publish(msg)
   if time.monotonic()-last_initial>2:
    pose=PoseWithCovarianceStamped();pose.header.frame_id='map';pose.header.stamp=node.get_clock().now().to_msg();pose.pose.pose.orientation.w=1.;pose.pose.covariance[0]=pose.pose.covariance[7]=.25;pose.pose.covariance[35]=.1;initial.publish(pose);last_initial=time.monotonic()
   rclpy.spin_once(node,timeout_sec=.05)
   text=(d/'log').read_text()
   if text.count('Managed nodes are active')>=2 and navigator.server_is_ready() and len(odoms)>10:
    try:buffer.lookup_transform('map','base_footprint',rclpy.time.Time());break
    except Exception:pass
  else:raise AssertionError('Odometria: '+str(odoms[-1] if odoms else None)+'\n'+(d/'log').read_text()[:2500]+'\n'+(d/'log').read_text()[-4500:])
  print('PASS: Nav2 real ativo com mapa, AMCL, RF2O e TF map→base; LiDAR sintético; nenhum motor iniciado')
 finally:
  if process.poll() is None:os.killpg(process.pid,signal.SIGINT)
  try:process.wait(timeout=7)
  except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
  log.close();node.destroy_node();rclpy.shutdown()

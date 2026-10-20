import json,math,os,sys,tempfile,time,subprocess,signal,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[3];sys.path.insert(0,str(root/'software/admin_web'))
from app.mapping import MapManager
import rclpy,numpy as np
from sensor_msgs.msg import Image,CameraInfo
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import TransformStamped
from std_msgs.msg import String
from nav_msgs.msg import OccupancyGrid,Odometry
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster
from tf2_ros import Buffer,TransformListener
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
rclpy.init();node=rclpy.create_node('onigiri_rgbd_integration')
rgb_pub=node.create_publisher(Image,'/camera/color/image_raw',10);depth_pub=node.create_publisher(Image,'/camera/depth/image_raw',10);info_pub=node.create_publisher(CameraInfo,'/camera/color/camera_info',10)
transforms=StaticTransformBroadcaster(node);tf=TransformStamped();tf.header.frame_id='camera_link';tf.child_frame_id='camera_color_optical_frame';tf.transform.rotation.x=-.5;tf.transform.rotation.y=.5;tf.transform.rotation.z=-.5;tf.transform.rotation.w=.5;transforms.sendTransform(tf)
perception=[];node.create_subscription(String,"/onigiri/perception",lambda msg:perception.append(json.loads(msg.data)),10)
buffer=Buffer();listener=TransformListener(buffer,node);navigator=ActionClient(node,NavigateToPose,'navigate_to_pose')
maps=[];odoms=[];node.create_subscription(OccupancyGrid,'/map',lambda msg:maps.append(msg),10);node.create_subscription(Odometry,'/odom_rgbd',lambda msg:odoms.append(msg),qos_profile_sensor_data)
texture=np.random.default_rng(42).integers(0,256,(240,320,3),dtype=np.uint8).tobytes();depth=(np.ones((240,320),dtype=np.uint16)*2000).tobytes()
manager=None
with tempfile.TemporaryDirectory(prefix='onigiri-rgbd-test-') as folder:
 try:
  path=Path(folder);config=path/'platform.json';config.write_text(json.dumps({'chassis':'tank','camera':'gemini2','lidar':False,'extrinsics_measured':True,'camera_xyz_rpy':[.2,0,.4,0,0,0],'body_width_m':.4,'body_length_m':.4,'max_track_speed_mps':.3}));os.environ['ONIGIRI_PLATFORM_FILE']=str(config);os.environ['ONIGIRI_RGBD_ENABLED']='1'
  manager=MapManager(path/'maps',root/'deploy/scripts/mapping_worker.sh',True);manager.start(rgbd=True)
  deadline=time.monotonic()+25
  while time.monotonic()<deadline:
   stamp=node.get_clock().now().to_msg()
   rgb=Image();rgb.header.stamp=stamp;rgb.header.frame_id='camera_color_optical_frame';rgb.width=320;rgb.height=240;rgb.encoding='rgb8';rgb.step=960;rgb.data=texture
   dep=Image();dep.header=rgb.header;dep.width=320;dep.height=240;dep.encoding='16UC1';dep.step=640;dep.data=depth
   info=CameraInfo();info.header=rgb.header;info.width=320;info.height=240;info.k=[250.,0.,159.5,0.,250.,119.5,0.,0.,1.];info.p=[250.,0.,159.5,0.,0.,250.,119.5,0.,0.,0.,1.,0.];info.distortion_model='plumb_bob';info.d=[0.]*5
   rgb_pub.publish(rgb);depth_pub.publish(dep);info_pub.publish(info)
   wait=time.monotonic()+.1
   while time.monotonic()<wait:rclpy.spin_once(node,timeout_sec=.01)
   assert manager.status()['running'],(path/'maps/slam.log').read_text()[-6000:]
   if len(odoms)>5 and perception and perception[-1].get('clear') and maps and maps[-1].info.width>0 and manager.preview()['state']=='live':break
  else:raise AssertionError(str(perception[-1:] if perception else 'perception absent')+'\n'+(path/'maps/slam.log').read_text()[-3500:])
  assert all(math.isfinite(msg.pose.pose.position.x) for msg in odoms)
  print('PASS: odometria RGB-D e mapa real RTAB-Map com imagens sintéticas, sem LiDAR')
  result=manager.save('rgbd-test');assert result['name']=='rgbd-test'
  saved=path/'maps/rgbd-test';assert (saved/'rtabmap.db').stat().st_size>1000;assert (saved/'map.pgm').is_file()
  print('PASS: prévia do mesmo painel, YAML/PGM e banco visual salvos atomicamente')
  manager.stop();before=hashlib.sha256((saved/'rtabmap.db').read_bytes()).hexdigest()
  log=(path/'localization.log').open('w');process=subprocess.Popen(['/usr/bin/python3',str(root/'software/robot_runtime/stack.py'),str(path),str(saved/'map.yaml')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   deadline=time.monotonic()+25
   while time.monotonic()<deadline:
    stamp=node.get_clock().now().to_msg();rgb.header.stamp=stamp;dep.header.stamp=stamp;info.header.stamp=stamp
    rgb_pub.publish(rgb);depth_pub.publish(dep);info_pub.publish(info)
    wait=time.monotonic()+.1
    while time.monotonic()<wait:rclpy.spin_once(node,timeout_sec=.01)
    assert process.poll() is None,(path/'localization.log').read_text()[-6000:]
    if navigator.server_is_ready() and 'Managed nodes are active' in (path/'localization.log').read_text():
     try:
      pose=buffer.lookup_transform('map','base_footprint',rclpy.time.Time());stamp=pose.header.stamp.sec+pose.header.stamp.nanosec/1e9
      if time.time()-stamp<1:break
     except Exception:pass
   else:raise AssertionError((path/'localization.log').read_text()[-9000:])
   assert hashlib.sha256((saved/'rtabmap.db').read_bytes()).hexdigest()==before
   print('PASS: banco visual reaberto, localização RGB-D e Nav2 real ativos; arquivo salvo preservado')
  finally:
   if process.poll() is None:os.killpg(process.pid,signal.SIGINT)
   try:process.wait(timeout=7)
   except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
   log.close()
 finally:
  if manager:manager.stop()
  node.destroy_node();rclpy.shutdown()

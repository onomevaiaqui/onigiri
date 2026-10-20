import json,os,pty,signal,subprocess,sys,tempfile,time,uuid
from pathlib import Path
root=Path(__file__).resolve().parents[3];sys.path.insert(0,str(root/'software/admin_web'))
from app.runtime import Process
import rclpy
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist,TransformStamped
from std_msgs.msg import Bool
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionServer, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.task import Future
rclpy.init();node=rclpy.create_node('onigiri_runtime_integration');scan=node.create_publisher(LaserScan,'/scan',10);twist=node.create_publisher(Twist,'/cmd_vel',10);arm=node.create_publisher(Bool,'/onigiri/arm',10)
odom_pub=node.create_publisher(Odometry,"/odom_rf2o",10)
broadcast=TransformBroadcaster(node)
slow=[False]
async def execute(goal):
 if slow[0]:
  ready=Future();timer=None
  def complete():
   timer.cancel()
   if not ready.done():ready.set_result(None)
  timer=node.create_timer(.6,complete);await ready;node.destroy_timer(timer)
 if goal.is_cancel_requested:goal.canceled()
 else:goal.succeed()
 return NavigateToPose.Result()
action=ActionServer(node,NavigateToPose,'navigate_to_pose',execute_callback=execute,cancel_callback=lambda g:CancelResponse.ACCEPT,callback_group=ReentrantCallbackGroup())
master,slave=pty.openpty();os.set_blocking(master,False);bridge=Process(root/'deploy/scripts/robot_bridge_worker.sh',True);base=None
with tempfile.TemporaryDirectory() as directory:
 try:
  config={'extrinsics_measured':True,'chassis':'tank','motor_driver':'sabertooth2x32','serial_port':os.ttyname(slave),'serial_address':128,'serial_baud':9600,'wheelbase_m':.4,'track_separation_m':.4,'max_track_speed_mps':1,'power_limit':.2,'motor_inversions':[False,False]}
  path=Path(directory)/'platform.json';path.write_text(json.dumps(config));env=os.environ.copy();env.update(ONIGIRI_MOTION_ENABLED='1',ONIGIRI_PLATFORM_FILE=str(path))
  base=subprocess.Popen(['/usr/bin/python3',str(root/'software/robot_runtime/base_node.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,start_new_session=True)
  bridge.start()
  def spin(seconds,velocity=False,odom_enabled=True):
   deadline=time.monotonic()+seconds
   while time.monotonic()<deadline:
    msg=LaserScan();msg.header.frame_id='laser';msg.header.stamp=node.get_clock().now().to_msg();msg.range_min=.1;msg.range_max=10.;msg.angle_min=-3.14;msg.angle_max=3.14;msg.angle_increment=.1;msg.ranges=[2.]*63;scan.publish(msg)
    measured=Odometry();measured.header.stamp=node.get_clock().now().to_msg();measured.pose.pose.orientation.w=1.;
    if odom_enabled:odom_pub.publish(measured)
    tf=TransformStamped();tf.header.frame_id='map';tf.child_frame_id='base_footprint';tf.header.stamp=node.get_clock().now().to_msg();tf.transform.rotation.w=1.;broadcast.sendTransform(tf)
    if velocity:
     command=Twist();command.linear.x=.5;twist.publish(command)
    rclpy.spin_once(node,timeout_sec=.04)
  spin(2)
  assert base.poll() is None,base.stderr.read().decode()
  bridge.send('arm');spin(.5,True)
  status=bridge.status()['telemetry'];assert status['base']['armed'],status
  data=os.read(master,65536);assert bytes([128,0,13,13]) in data,data
  spin(.6);assert not bridge.status()['telemetry']['base']['armed']
  print('PASS: ROS -> base -> serial virtual, potência limitada e parada por perda de comandos')
  bridge.send('arm');spin(.3,True);spin(.7,True,False);assert not bridge.status()['telemetry']['base']['armed']
  print('PASS: base para por perda de odometria mesmo recebendo comandos de velocidade')
  spin(.3)
  bridge.send('arm');spin(.3);bridge.send('navigate',x=1.,y=0.,yaw=0.);spin(.6)
  status=bridge.status()['telemetry'];assert status['phase']=='arrived',status
  print('PASS: posição TF, ação NavigateToPose e chegada confirmada por servidor sintético')
  slow[0]=True;bridge.send('arm');spin(.3);bridge.send('navigate',x=1.,y=0.,yaw=0.);spin(.1);bridge.send('cancel');bridge.send('arm');spin(.35)
  status=bridge.status()['telemetry'];assert not status['base']['armed'];assert 'Aguarde' in status.get('error',''),status
  spin(.8);assert bridge.status()['telemetry']['phase']=='cancelled'
  print('PASS: cancelamento durante aceitação pendente, confirmação ROS e rearme bloqueado até terminar')
  bridge.send('emergency_stop');spin(.4);assert bridge.status()['telemetry']['base']['emergency_stop']
  bridge.send('release');spin(.4);status=bridge.status()['telemetry'];assert not status['base']['armed'] and not status['base']['emergency_stop']
  print('PASS: parada de emergência e liberação sem rearme automático')
 finally:
  bridge.stop()
  if base and base.poll() is None:
   os.killpg(base.pid,signal.SIGINT)
   try:base.wait(timeout=4)
   except subprocess.TimeoutExpired:os.killpg(base.pid,signal.SIGKILL);base.wait()
  os.close(master);os.close(slave);node.destroy_node();rclpy.shutdown()

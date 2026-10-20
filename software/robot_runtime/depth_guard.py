"""Front RGB-D clearance and point cloud. No commands; missing depth never means free."""
import json,math,os,struct,time
from pathlib import Path

def assess(width,height,step,encoding,data,k,rotation,translation,clearance,max_height=1.5,bigendian=False):
    size={'16UC1':2,'32FC1':4}.get(encoding)
    if not size or width<=0 or height<=0 or width*height>3_000_000 or step<width*size or len(data)<step*height:raise ValueError('Profundidade inválida')
    fx,fy,cx,cy=k[0],k[4],k[2],k[5]
    if fx<=0 or fy<=0:raise ValueError('Calibração da câmera inválida')
    points=[];valid=0;total=0;nearest=float('inf');stride=max(4,(width+79)//80)
    for y in range(0,height,stride):
        for x in range(0,width,stride):
            total+=1;value=struct.unpack_from(('>' if bigendian else '<')+('H' if size==2 else 'f'),data,y*step+x*size)[0];z=value/1000 if size==2 else value
            if not math.isfinite(z) or not .15<=z<=5.:continue
            valid+=1;v=[(x-cx)*z/fx,(y-cy)*z/fy,z]
            p=[sum(rotation[i][j]*v[j] for j in range(3))+translation[i] for i in range(3)]
            if not all(math.isfinite(a) for a in p):continue
            points.append(p)
            if .05<=p[2]<=max_height:nearest=min(nearest,math.hypot(p[0],p[1]))
    ratio=valid/max(total,1)
    return {'clear':ratio>=.5 and nearest>clearance,'valid_ratio':ratio,'nearest_m':nearest if math.isfinite(nearest) else None,'front_only':True},points

def main():
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Image,CameraInfo,PointCloud2
    from sensor_msgs_py.point_cloud2 import create_cloud_xyz32
    from std_msgs.msg import String,Header
    from tf2_ros import Buffer,TransformListener
    root=Path(__file__).resolve().parents[2];config=json.loads(Path(os.environ.get('ONIGIRI_PLATFORM_FILE',root/'data/platform.json')).read_text())
    rclpy.init();node=Node('onigiri_depth_guard');buffer=Buffer();listener=TransformListener(buffer,node)
    state={'info':None,'last':0.};status=node.create_publisher(String,'/onigiri/perception',10);cloud=node.create_publisher(PointCloud2,'/camera/perception/points',qos_profile_sensor_data)
    def info(msg):state['info']=msg
    node.create_subscription(CameraInfo,os.environ.get('ONIGIRI_CAMERA_INFO_TOPIC','/camera/color/camera_info'),info,qos_profile_sensor_data)
    def depth(msg):
        if time.monotonic()-state['last']<.15:return
        state['last']=time.monotonic();payload={'clear':False,'front_only':True,'source':'rgbd','stamp':msg.header.stamp.sec+msg.header.stamp.nanosec/1e9}
        try:
            calibration=state['info']
            if calibration is None or calibration.width!=msg.width or calibration.height!=msg.height:raise ValueError('A profundidade precisa estar alinhada ao RGB e à sua calibração')
            if abs(node.get_clock().now().nanoseconds/1e9-payload['stamp'])>.5:raise ValueError('Profundidade atrasada')
            tf=buffer.lookup_transform('base_footprint',calibration.header.frame_id,rclpy.time.Time());q=tf.transform.rotation;t=tf.transform.translation
            x,y,z,w=q.x,q.y,q.z,q.w
            rotation=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
            assessment,points=assess(msg.width,msg.height,msg.step,msg.encoding,bytes(msg.data),calibration.k,rotation,[t.x,t.y,t.z],.5*math.hypot(config.get('body_width_m',.5),config.get('body_length_m',.5))+.1,bigendian=msg.is_bigendian)
            payload.update(assessment);header=Header();header.frame_id='base_footprint';header.stamp=msg.header.stamp;cloud.publish(create_cloud_xyz32(header,points))
        except Exception as error:payload['error']=str(error)
        output=String();output.data=json.dumps(payload,allow_nan=False);status.publish(output)
    node.create_subscription(Image,os.environ.get('ONIGIRI_CAMERA_DEPTH_TOPIC','/camera/depth/image_raw'),depth,qos_profile_sensor_data)
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
if __name__=='__main__':main()

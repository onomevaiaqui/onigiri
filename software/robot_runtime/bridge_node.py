#!/usr/bin/env python3
"""Local file RPC to ROS action, initial pose and measured TF. No velocity publisher."""
import json,math,os,sys,time
from pathlib import Path

def main():
    import rclpy
    from rclpy.node import Node
    from rclpy.action import ActionClient
    from nav2_msgs.action import NavigateToPose
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from std_msgs.msg import Bool, String
    from tf2_ros import Buffer,TransformListener
    rclpy.init();node=Node('onigiri_dashboard_bridge')
    directory=Path(sys.argv[1]);buffer=Buffer();listener=TransformListener(buffer,node)
    navigator=ActionClient(node,NavigateToPose,'navigate_to_pose')
    arm=node.create_publisher(Bool,'/onigiri/arm',10);estop=node.create_publisher(Bool,'/onigiri/emergency_stop',10)
    pose_pub=node.create_publisher(PoseWithCovarianceStamped,'/initialpose',10)
    state={'phase':'idle','base':None,'pose':None,'last_request':None};active=None;generation=0;outstanding=set()
    def base(msg):
        try:state['base']={**json.loads(msg.data),'received_at':time.time()}
        except ValueError:pass
    node.create_subscription(String,'/onigiri/base/status',base,10)
    def boolean(pub,value):msg=Bool();msg.data=value;pub.publish(msg)
    def cancel():
        nonlocal generation,active
        generation+=1
        if active:active.cancel_goal_async()
        active=None;state['phase']='cancel_pending' if outstanding else 'cancelled';boolean(arm,False)
    def accepted(future,token):
        nonlocal active
        try:
            handle=future.result()
            if token!=generation:
                if handle.accepted:
                    handle.get_result_async().add_done_callback(lambda f:finished(f,token));handle.cancel_goal_async()
                else:outstanding.discard(token)
                return
            if not handle.accepted:outstanding.discard(token);state['phase']='rejected';return
            active=handle;state['phase']='navigating'
            handle.get_result_async().add_done_callback(lambda f:finished(f,token))
        except Exception as error:outstanding.discard(token);state['phase']='failed';state['error']=str(error)
    def finished(future,token):
        nonlocal active
        outstanding.discard(token)
        if token!=generation:
            if not outstanding and state['phase']=='cancel_pending':state['phase']='cancelled'
            return
        active=None
        try:state['phase']='arrived' if future.result().status==4 else 'failed'
        except Exception:state['phase']='failed'
        boolean(arm,False)
    def execute(request):
        nonlocal generation
        operation=request['operation']
        if operation=='cancel':cancel();return
        if operation=='emergency_stop':cancel();boolean(estop,True);return
        if operation=='release':boolean(estop,False);return
        if operation=='arm':
            if outstanding:raise ValueError('Aguarde o cancelamento do objetivo anterior antes de rearmar')
            boolean(arm,True);return
        if operation=='initial_pose':
            if state['phase'] in ('navigating','pending'):raise ValueError('Cancele a navegação antes de reposicionar')
            pose=PoseWithCovarianceStamped();pose.header.frame_id='map';pose.header.stamp=node.get_clock().now().to_msg()
            pose.pose.pose.position.x=request['x'];pose.pose.pose.position.y=request['y']
            pose.pose.pose.orientation.z=math.sin(request['yaw']/2);pose.pose.pose.orientation.w=math.cos(request['yaw']/2)
            pose.pose.covariance[0]=pose.pose.covariance[7]=.25;pose.pose.covariance[35]=.0685;pose_pub.publish(pose);return
        if operation=='navigate':
            if outstanding:raise ValueError('Cancele o destino atual e aguarde a confirmação')
            if not navigator.server_is_ready():raise ValueError('Nav2 indisponível')
            current=state['base']
            if not current or time.time()-current['received_at']>1 or not current.get('armed'):raise ValueError('Base não armada ou sem telemetria')
            if not state['pose'] or time.time()-state['pose']['stamp']>1:raise ValueError('Localização ausente ou atrasada')
            goal=NavigateToPose.Goal();goal.pose.header.frame_id='map';goal.pose.header.stamp=node.get_clock().now().to_msg()
            goal.pose.pose.position.x=request['x'];goal.pose.pose.position.y=request['y'];goal.pose.pose.orientation.z=math.sin(request['yaw']/2);goal.pose.pose.orientation.w=math.cos(request['yaw']/2)
            generation+=1;token=generation;outstanding.add(token);state['phase']='pending'
            navigator.send_goal_async(goal).add_done_callback(lambda f:accepted(f,token));return
        raise ValueError('Operação desconhecida')
    def tick():
        try:
            transform=buffer.lookup_transform('map','base_footprint',rclpy.time.Time())
            stamp=transform.header.stamp.sec+transform.header.stamp.nanosec/1e9
            rotation=transform.transform.rotation
            state['pose']={'x':transform.transform.translation.x,'y':transform.transform.translation.y,'yaw':math.atan2(2*(rotation.w*rotation.z+rotation.x*rotation.y),1-2*(rotation.y**2+rotation.z**2)),'stamp':stamp}
        except Exception:state['pose']=None
        for path in sorted(directory.glob('request-*.json')):
            try:
                request=json.loads(path.read_text());path.unlink()
                if time.time()-request['created_at']>2:raise ValueError('Solicitação expirada')
                execute(request);state['last_request']={'id':request['id'],'ok':True};state.pop('error',None)
            except Exception as error:state['error']=str(error);state['last_request']={'id':path.stem,'ok':False}
        state['received_at']=time.time();state['nav2_ready']=navigator.server_is_ready()
        temp=directory/'status.tmp';temp.write_text(json.dumps(state));os.replace(temp,directory/'status.json')
    node.create_timer(.2,tick)
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        if rclpy.ok():cancel()
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
if __name__=='__main__':main()

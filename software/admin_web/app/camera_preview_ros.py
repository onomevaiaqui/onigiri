"""Read-only RGB Image subscriber. Driver must be started separately."""
import base64
import json
import os
import struct
import sys
import time
import zlib
from pathlib import Path

def image_png(width, height, step, encoding, data):
    channels = {"rgb8":3,"bgr8":3,"mono8":1}.get(encoding)
    if not channels:
        raise ValueError("Formato RGB não suportado: " + encoding)
    if not 0 < width <= 1920 or not 0 < height <= 1080 or step < width*channels or len(data) < step*height:
        raise ValueError("Dimensões de imagem inválidas ou superiores a 1920×1080")
    rows=[]
    # Limit browser preview to 640 px, preserving aspect ratio.
    factor=max(1,(width+639)//640,(height+479)//480)
    for y in range(0,height,factor):
        row=bytearray()
        for x in range(0,width,factor):
            pixel=data[y*step+x*channels:y*step+x*channels+channels]
            row.extend(pixel[::-1] if encoding=="bgr8" else pixel)
        rows.append(b"\0"+row)
    w=(width+factor-1)//factor;h=(height+factor-1)//factor
    def chunk(kind,value):
        return struct.pack("!I",len(value))+kind+value+struct.pack("!I",zlib.crc32(kind+value)&0xffffffff)
    return b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack("!2I5B",w,h,8,0 if channels==1 else 2,0,0,0))+chunk(b"IDAT",zlib.compress(b"".join(rows),1))+chunk(b"IEND",b"")


def depth_png(width,height,step,encoding,data,bigendian=False):
    if encoding not in ('16UC1','32FC1'):raise ValueError('Formato de profundidade não suportado')
    size=2 if encoding=='16UC1' else 4
    if not 0<width<=1920 or not 0<height<=1080 or step<width*size or len(data)<step*height:raise ValueError('Profundidade inválida')
    import math
    factor=max(1,(width+639)//640,(height+479)//480);pixels=bytearray()
    for y in range(0,height,factor):
        for x in range(0,width,factor):
            value=struct.unpack_from(('>' if bigendian else '<')+('H' if size==2 else 'f'),data,y*step+x*size)[0]
            meters=value/1000 if size==2 else value
            pixels.append(round(255*(1-min(meters,5)/5)) if math.isfinite(meters) and meters>0 else 0)
    w=(width+factor-1)//factor;h=(height+factor-1)//factor
    return image_png(w,h,w,'mono8',pixels)

def main():
    import rclpy
    from sensor_msgs.msg import Image, Imu
    from rclpy.qos import qos_profile_sensor_data
    destination=Path(sys.argv[1]);topic=sys.argv[2]
    rclpy.init();node=rclpy.create_node("onigiri_camera_preview");last=0
    def receive(message):
        nonlocal last
        now=time.monotonic()
        if now-last < .25:return
        last=now
        try:
            image=image_png(message.width,message.height,message.step,message.encoding,bytes(message.data))
            snapshot={"received_at":time.time(),"png_base64":base64.b64encode(image).decode(),"topic":topic,"frame":message.header.frame_id}
        except ValueError as error:
            snapshot={"received_at":time.time(),"error":str(error)}
        temp=destination.with_suffix(".tmp");temp.write_text(json.dumps(snapshot));os.replace(temp,destination)
    def depth(message):
        now=time.monotonic()
        if now-depth.last<.5:return
        depth.last=now
        try:
            png=depth_png(message.width,message.height,message.step,message.encoding,bytes(message.data),message.is_bigendian)
            data={'received_at':time.time(),'png_base64':base64.b64encode(png).decode(),'range_m':5}
        except ValueError as error:data={'received_at':time.time(),'error':str(error)}
        path=destination.with_name('depth.json');temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data));os.replace(temp,path)
    depth.last=0.
    def imu(message):
        if time.monotonic()-imu.last<.5:return
        imu.last=time.monotonic()
        def vector(value):return {'x':value.x,'y':value.y,'z':value.z}
        data={'received_at':time.time(),'angular_velocity':vector(message.angular_velocity),'linear_acceleration':vector(message.linear_acceleration),'frame':message.header.frame_id}
        path=destination.with_name('imu.json');temp=path.with_suffix('.tmp');
        import math
        if not all(math.isfinite(v) for vector in (data['angular_velocity'],data['linear_acceleration']) for v in vector.values()):return
        temp.write_text(json.dumps(data,allow_nan=False));os.replace(temp,path)
    imu.last=0.
    subscription=node.create_subscription(Image,topic,receive,qos_profile_sensor_data)
    depth_subscription=node.create_subscription(Image,os.environ.get('ONIGIRI_CAMERA_DEPTH_TOPIC','/camera/depth/image_raw'),depth,qos_profile_sensor_data)
    imu_subscription=node.create_subscription(Imu,os.environ.get('ONIGIRI_CAMERA_IMU_TOPIC','/camera/gyro_accel/sample'),imu,qos_profile_sensor_data)
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
if __name__=="__main__":main()

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

def main():
    import rclpy
    from sensor_msgs.msg import Image
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
    subscription=node.create_subscription(Image,topic,receive,qos_profile_sensor_data)
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
if __name__=="__main__":main()

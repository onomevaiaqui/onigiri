"""Read-only /map subscriber. Runs under system Python with ROS sourced."""
import base64
import hashlib
import json
import math
import os
import struct
import sys
import time
import zlib
from pathlib import Path


class MapRevision:
    def __init__(self):
        self.digest = None
        self.revision = 0
        self.changed_at = None

    def update(self, image, geometry, received_at):
        digest = hashlib.sha256(image + json.dumps(geometry, sort_keys=True).encode()).digest()
        if digest != self.digest:
            self.digest = digest
            self.revision += 1
            self.changed_at = received_at
        return {'revision': self.revision, 'changed_at': self.changed_at}


def map_png(width, height, cells):
    if not 0 < width <= 4096 or not 0 < height <= 4096 or width * height > 4_000_000:
        raise ValueError('Mapa excede o limite da prévia (4 milhões de células).')
    if len(cells) != width * height:
        raise ValueError('Dimensões do mapa inconsistentes.')
    table = bytes(round(255 * (1 - value / 100)) if value <= 100 else 205 for value in range(256))
    pixels = cells.translate(table)
    # ROS rows start at the bottom; PNG rows start at the top.
    rows = b''.join(b'\0' + pixels[y * width:(y + 1) * width] for y in range(height - 1, -1, -1))
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, 0, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows, 1)) + chunk(b'IEND', b''))


def main():
    import rclpy
    from nav_msgs.msg import OccupancyGrid
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
    destination = Path(sys.argv[1])
    rclpy.init()
    node = rclpy.create_node('onigiri_map_preview')
    last = 0.0
    sequence = 0
    revision = MapRevision()
    def receive(message):
        nonlocal last, sequence
        now = time.monotonic()
        if now - last < 0.2:
            return
        last = now
        try:
            if not math.isfinite(message.info.resolution) or message.info.resolution <= 0:
                raise ValueError('Resolução de mapa inválida.')
            image = map_png(message.info.width, message.info.height, message.data.tobytes())
            origin = message.info.origin
            geometry = [message.info.resolution, origin.position.x, origin.position.y, origin.position.z,
                        origin.orientation.x, origin.orientation.y, origin.orientation.z, origin.orientation.w,
                        message.header.frame_id]
            sequence += 1
            received_at = time.time()
            snapshot = {'sequence': sequence, 'received_at': received_at,
                        **revision.update(image, geometry, received_at),
                        'width': message.info.width, 'height': message.info.height,
                        'resolution': message.info.resolution, 'frame': message.header.frame_id,
                        'png_base64': base64.b64encode(image).decode()}
        except (ValueError, OverflowError) as error:
            snapshot = {'error': str(error), 'received_at': time.time()}
        temporary = destination.with_suffix('.tmp')
        temporary.write_text(json.dumps(snapshot))
        os.replace(temporary, destination)
    # Volatile is compatible with transient-local and volatile publishers; SLAM
    # continuously publishes /map. A late subscriber waits for the next message.
    qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT,
                     durability=DurabilityPolicy.VOLATILE)
    subscription = node.create_subscription(OccupancyGrid, '/map', receive, qos)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

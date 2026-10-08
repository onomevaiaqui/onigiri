#!/usr/bin/env python3
"""First obstacle-avoidance behavior for Onigiri.

The motor controller owns the LiDAR safety check. This node only requests a
slow motion through /cmd_vel. When an obstacle enters the forward sector, it
turns left briefly, then resumes forward motion. Manual UDP control from the
F710 takes priority whenever it is being sent.
"""

import math
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


FORWARD_SPEED = 0.20
TURN_LEFT_SPEED = 0.35
PUBLISH_HZ = 10.0
AVOIDANCE_DISTANCE = 0.50
FRONT_HALF_ANGLE_DEGREES = 12.0
SCAN_TIMEOUT_SECONDS = 0.50
TURN_SECONDS = 0.90


class BasicAutonomy(Node):
    def __init__(self) -> None:
        super().__init__("onigiri_autonomous_basic")
        self.publisher = self.create_publisher(Twist, "/cmd_vel", 10)
        self.create_subscription(LaserScan, "/scan", self.on_scan, 10)
        self.create_timer(1.0 / PUBLISH_HZ, self.publish_command)
        self.front_distance = None
        self.last_scan = 0.0
        self.turn_until = 0.0
        self.get_logger().info(
            "Autonomia ativa: avanca devagar; obstaculo a 0,50 m inicia giro curto para a esquerda."
        )

    def on_scan(self, scan: LaserScan) -> None:
        distances = []
        half_angle = math.radians(FRONT_HALF_ANGLE_DEGREES)
        for index, distance in enumerate(scan.ranges):
            angle = scan.angle_min + index * scan.angle_increment
            angle = math.atan2(math.sin(angle), math.cos(angle))
            if abs(angle) <= half_angle and math.isfinite(distance):
                if scan.range_min <= distance <= scan.range_max:
                    distances.append(distance)

        self.front_distance = min(distances) if distances else float("inf")
        self.last_scan = time.monotonic()

    def publish_command(self) -> None:
        command = Twist()
        now = time.monotonic()

        # Without a current LiDAR reading, do not command any movement.
        if now - self.last_scan > SCAN_TIMEOUT_SECONDS:
            self.publisher.publish(command)
            return

        if now < self.turn_until:
            command.angular.z = TURN_LEFT_SPEED
        elif self.front_distance is not None and self.front_distance < AVOIDANCE_DISTANCE:
            self.turn_until = now + TURN_SECONDS
            command.angular.z = TURN_LEFT_SPEED
            self.get_logger().info(
                f"Obstaculo a {self.front_distance:.2f} m: girando para a esquerda."
            )
        else:
            command.linear.x = FORWARD_SPEED

        self.publisher.publish(command)

    def destroy_node(self) -> None:
        # A last zero command makes shutdown intentional and immediate.
        self.publisher.publish(Twist())
        super().destroy_node()


def main() -> None:
    rclpy.init()
    node = BasicAutonomy()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

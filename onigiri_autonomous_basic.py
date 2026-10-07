#!/usr/bin/env python3
"""First safe autonomous behavior for Onigiri: advance and stop at obstacles.

The motor controller owns the LiDAR safety check. This node only requests a
slow forward motion through /cmd_vel. Manual UDP control from the F710 takes
priority whenever it is being sent.
"""

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


FORWARD_SPEED = 0.20
PUBLISH_HZ = 10.0


class BasicAutonomy(Node):
    def __init__(self) -> None:
        super().__init__("onigiri_autonomous_basic")
        self.publisher = self.create_publisher(Twist, "/cmd_vel", 10)
        self.create_timer(1.0 / PUBLISH_HZ, self.publish_forward)
        self.get_logger().info(
            "Autonomia basica ativa: avancando devagar; o LiDAR para diante de obstaculos."
        )

    def publish_forward(self) -> None:
        command = Twist()
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


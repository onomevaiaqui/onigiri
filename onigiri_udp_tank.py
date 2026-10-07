#!/usr/bin/env python3
"""Receive UDP tank commands and control the Onigiri Motor HAT."""

import socket
import time
import math

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from smbus import SMBus


I2C_ADDR = 0x6F
PORT = 5005
DEADZONE = 0.08
WATCHDOG_SECONDS = 0.30
# The LiDAR is centered and its 0-degree direction is the robot's front.
# Forward movement is inhibited below this distance; reversing and turning remain available.
FRONT_STOP_DISTANCE = 0.35
SCAN_TIMEOUT_SECONDS = 0.50
FRONT_HALF_ANGLE_DEGREES = 12.0


class MotorHAT:
    CHANNELS = {
        1: (8, 10, 9),
        2: (13, 11, 12),
        3: (2, 4, 3),
    }

    def __init__(self):
        self.bus = SMBus(1)
        self.bus.write_byte_data(I2C_ADDR, 0x01, 0x04)
        self.bus.write_byte_data(I2C_ADDR, 0x00, 0x11)
        self.bus.write_byte_data(I2C_ADDR, 0xFE, 0x03)
        self.bus.write_byte_data(I2C_ADDR, 0x00, 0x01)
        time.sleep(0.01)
        self.bus.write_byte_data(I2C_ADDR, 0x00, 0x81)
        self.stop_all()

    def _pwm(self, channel: int, on: int, off: int) -> None:
        reg = 0x06 + 4 * channel
        for offset, value in enumerate((on & 0xFF, on >> 8, off & 0xFF, off >> 8)):
            self.bus.write_byte_data(I2C_ADDR, reg + offset, value)

    def set_motor(self, number: int, value: float) -> None:
        pwm_channel, in1, in2 = self.CHANNELS[number]
        value = max(-1.0, min(1.0, value))

        if abs(value) < DEADZONE:
            # Short brake: stops the robot quickly whenever control is released.
            self._pwm(in1, 4096, 0)
            self._pwm(in2, 4096, 0)
            self._pwm(pwm_channel, 4096, 0)
            return

        if value > 0:
            self._pwm(in1, 4096, 0)
            self._pwm(in2, 0, 4096)
        else:
            self._pwm(in1, 0, 4096)
            self._pwm(in2, 4096, 0)

        self._pwm(pwm_channel, 0, int(abs(value) * 4095))

    def drive(self, forward: float, turn_right: float, lateral_right: float) -> None:
        m1 = forward + turn_right
        m2 = forward - turn_right
        scale = max(1.0, abs(m1), abs(m2))
        self.set_motor(1, m1 / scale)
        self.set_motor(2, m2 / scale)
        self.set_motor(3, lateral_right)

    def stop_all(self) -> None:
        for motor in self.CHANNELS:
            self.set_motor(motor, 0.0)

    def close(self) -> None:
        self.stop_all()
        self.bus.close()


def parse_command(payload: bytes) -> tuple[float, float, float]:
    forward_text, turn_text, lateral_text = payload.decode("ascii").strip().split(",", 2)
    return float(forward_text), float(turn_text), float(lateral_text)


class OnigiriBase(Node):
    def __init__(self) -> None:
        super().__init__("onigiri_base")
        self.hat = MotorHAT()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", PORT))
        self.sock.setblocking(False)
        self.last_command = 0.0
        self.last_udp = 0.0
        self.front_distance = None
        self.last_scan = 0.0
        self.last_guard_log = 0.0

        self.create_subscription(Twist, "/cmd_vel", self.on_cmd_vel, 10)
        self.create_subscription(LaserScan, "/scan", self.on_scan, 10)
        self.create_timer(0.02, self.poll)
        self.get_logger().info(
            f"Pronto: UDP na porta {PORT}, /cmd_vel e protecao frontal do LiDAR em {FRONT_STOP_DISTANCE:.2f} m."
        )

    def on_scan(self, scan: LaserScan) -> None:
        distances = []
        half_angle = math.radians(FRONT_HALF_ANGLE_DEGREES)
        for index, distance in enumerate(scan.ranges):
            angle = scan.angle_min + index * scan.angle_increment
            # Normalizes to [-pi, pi], so 0 degrees means straight ahead.
            angle = math.atan2(math.sin(angle), math.cos(angle))
            if abs(angle) <= half_angle and math.isfinite(distance):
                if scan.range_min <= distance <= scan.range_max:
                    distances.append(distance)

        self.front_distance = min(distances) if distances else float("inf")
        self.last_scan = time.monotonic()

    def forward_is_safe(self) -> bool:
        if time.monotonic() - self.last_scan > SCAN_TIMEOUT_SECONDS:
            return False
        return self.front_distance is not None and self.front_distance >= FRONT_STOP_DISTANCE

    def apply(self, forward: float, turn_right: float, lateral_right: float) -> None:
        if forward > 0.0 and not self.forward_is_safe():
            forward = 0.0
            now = time.monotonic()
            if now - self.last_guard_log > 1.0:
                distance = self.front_distance
                description = "sem leitura recente" if distance is None else f"{distance:.2f} m"
                self.get_logger().warning(
                    f"Movimento para frente bloqueado pelo LiDAR ({description})."
                )
                self.last_guard_log = now
        self.hat.drive(forward, turn_right, lateral_right)
        self.last_command = time.monotonic()

    def on_cmd_vel(self, msg: Twist) -> None:
        # Enquanto o F710 envia pacotes, ele tem prioridade sobre autonomia.
        if time.monotonic() - self.last_udp < WATCHDOG_SECONDS:
            return

        # Convenção ROS: x = frente, y = esquerda, z angular = anti-horário.
        self.apply(
            msg.linear.x,
            -msg.angular.z,
            -msg.linear.y,
        )

    def poll(self) -> None:
        while True:
            try:
                payload, _sender = self.sock.recvfrom(64)
            except BlockingIOError:
                break

            try:
                forward, turn_right, lateral_right = parse_command(payload)
            except (UnicodeDecodeError, ValueError):
                continue

            self.last_udp = time.monotonic()
            self.apply(forward, turn_right, lateral_right)

        if time.monotonic() - self.last_command > WATCHDOG_SECONDS:
            self.hat.stop_all()

    def destroy_node(self) -> None:
        self.sock.close()
        self.hat.close()
        super().destroy_node()


def main() -> None:
    rclpy.init()
    node = OnigiriBase()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

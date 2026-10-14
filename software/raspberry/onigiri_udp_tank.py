#!/usr/bin/env python3
"""Receive UDP tank commands and control the Onigiri Motor HAT."""

import socket
import time
import math

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_srvs.srv import SetBool
from std_msgs.msg import String
from smbus import SMBus


I2C_ADDR = 0x6F
PORT = 5005
DEADZONE = 0.08
WATCHDOG_SECONDS = 0.30
# The LiDAR is centered and scans 360 degrees. Translational motion is
# inhibited only in the direction where an obstacle is too close. Turning is
# intentionally still allowed so the operator can free the robot.
FRONT_STOP_DISTANCE = 0.35
REAR_STOP_DISTANCE = 0.35
LATERAL_STOP_DISTANCE = 0.35
SCAN_TIMEOUT_SECONDS = 0.50
GUARD_HALF_ANGLE_DEGREES = 12.0


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
        self.last_manual_motion = 0.0
        self.distances = {
            "frente": None,
            "re": None,
            "direita": None,
            "esquerda": None,
        }
        self.last_scan = 0.0
        self.last_guard_log = 0.0

        self.create_subscription(Twist, "/cmd_vel", self.on_cmd_vel, 10)
        self.mission_cancel_publisher = self.create_publisher(
            String, "/onigiri/mission/cancel", 10
        )
        self.autonomy_client = self.create_client(SetBool, "/onigiri_autonomous/set_enabled")
        self.create_subscription(LaserScan, "/scan", self.on_scan, 10)
        self.create_timer(0.02, self.poll)
        self.get_logger().info(
            "Pronto: UDP na porta %s, /cmd_vel e protecao 360 graus do LiDAR em %.2f m."
            % (PORT, FRONT_STOP_DISTANCE)
        )

    def on_scan(self, scan: LaserScan) -> None:
        sectors = {name: [] for name in self.distances}
        half_angle = math.radians(GUARD_HALF_ANGLE_DEGREES)
        for index, distance in enumerate(scan.ranges):
            angle = scan.angle_min + index * scan.angle_increment
            # Normalizes to [-pi, pi], so 0 degrees means straight ahead.
            angle = math.atan2(math.sin(angle), math.cos(angle))
            if not math.isfinite(distance):
                continue
            if not scan.range_min <= distance <= scan.range_max:
                continue

            if abs(angle) <= half_angle:
                sectors["frente"].append(distance)
            elif abs(abs(angle) - math.pi) <= half_angle:
                sectors["re"].append(distance)
            elif abs(angle + math.pi / 2) <= half_angle:
                sectors["direita"].append(distance)
            elif abs(angle - math.pi / 2) <= half_angle:
                sectors["esquerda"].append(distance)

        self.distances = {
            name: min(values) if values else float("inf")
            for name, values in sectors.items()
        }
        self.last_scan = time.monotonic()

    def direction_is_safe(self, direction: str, minimum_distance: float) -> bool:
        if time.monotonic() - self.last_scan > SCAN_TIMEOUT_SECONDS:
            return False
        distance = self.distances[direction]
        return distance is not None and distance >= minimum_distance

    def block_if_unsafe(
        self, value: float, direction: str, minimum_distance: float
    ) -> float:
        if value <= 0.0 or self.direction_is_safe(direction, minimum_distance):
            return value

        now = time.monotonic()
        if now - self.last_guard_log > 1.0:
            distance = self.distances[direction]
            description = "sem leitura recente" if distance is None else f"{distance:.2f} m"
            self.get_logger().warning(
                f"Movimento para {direction} bloqueado pelo LiDAR ({description})."
            )
            self.last_guard_log = now
        return 0.0

    def apply(self, forward: float, turn_right: float, lateral_right: float) -> None:
        forward = self.block_if_unsafe(forward, "frente", FRONT_STOP_DISTANCE)
        forward = -self.block_if_unsafe(-forward, "re", REAR_STOP_DISTANCE)
        lateral_right = self.block_if_unsafe(
            lateral_right, "direita", LATERAL_STOP_DISTANCE
        )
        lateral_right = -self.block_if_unsafe(
            -lateral_right, "esquerda", LATERAL_STOP_DISTANCE
        )
        self.hat.drive(forward, turn_right, lateral_right)
        self.last_command = time.monotonic()

    def on_cmd_vel(self, msg: Twist) -> None:
        # Enquanto o F710 envia pacotes, ele tem prioridade sobre autonomia.
        if time.monotonic() - self.last_manual_motion < WATCHDOG_SECONDS:
            return

        # Convenção ROS: x = frente, y = esquerda, z angular = anti-horário.
        self.apply(
            msg.linear.x,
            -msg.angular.z,
            -msg.linear.y,
        )

    def set_autonomy(self, enabled: bool) -> None:
        if not self.autonomy_client.service_is_ready():
            self.get_logger().warning("Servico de autonomia ainda nao esta disponivel.")
            return

        request = SetBool.Request()
        request.data = enabled
        future = self.autonomy_client.call_async(request)
        future.add_done_callback(self.on_autonomy_response)

    def on_autonomy_response(self, future) -> None:
        try:
            response = future.result()
            self.get_logger().info(response.message)
        except Exception as error:
            self.get_logger().error(f"Falha ao alternar autonomia: {error}")

    def poll(self) -> None:
        while True:
            try:
                payload, _sender = self.sock.recvfrom(64)
            except BlockingIOError:
                break

            try:
                message = payload.decode("ascii").strip()
            except (UnicodeDecodeError, ValueError):
                continue

            if message == "AUTO_ON":
                self.set_autonomy(True)
                continue
            if message == "AUTO_OFF":
                self.set_autonomy(False)
                continue
            if message == "MISSION_CANCEL":
                self.mission_cancel_publisher.publish(String(data="manual_override"))
                self.hat.stop_all()
                self.last_command = time.monotonic()
                continue

            try:
                forward, turn_right, lateral_right = parse_command(payload)
            except ValueError:
                continue

            moving = max(abs(forward), abs(turn_right), abs(lateral_right)) >= DEADZONE
            if moving:
                self.last_manual_motion = time.monotonic()
                self.apply(forward, turn_right, lateral_right)
            elif time.monotonic() - self.last_manual_motion < WATCHDOG_SECONDS:
                # Stops immediately after the operator releases a moving stick.
                self.apply(0.0, 0.0, 0.0)

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

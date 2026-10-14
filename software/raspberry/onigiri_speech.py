#!/usr/bin/env python3
"""Speak mission messages with the local Linux speech engine."""

import shutil
import subprocess

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class OnigiriSpeech(Node):
    def __init__(self) -> None:
        super().__init__("onigiri_speech")
        self.engine = shutil.which("espeak-ng")
        self.create_subscription(String, "/onigiri/speech", self.speak, 10)
        if self.engine is None:
            self.get_logger().warning(
                "espeak-ng nao encontrado. Mensagens de fala serao registradas somente no log."
            )
        else:
            self.get_logger().info("Saida de voz pronta em /onigiri/speech.")

    def speak(self, message: String) -> None:
        self.get_logger().info(f"Fala: {message.data}")
        if self.engine is None:
            return
        subprocess.Popen(
            [self.engine, "-v", "pt-br", message.data],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def main() -> None:
    rclpy.init()
    node = OnigiriSpeech()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

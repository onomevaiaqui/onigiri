#!/usr/bin/env python3
"""Mission workflow for destination guidance with Nav2.

This node is intentionally inactive until it receives a textual request on
/onigiri/voice_command or /onigiri/mission/request. A future speech-recognition
node only needs to publish the recognized phrase on that topic.
"""

import json
import math
import re
import time
import unicodedata
from pathlib import Path

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import String


DEFAULT_DESTINATIONS_FILE = "/home/onigiri/onigiri/config/destinations.json"
ARRIVAL_WAIT_SECONDS = 15.0


def normalize(text: str) -> str:
    """Normalize Portuguese input without losing meaningful words."""
    decomposed = unicodedata.normalize("NFD", text.casefold())
    without_accents = "".join(character for character in decomposed if not unicodedata.combining(character))
    return " ".join(without_accents.split())


def contains_phrase(request: str, phrase: str) -> bool:
    """Match a complete registered expression, never part of another word."""
    return bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", request))


def quaternion_from_yaw(yaw: float) -> tuple[float, float]:
    return math.sin(yaw / 2.0), math.cos(yaw / 2.0)


class MissionManager(Node):
    def __init__(self) -> None:
        super().__init__("onigiri_mission_manager")
        self.declare_parameter("destinations_file", DEFAULT_DESTINATIONS_FILE)
        self.declare_parameter("arrival_wait_seconds", ARRIVAL_WAIT_SECONDS)

        self.destinations_file = Path(
            self.get_parameter("destinations_file").value
        ).expanduser()
        self.arrival_wait_seconds = float(
            self.get_parameter("arrival_wait_seconds").value
        )
        self.destinations, self.home_name = self.load_destinations()

        self.navigator = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self.speech_publisher = self.create_publisher(String, "/onigiri/speech", 10)
        self.create_subscription(String, "/onigiri/voice_command", self.on_request, 10)
        self.create_subscription(String, "/onigiri/mission/request", self.on_request, 10)
        self.create_subscription(String, "/onigiri/mission/cancel", self.on_cancel, 10)
        self.create_timer(0.2, self.tick)

        self.active_goal = None
        self.phase = "idle"
        self.current_destination = None
        self.wait_until = 0.0
        self.get_logger().info(
            "Missões prontas. Aguardo pedido em /onigiri/voice_command ou /onigiri/mission/request."
        )

    def load_destinations(self) -> tuple[dict[str, dict], str]:
        try:
            content = json.loads(self.destinations_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(
                f"Nao foi possivel abrir destinos em {self.destinations_file}: {error}"
            ) from error

        destinations = {item["name"]: item for item in content["destinations"]}
        home_name = content["home"]
        if home_name not in destinations:
            raise RuntimeError("O destino configurado como home nao existe.")
        return destinations, home_name

    def say(self, phrase: str) -> None:
        self.speech_publisher.publish(String(data=phrase))
        self.get_logger().info(f"Fala: {phrase}")

    def find_destination(self, request: str) -> dict | None:
        request = normalize(request)
        candidates: list[tuple[int, dict]] = []
        for destination in self.destinations.values():
            names = [destination["name"], *destination.get("aliases", [])]
            for name in names:
                normalized_name = normalize(name)
                if normalized_name and contains_phrase(request, normalized_name):
                    candidates.append((len(normalized_name), destination))
        if candidates:
            # A frase mais específica evita que "escritório 2" seja confundido
            # com "escritório" quando ambos estiverem cadastrados.
            return max(candidates, key=lambda item: item[0])[1]
        return None

    def on_request(self, message: String) -> None:
        if self.phase != "idle":
            self.say("Já estou realizando uma missão. Diga parar para cancelar.")
            return

        destination = self.find_destination(message.data)
        if destination is None:
            self.say("Não encontrei esse destino. Tente novamente.")
            return

        self.current_destination = destination
        self.say(f"Me siga, por favor. Vou até {destination['name']}.")
        self.send_goal(destination, "going_to_destination")

    def on_cancel(self, message: String) -> None:
        if self.phase == "idle":
            return
        if self.active_goal is not None:
            self.active_goal.cancel_goal_async()
        self.active_goal = None
        self.phase = "idle"
        self.current_destination = None
        self.wait_until = 0.0
        self.say("Missão interrompida. O controle manual está ativo.")
        self.get_logger().warning(f"Missao cancelada: {message.data}")

    def send_goal(self, destination: dict, phase: str) -> None:
        if not self.navigator.server_is_ready():
            self.say("A navegação ainda não está disponível.")
            self.phase = "idle"
            self.current_destination = None
            return

        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(destination["x"])
        goal.pose.pose.position.y = float(destination["y"])
        goal.pose.pose.orientation.z, goal.pose.pose.orientation.w = quaternion_from_yaw(
            float(destination.get("yaw", 0.0))
        )

        self.phase = phase
        self.navigator.send_goal_async(goal).add_done_callback(self.goal_accepted)
        self.get_logger().info(f"Enviando destino: {destination['name']}")

    def goal_accepted(self, future) -> None:
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.phase = "idle"
            self.current_destination = None
            self.say("Não consegui iniciar a navegação.")
            return

        self.active_goal = goal_handle
        goal_handle.get_result_async().add_done_callback(self.goal_finished)

    def goal_finished(self, future) -> None:
        result = future.result()
        self.active_goal = None
        if result.status != GoalStatus.STATUS_SUCCEEDED:
            self.phase = "idle"
            self.current_destination = None
            self.say("Não consegui concluir o percurso com segurança.")
            return

        if self.phase == "going_to_destination":
            wait_seconds = float(
                self.current_destination.get(
                    "wait_seconds", self.arrival_wait_seconds
                )
            )
            arrival_message = self.current_destination.get(
                "arrival_message",
                f"{self.current_destination['name']}. Vou aguardar {wait_seconds:.0f} segundos.",
            )
            self.say(arrival_message)
            self.phase = "waiting_at_destination"
            self.wait_until = time.monotonic() + wait_seconds
        elif self.phase == "returning_home":
            self.phase = "idle"
            self.current_destination = None
            self.say("Voltei para a base.")

    def tick(self) -> None:
        if self.phase != "waiting_at_destination" or time.monotonic() < self.wait_until:
            return
        if not self.current_destination.get("return_to_base", True):
            self.say("Vou permanecer neste destino.")
            self.phase = "idle"
            self.current_destination = None
            return
        self.say("Até mais. Vou retornar para a base.")
        self.send_goal(self.destinations[self.home_name], "returning_home")


def main() -> None:
    rclpy.init()
    node = MissionManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

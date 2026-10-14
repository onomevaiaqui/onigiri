#!/usr/bin/env python3
"""Publish recognized Portuguese speech from the webcam microphone to ROS 2."""

import json
import queue
import sys
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


DEFAULT_MODEL_PATH = "/home/onigiri/onigiri/models/vosk-model-small-pt-0.3"


class OnigiriVoiceRecognizer(Node):
    """Recognize final utterances locally and publish them for the mission node."""

    def __init__(self) -> None:
        super().__init__("onigiri_voice_recognizer")
        self.declare_parameter("model_path", DEFAULT_MODEL_PATH)
        self.declare_parameter("audio_device", "")
        self.declare_parameter("sample_rate", 16000)

        self.model_path = Path(self.get_parameter("model_path").value).expanduser()
        self.audio_device = self.get_parameter("audio_device").value
        self.sample_rate = int(self.get_parameter("sample_rate").value)
        self.publisher = self.create_publisher(String, "/onigiri/voice_command", 10)
        self.audio_queue: queue.Queue[bytes] = queue.Queue()

        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model
        except ImportError as error:
            raise RuntimeError(
                "Dependências de voz ausentes. Instale software/raspberry/requirements-voice.txt."
            ) from error

        if not self.model_path.is_dir():
            raise RuntimeError(
                f"Modelo Vosk não encontrado em {self.model_path}. Veja docs/MISSOES_E_DESTINOS.md."
            )

        self.sd = sd
        self.recognizer = KaldiRecognizer(Model(str(self.model_path)), self.sample_rate)
        self.stream = sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=8000,
            device=self.audio_device or None,
            dtype="int16",
            channels=1,
            callback=self.on_audio,
        )
        self.stream.start()
        self.create_timer(0.05, self.process_audio)
        device_label = self.audio_device or "dispositivo de áudio padrão"
        self.get_logger().info(
            f"Reconhecimento de voz pronto: {device_label}; publicando em /onigiri/voice_command."
        )

    def on_audio(self, indata, frames, time_info, status) -> None:
        if status:
            self.get_logger().warning(f"Áudio: {status}")
        self.audio_queue.put(bytes(indata))

    def process_audio(self) -> None:
        while not self.audio_queue.empty():
            data = self.audio_queue.get_nowait()
            if not self.recognizer.AcceptWaveform(data):
                continue
            phrase = json.loads(self.recognizer.Result()).get("text", "").strip()
            if phrase:
                self.publisher.publish(String(data=phrase))
                self.get_logger().info(f"Reconhecido: {phrase}")

    def close(self) -> None:
        self.stream.stop()
        self.stream.close()


def main() -> None:
    rclpy.init()
    node = None
    try:
        node = OnigiriVoiceRecognizer()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except RuntimeError as error:
        print(f"Erro: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    finally:
        if node is not None:
            node.close()
            node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Send Logitech F710 tank commands to the Onigiri over UDP."""

import argparse
import socket
import sys
import time

import pygame


def deadzone(value: float, threshold: float = 0.08) -> float:
    return 0.0 if abs(value) < threshold else value


def send(
    sock: socket.socket,
    destination: tuple[str, int],
    forward: float,
    turn: float,
    lateral_right: float,
) -> None:
    packet = f"{forward:.3f},{turn:.3f},{lateral_right:.3f}".encode("ascii")
    sock.sendto(packet, destination)


def main() -> int:
    parser = argparse.ArgumentParser(description="F710 to Onigiri UDP bridge")
    parser.add_argument("host", help="IPv4 address or Tailscale name of the Raspberry Pi")
    parser.add_argument("--port", type=int, default=5005)
    args = parser.parse_args()

    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("Nenhum joystick detectado. Conecte o receptor USB do Logitech F710.")
        return 1

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"Joystick ativo: {joystick.get_name()}")
    print("Esquerdo: cima/baixo acelera; esquerda/direita gira.")
    print("Direito horizontal: deslocamento lateral. Ctrl+C para parar.")

    destination = (args.host, args.port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        while True:
            pygame.event.pump()

            # F710 em XInput: eixo 0 = horizontal; eixo 1 = vertical (cima é negativo).
            forward = deadzone(-joystick.get_axis(1))
            turn_right = deadzone(joystick.get_axis(0))
            lateral_right = deadzone(joystick.get_axis(2))
            send(sock, destination, forward, turn_right, lateral_right)
            time.sleep(1 / 30)
    except KeyboardInterrupt:
        print("Parando: enviando comando zero.")
    finally:
        for _ in range(3):
            send(sock, destination, 0.0, 0.0, 0.0)
            time.sleep(0.03)
        sock.close()
        pygame.quit()

    return 0


if __name__ == "__main__":
    sys.exit(main())

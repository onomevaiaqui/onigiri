#!/usr/bin/env python3
"""Show Logitech F710 button numbers to choose a safe autonomy toggle."""

import pygame


pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    raise SystemExit("Nenhum joystick detectado.")

joystick = pygame.joystick.Joystick(0)
joystick.init()
print(f"Joystick ativo: {joystick.get_name()}")
print("Pressione o botao que deseja usar para alternar a autonomia. Ctrl+C para encerrar.")

try:
    while True:
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                print(f"Botao pressionado: {event.button}")
            elif event.type == pygame.JOYBUTTONUP:
                print(f"Botao solto: {event.button}")
except KeyboardInterrupt:
    pass
finally:
    pygame.quit()


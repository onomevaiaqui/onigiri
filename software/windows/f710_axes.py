#!/usr/bin/env python3
"""Show F710 axis changes for control mapping."""

import pygame


pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    raise SystemExit("Nenhum joystick detectado.")

joystick = pygame.joystick.Joystick(0)
joystick.init()
print(f"Joystick ativo: {joystick.get_name()}")
print("Mova somente o analógico direito. Ctrl+C para encerrar.")

try:
    while True:
        for event in pygame.event.get():
            if event.type == pygame.JOYAXISMOTION:
                print(f"axis {event.axis}: {event.value:+.3f}")
except KeyboardInterrupt:
    pass
finally:
    pygame.quit()

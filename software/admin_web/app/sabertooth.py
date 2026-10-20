"""Sabertooth legacy Packetized Serial codec. Pure functions: never opens ports."""
import math

def motor_packet(address, motor, power):
    if not isinstance(address, int) or not 128 <= address <= 135:
        raise ValueError("Endereço deve estar entre 128 e 135")
    if motor not in (1, 2):
        raise ValueError("Motor deve ser 1 ou 2")
    if not math.isfinite(power) or not -1 <= power <= 1:
        raise ValueError("Potência normalizada deve estar entre -1 e 1")
    command = (0 if motor == 1 else 4) + (1 if power < 0 else 0)
    value = round(abs(power)*127)
    return bytes((address, command, value, (address+command+value)&127))

def tank_preview(forward, turn, address=128, invert_left=False, invert_right=False):
    """Normalized input, positive turn is ROS counterclockwise. No speed feedback."""
    if not all(math.isfinite(x) and -1 <= x <= 1 for x in (forward,turn)):
        raise ValueError("Entradas devem estar entre -1 e 1")
    left, right = forward-turn, forward+turn
    scale = max(1,abs(left),abs(right))
    left, right = left/scale, right/scale
    if invert_left: left = -left
    if invert_right: right = -right
    return {"left":left,"right":right,
            "packets_hex":[motor_packet(address,1,left).hex(' '),motor_packet(address,2,right).hex(' ')],
            "transmitted":False}

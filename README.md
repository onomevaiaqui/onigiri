# Onigiri

Base de software e manual de construção do robô móvel **Onigiri**.

O estado atual é um robô omnidirecional de três motores, comandado pelo Logitech F710 a partir de um PC Windows e protegido por uma parada frontal baseada no RPLIDAR A1. O Raspberry Pi executa Ubuntu 24.04 e ROS 2 Jazzy.

## Estado validado

- [x] Três motores JGY370 12 V / 40 RPM acionados pelo Stepper Motor HAT v0.2.
- [x] Locomoção: frente/ré, giro e deslocamento lateral.
- [x] Controle remoto por Logitech F710 no Windows, via Tailscale/UDP.
- [x] RPLIDAR A1 publicando `/scan` no ROS 2.
- [x] Proteção frontal: avanço bloqueado a menos de 0,35 m; ré, giro e lateral continuam disponíveis.
- [x] Controlador de motores e LiDAR inicializados automaticamente no Raspberry.
- [x] Modo autônomo experimental: avanço lento e desvio pelo lado mais livre.
- [x] Autonomia inicia desativada e exige ativação explícita.
- [ ] Desvio autônomo de obstáculos e navegação.

## Estrutura

- `onigiri_udp_tank.py` — controlador executado no Raspberry: motores, UDP, `/cmd_vel` e proteção LiDAR.
- `f710_bridge.py` — ponte executada no Windows: Logitech F710 para UDP.
- `onigiri_autonomous_basic.py` — comportamento autônomo inicial, desabilitado no boot até validação.
- `systemd/` — serviços para iniciar o controlador e o LiDAR no boot.
- `docs/MANUAL_DE_CONSTRUCAO.md` — montagem, alimentação, rede e operação.

## Segurança

Os motores e o Raspberry usam alimentações separadas com terra comum: a LiPo 3S alimenta o HAT/motores e o conversor Tobsun EA75-5V alimenta o Raspberry via USB-C. Não conecte um segundo carregador/fonte USB-C ao Raspberry enquanto o Tobsun estiver alimentando-o.

Antes de qualquer teste, mantenha as rodas suspensas ou deixe área livre ao redor do robô. A proteção por LiDAR é uma camada adicional e não substitui supervisão humana ou um desligamento físico da alimentação.

Para o procedimento completo, consulte o [manual de construção](docs/MANUAL_DE_CONSTRUCAO.md).

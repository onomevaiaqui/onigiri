# Onigiri

Base de software, operação e construção do robô móvel **Onigiri**.

O Onigiri usa um Raspberry Pi 4 com Ubuntu 24.04 e ROS 2 Jazzy, três motores JGY370 de 12 V, um Stepper Motor HAT v0.2 e um RPLIDAR A1M8. O Logitech F710, conectado a um PC Windows, controla o robô pela rede Tailscale.

## O que já funciona

- Três motores: frente/ré, giro e deslocamento lateral.
- RPLIDAR A1 publicando `/scan`.
- Parada frontal rígida a 35 cm.
- Desvio autônomo experimental: compara os lados livres e começa a desviar a 80 cm.
- Prioridade manual: movimentar um analógico do F710 assume imediatamente o controle.
- Botão 7 do F710 ativa/desativa a autonomia.
- Inicialização automática no Raspberry: base, LiDAR e autonomia armada.
- Autonomia segura no boot: o processo inicia, mas o robô fica parado até receber ativação explícita.

> A autonomia atual é reativa, não é navegação por mapa. Ela não possui encoders, odometria, SLAM ou planejamento de rota.

## Comece aqui

O guia completo de montagem, instalação, operação, atualização e diagnóstico está em [docs/MANUAL_DE_CONSTRUCAO.md](docs/MANUAL_DE_CONSTRUCAO.md).

## Estrutura

| Caminho | Uso |
|---|---|
| `onigiri_udp_tank.py` | Raspberry: motores, LiDAR, UDP e `/cmd_vel`. |
| `onigiri_autonomous_basic.py` | Raspberry: autonomia reativa, inicialmente desativada. |
| `f710_bridge.py` | Windows: ponte Logitech F710 → UDP. |
| `f710_axes.py` | Windows: identifica eixos do controle. |
| `f710_buttons.py` | Windows: identifica botões do controle. |
| `systemd/` | Serviços automáticos do Raspberry. |
| `docs/` | Manual e procedimentos operacionais. |

## Segurança essencial

- A LiPo 3S alimenta o HAT e os motores; o Tobsun EA75-5V alimenta o Raspberry pelo USB-C.
- Não conecte outra fonte/carregador USB-C ao Raspberry enquanto o Tobsun estiver alimentando-o.
- Mantenha pessoas, cabos e objetos fora da área de movimento antes de ativar a autonomia.
- O LiDAR e o software são camadas de proteção, não substituem supervisão nem uma forma física de cortar a alimentação.

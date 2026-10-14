# Arquitetura da plataforma

## Visão geral

O Onigiri integra um computador embarcado, motores, sensores e um computador de controle. O Raspberry Pi executa o ROS 2 e toma decisões locais de movimento. O PC Windows fornece o controle manual por rede.

```text
Logitech F710 + PC Windows
          |
          | UDP pela rede Tailscale
          v
Raspberry Pi 4 + ROS 2 Jazzy
   |              |             |
   |              |             +--> RPLIDAR A1M8 --> /scan
   |              |
   |              +--> autonomia reativa
   |
   +--> Stepper Motor HAT v0.2 --> M1, M2 e M3
```

## Software

| Local | Arquivo | Responsabilidade |
|---|---|---|
| Raspberry Pi | `software/raspberry/onigiri_udp_tank.py` | Recebe comandos UDP, controla motores, aplica parada frontal e publica integração ROS 2. |
| Raspberry Pi | `software/raspberry/onigiri_autonomous_basic.py` | Executa a autonomia reativa quando habilitada. |
| Windows | `software/windows/f710_bridge.py` | Lê o Logitech F710 e envia comandos UDP ao Raspberry. |
| Windows | `software/windows/f710_axes.py` | Ajuda a identificar os eixos de um controle. |
| Windows | `software/windows/f710_buttons.py` | Ajuda a identificar os botões de um controle. |

## Implantação no Raspberry Pi

Os serviços em `deploy/systemd/` foram preparados para a instalação atual, na qual os scripts são copiados para `/home/onigiri/`.

Para atualizar o Raspberry a partir deste repositório, copie os arquivos de `software/raspberry/` para `/home/onigiri/` e os arquivos de `deploy/systemd/` para `/etc/systemd/system/`, conforme o manual.

## Limites atuais

- Sem encoders e odometria física.
- Sem localização persistente em mapa.
- A proteção automática cobre apenas o avanço frontal.
- Voz, câmera e navegação até destinos são recursos planejados.

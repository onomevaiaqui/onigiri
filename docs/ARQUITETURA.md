# Arquitetura da plataforma

## Visão geral

O Onigiri integra um computador embarcado, motores, sensores e um computador de controle. O Raspberry Pi executa o ROS 2 e toma decisões locais de movimento. O computador do operador fornece o controle manual por rede e pode usar Windows, macOS ou Linux.

```text
Logitech F710 + computador do operador
          |
          | UDP pela rede Tailscale
          v
Raspberry Pi 4 + ROS 2 Jazzy
   |              |             |              |
   |              |             +--> RPLIDAR A1M8 --> /scan
   |              |
   |              +--> autonomia reativa
   |
   +--> Stepper Motor HAT v0.2 --> M1, M2 e M3
   |
   +--> Webcam UVC + microfone --> Vosk --> /onigiri/voice_command
   |
   +--> Alto-falante/amplificador <-- espeak-ng <-- /onigiri/speech
```

## Software

| Local | Arquivo | Responsabilidade |
|---|---|---|
| Raspberry Pi | `software/raspberry/onigiri_motor_controller.py` | Recebe comandos UDP, controla motores, aplica parada frontal e publica integração ROS 2. |
| Raspberry Pi | `software/raspberry/onigiri_autonomous_basic.py` | Executa a autonomia reativa quando habilitada. |
| Raspberry Pi | `software/raspberry/onigiri_voice_recognizer.py` | Transcreve localmente o microfone da webcam e publica frases reconhecidas. |
| Raspberry Pi | `software/raspberry/onigiri_mission_manager.py` | Conecta pedidos de destino ao Nav2, espera e retorno à base. |
| Raspberry Pi | `software/raspberry/onigiri_speech.py` | Converte mensagens ROS em fala local. |
| Computador do operador | `software/operator_client/f710_bridge.py` | Lê o Logitech F710 e envia comandos UDP ao Raspberry. |
| Computador do operador | `software/operator_client/f710_axes.py` | Ajuda a identificar os eixos de um controle. |
| Computador do operador | `software/operator_client/f710_buttons.py` | Ajuda a identificar os botões de um controle. |

## Implantação no Raspberry Pi

Os serviços em `deploy/systemd/` foram preparados para um clone em
`/home/onigiri/onigiri`.

Para atualizar o Raspberry, execute `git pull` no clone e reinstale os serviços,
conforme o [guia de construção do zero](GUIA_DE_CONSTRUCAO_DO_ZERO.md).

## Limites atuais

- Sem encoders e odometria física.
- Sem localização persistente em mapa.
- A proteção automática por LiDAR foi implementada para frente, ré e laterais,
  mas precisa de validação física completa.
- Voz e missão dependem de webcam/microfone, modelo Vosk, mapa, localização e
  Nav2 instalados e configurados.

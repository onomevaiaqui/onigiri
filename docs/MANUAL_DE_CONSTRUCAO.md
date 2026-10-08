# Manual de construção — Onigiri

Este documento registra apenas a configuração que foi montada e testada.

## 1. Componentes

| Item | Função |
|---|---|
| Raspberry Pi 4 | Computador principal, Ubuntu 24.04 e ROS 2 Jazzy |
| Stepper Motor HAT v0.2 (UGEek/Geekworm compatível) | Driver dos três motores DC via I2C |
| 3 × JGY370 12 V, 40 RPM | M1 dianteiro esquerdo, M2 dianteiro direito, M3 traseiro |
| LiPo 3S, 11,1 V, 1150 mAh | Alimentação dos motores/HAT |
| Tobsun EA75-5V | Conversor 12/24 V para 5 V; alimenta o Raspberry por USB-C |
| RPLIDAR A1M8 | Detecção frontal de obstáculos |
| Logitech F710 + PC Windows | Controle remoto no estado atual |

## 2. Arquitetura de alimentação

```text
LiPo 3S (11,1 V)
 ├── Stepper Motor HAT → M1, M2, M3
 └── Tobsun EA75-5V → USB-C → Raspberry Pi 4
                                  └── USB → RPLIDAR A1
```

- A tensão medida na saída do Tobsun foi **5,07 V**.
- O HAT não é a fonte de 5 V do Raspberry nesta montagem.
- Não alimente simultaneamente o Raspberry pelo Tobsun e por outro carregador/fonte USB-C.
- Verifique a polaridade da bateria antes de ligar o HAT.

## 3. Mecânica e motores

O chassi usa três módulos de tração dispostos para locomoção omnidirecional, inspirada no conceito de rodas esféricas. A identificação validada é:

| Canal HAT | Motor | Posição | Movimento positivo validado |
|---|---|---|---|
| M1 | JGY370 | Dianteiro esquerdo | Frente |
| M2 | JGY370 | Dianteiro direito | Frente |
| M3 | JGY370 | Traseiro | Direita |

Comandos combinados validados:

- M1 e M2 positivos: frente.
- M1 positivo e M2 negativo: giro para a direita.
- M3 positivo: deslocamento lateral para a direita.

## 4. I2C e HAT

O HAT foi detectado em `0x6f`; `0x70` é o endereço de all-call do PCA9685.

Mapeamento utilizado pelo controlador:

| Motor | PWM | IN1 | IN2 |
|---|---:|---:|---:|
| M1 | 8 | 10 | 9 |
| M2 | 13 | 11 | 12 |
| M3 | 2 | 4 | 3 |

O script usa frenagem elétrica curta ao soltar o comando, para reduzir a inércia.

## 5. Raspberry e ROS 2

Sistema operacional: Ubuntu 24.04 no Raspberry Pi 4. Middleware: ROS 2 Jazzy.

Pacotes utilizados:

```bash
sudo apt install i2c-tools python3-smbus joystick evtest
sudo apt install ros-jazzy-joy-linux
```

O LiDAR é exposto de forma estável em:

```text
/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0
```

O tópico ROS do LiDAR é `/scan`; o eixo zero está fisicamente alinhado com a frente do robô.

## 6. Serviços de inicialização

Os dois serviços devem ficar habilitados:

```bash
sudo systemctl enable onigiri-udp.service
sudo systemctl enable onigiri-lidar.service
```

Após ligar o robô, confira:

```bash
ros2 node list
```

Resultado esperado:

```text
/onigiri_base
/rplidar_composition
```

## 7. Controle pelo F710

No Windows, conecte o receptor USB do F710 e execute no Git Bash:

```bash
python "/c/caminho/para/f710_bridge.py" 100.95.225.112
```

Mapeamento atual:

| Controle | Ação |
|---|---|
| Analógico esquerdo vertical | Frente/ré |
| Analógico esquerdo horizontal | Giro |
| Analógico direito horizontal | Deslocamento lateral |

O Raspberry recebe os comandos por UDP na porta `5005`. O watchdog para os motores se os pacotes pararem por mais de 0,30 s.

## 8. Proteção frontal por LiDAR

O controlador monitora os pontos do LiDAR em ±12° na frente. Quando há obstáculo a menos de **0,35 m**, ele bloqueia somente o comando para frente. Ré, giro e deslocamento lateral permanecem possíveis para que o operador se afaste.

Teste:

1. Posicione um objeto plano a aproximadamente 25 cm em frente ao LiDAR.
2. Tente avançar: o robô deve ficar parado.
3. Afaste o objeto para aproximadamente 60 cm: o avanço deve voltar a funcionar.

## 9. Redes

Há dois perfis Wi-Fi configurados com reconexão automática: `Itaipu_Parquetec` e `Metto`. O acesso remoto ocorre pela rede Tailscale; o endereço do Raspberry usado no desenvolvimento é `100.95.225.112`.

## 10. Próximas etapas

### 10.1 Modo autônomo básico

O arquivo `onigiri_autonomous_basic.py` publica um comando lento de avanço (`0,20`) no tópico `/cmd_vel`. Ao encontrar obstáculo a menos de **0,50 m**, ele compara os setores diagonais esquerdo e direito do LiDAR e faz um giro curto para o lado com mais espaço livre antes de voltar a avançar. O controlador principal mantém a responsabilidade pela segurança: se o LiDAR enxergar algo a menos de 0,35 m, o avanço é bloqueado.

Em 8 de outubro de 2026, o modo autônomo básico foi validado após reinicialização por troca de bateria. Os três motores também foram confirmados por comandos ROS: M1/M2 no avanço e M3 no movimento lateral.

Na mesma validação, o comportamento de desvio experimental foi confirmado: com um objeto a aproximadamente 40 cm à frente, o Onigiri interrompeu o avanço, girou para a esquerda e retomou o deslocamento sem atingir o limite de segurança de 35 cm.

Também foi validada a escolha dinâmica do lado: com espaço livre à esquerda, o robô escolheu a esquerda; bloqueando o setor diagonal esquerdo e mantendo a direita livre, escolheu corretamente a direita.

O controle manual do F710 tem prioridade enquanto estiver enviando dados. O serviço autônomo inicia **desativado**, portanto não move o robô ao ligar a bateria. Para ativá-lo intencionalmente no Raspberry, pare a ponte do F710 com `Ctrl+C` e execute:

```bash
source /opt/ros/jazzy/setup.bash
ros2 service call /onigiri_autonomous/set_enabled std_srvs/srv/SetBool "{data: true}"
```

Para parar a autonomia explicitamente:

```bash
source /opt/ros/jazzy/setup.bash
ros2 service call /onigiri_autonomous/set_enabled std_srvs/srv/SetBool "{data: false}"
```

O serviço `onigiri-autonomous.service` pode ser habilitado no boot porque permanece parado até a ativação explícita. Este é um comportamento experimental: sempre realize o teste em área livre e supervisionada.

### 10.2 Evolução planejada

1. Validar o modo autônomo básico em área livre.
2. Definir forma segura de alternar entre controle manual e autonomia.
3. Implementar desvio de obstáculos usando o LiDAR.
4. Acrescentar câmera, áudio e demais periféricos.
5. Documentar cada mudança neste manual.

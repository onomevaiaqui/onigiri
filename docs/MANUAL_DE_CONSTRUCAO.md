# Manual de construção e operação — Onigiri

Este manual descreve a configuração montada e validada até 8 de outubro de 2026. Atualize-o junto de qualquer alteração elétrica, mecânica ou de software.

## 1. Segurança

1. Desligue a LiPo antes de mexer em cabos, HAT ou motores.
2. Antes de testar, suspenda as rodas ou deixe uma área livre ao redor do robô.
3. A autonomia atual é experimental e reativa; supervisione o robô o tempo todo.
4. O LiDAR só protege o setor frontal configurado. Ré e deslocamento lateral não possuem, por enquanto, barreira equivalente.
5. Não conecte simultaneamente o Tobsun e outra fonte/carregador USB-C ao Raspberry.

## 2. Componentes validados

| Item | Função |
|---|---|
| Raspberry Pi 4 | Computador principal: Ubuntu 24.04 + ROS 2 Jazzy |
| Stepper Motor HAT v0.2, compatível UGEek/Geekworm | Driver I2C dos motores DC |
| 3 × JGY370, 12 V, 40 RPM | Tração: M1 dianteiro esquerdo, M2 dianteiro direito, M3 traseiro |
| LiPo 3S, 11,1 V, 1150 mAh | Alimentação dos motores/HAT |
| Tobsun EA75-5V | Conversão para 5 V; alimenta o Raspberry por USB-C |
| RPLIDAR A1M8 | Percepção de obstáculos |
| Logitech F710 + PC Windows | Controle manual e seleção da autonomia |

## 3. Alimentação

```text
LiPo 3S (11,1 V)
 ├── Stepper Motor HAT ──> M1, M2, M3
 └── Tobsun EA75-5V ────> USB-C ──> Raspberry Pi 4
                                           └── USB ──> RPLIDAR A1
```

- Saída Tobsun validada: **5,07 V**.
- O HAT não alimenta o Raspberry nesta montagem.
- Confira a polaridade antes de ligar a bateria.
- A tensão e a corrente de pico dos motores devem permanecer dentro da capacidade do HAT.

## 4. Mecânica, motores e HAT

O chassi usa três módulos de tração para movimento omnidirecional.

| Canal | Posição | Movimento positivo validado |
|---|---|---|
| M1 | Dianteiro esquerdo | Frente |
| M2 | Dianteiro direito | Frente |
| M3 | Traseiro | Direita/lateral |

Comandos combinados validados:

- M1 + M2 positivos: frente.
- M1 positivo + M2 negativo: giro à direita.
- M3 positivo: lateral à direita.

O HAT PCA9685 foi detectado em `0x6f`; `0x70` é o endereço all-call. O controlador usa este mapeamento:

| Motor | PWM | IN1 | IN2 |
|---|---:|---:|---:|
| M1 | 8 | 10 | 9 |
| M2 | 13 | 11 | 12 |
| M3 | 2 | 4 | 3 |

## 5. Software necessário

### Raspberry Pi

O Raspberry executa Ubuntu 24.04 e ROS 2 Jazzy. Instale os utilitários usados pelo projeto:

```bash
sudo apt update
sudo apt install i2c-tools python3-smbus joystick evtest ros-jazzy-rplidar-ros
```

Confirme o HAT e o LiDAR:

```bash
sudo i2cdetect -y 1
ls -l /dev/serial/by-id/
```

O HAT deve aparecer em `6f`. O LiDAR validado usa o link estável:

```text
/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0
```

O usuário `onigiri` precisa acessar I2C e serial:

```bash
sudo usermod -aG i2c,dialout onigiri
```

Saia e entre novamente na sessão SSH após esse comando.

### PC Windows

Instale Python e `pygame-ce`:

```bash
python -m pip install pygame-ce
```

O desenvolvimento atual usa `C:\Python314\python.exe`. Ajuste os comandos se o Python estiver em outro local.

## 6. Implantação no Raspberry

Os scripts devem ficar em `/home/onigiri`. A partir do Windows, com Git Bash:

```bash
scp onigiri_udp_tank.py onigiri_autonomous_basic.py onigiri@<IP_TAILSCALE_DO_RASPBERRY>:~/
scp systemd/onigiri-udp.service systemd/onigiri-lidar.service systemd/onigiri-autonomous.service onigiri@<IP_TAILSCALE_DO_RASPBERRY>:~/
```

No Raspberry, instale os serviços:

```bash
sudo install -m 644 ~/onigiri-udp.service /etc/systemd/system/onigiri-udp.service
sudo install -m 644 ~/onigiri-lidar.service /etc/systemd/system/onigiri-lidar.service
sudo install -m 644 ~/onigiri-autonomous.service /etc/systemd/system/onigiri-autonomous.service
sudo systemctl daemon-reload
sudo systemctl enable --now onigiri-udp.service onigiri-lidar.service onigiri-autonomous.service
```

Todos os três serviços iniciam no boot. A autonomia inicia armada, mas **desativada**, portanto não deve mover o robô sozinha.

Verificação:

```bash
systemctl is-active onigiri-udp.service onigiri-lidar.service onigiri-autonomous.service
source /opt/ros/jazzy/setup.bash
ros2 node list
```

Resultado esperado: três linhas `active`, além de nós como `/onigiri_base`, `/rplidar_composition` e `/onigiri_autonomous_basic`.

## 7. Controle Logitech F710

Execute a ponte no Windows/Git Bash:

```bash
python "/c/caminho/para/onigiri/f710_bridge.py" <IP_TAILSCALE_DO_RASPBERRY>
```

| Controle | Ação |
|---|---|
| Analógico esquerdo vertical | Frente/ré |
| Analógico esquerdo horizontal | Giro |
| Analógico direito horizontal | Deslocamento lateral |
| Botão 7 | Ativa/desativa a autonomia |
| `Ctrl+C` na ponte | Envia parada e desativa a autonomia |

O F710 envia UDP para a porta `5005`. Movimentar um analógico tem prioridade sobre a autonomia. Quando os analógicos retornam ao centro, a autonomia pode retomar se o botão 7 permanecer ligado.

Para descobrir um eixo ou botão em outro controle, execute `f710_axes.py` ou `f710_buttons.py` no Windows.

### Inicialização automática no Windows

Crie um arquivo `Onigiri F710 Bridge.cmd` na pasta de inicialização do usuário:

```text
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
```

Conteúdo, ajustando os caminhos quando necessário:

```bat
@echo off
start "Onigiri F710 Bridge" /min "C:\Python314\python.exe" "C:\caminho\para\onigiri\f710_bridge.py" <IP_TAILSCALE_DO_RASPBERRY>
```

A ponte aguarda o receptor USB se ele não estiver conectado e desativa a autonomia se o controle desconectar.

## 8. LiDAR e proteções

O LiDAR publica `/scan`; seu eixo zero está alinhado com a frente do robô.

### Barreira de emergência

O controlador principal mede o setor de ±12° à frente. Abaixo de **0,35 m**, bloqueia apenas o avanço. Ré, giro e lateral continuam disponíveis para liberar o robô.

Teste:

1. Coloque um objeto plano a 25 cm, na altura do LiDAR.
2. Tente avançar: o robô deve ficar parado.
3. Afaste o objeto para 60 cm: o avanço deve voltar a funcionar.

### Autonomia reativa

Com autonomia ligada, o robô avança em potência máxima, adequada aos JGY370 de 40 RPM. Ao identificar obstáculo a menos de **0,80 m**, compara setores diagonais de 30° a 75° à esquerda/direita, gira por aproximadamente 0,9 s para o lado com maior distância livre e retoma o avanço. Em caso de empate, prefere a esquerda.

Para ativar/desativar sem o F710:

```bash
source /opt/ros/jazzy/setup.bash
ros2 service call /onigiri_autonomous/set_enabled std_srvs/srv/SetBool "{data: true}"
ros2 service call /onigiri_autonomous/set_enabled std_srvs/srv/SetBool "{data: false}"
```

Se `/scan` ficar sem atualização por mais de 0,5 s, a autonomia não envia movimento.

## 9. Sequência de operação

1. Verifique fiação, bateria, área livre e posição frontal do LiDAR.
2. Ligue a alimentação do robô e aguarde os três serviços ficarem ativos.
3. Faça login no Windows; a ponte do F710 inicia automaticamente se a configuração de inicialização estiver criada.
4. Controle manualmente pelos analógicos ou pressione o botão 7 para ativar a autonomia.
5. Para interromper a autonomia, pressione novamente o botão 7, mova os analógicos ou desligue a ponte com `Ctrl+C`.
6. Desligue a LiPo antes de transportar, alterar a montagem ou trocar cabos.

## 10. Diagnóstico e recuperação

### Serviços

```bash
sudo systemctl status onigiri-udp.service --no-pager
sudo systemctl status onigiri-lidar.service --no-pager
sudo systemctl status onigiri-autonomous.service --no-pager
```

Reinicie somente o componente necessário:

```bash
sudo systemctl restart onigiri-udp.service
sudo systemctl restart onigiri-lidar.service
sudo systemctl restart onigiri-autonomous.service
```

Veja erros recentes:

```bash
sudo journalctl -u onigiri-udp.service -n 50 --no-pager
sudo journalctl -u onigiri-lidar.service -n 50 --no-pager
sudo journalctl -u onigiri-autonomous.service -n 50 --no-pager
```

### LiDAR

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic echo /scan --once
```

### F710

1. Confirme o receptor USB e o modo do controle.
2. Execute `f710_bridge.py` no Git Bash e verifique a mensagem `Joystick ativo`.
3. Se não houver controle manual, confirme se o PC alcança o IP Tailscale do Raspberry.
4. Se o robô estiver parado com autonomia ligada, confirme `/scan` e os três serviços.

## 11. Atualização de código

1. Faça alterações no repositório e publique no GitHub.
2. Copie ao Raspberry somente os arquivos modificados com `scp`.
3. Para alterações em `onigiri_udp_tank.py`, reinicie `onigiri-udp.service`.
4. Para alterações em `onigiri_autonomous_basic.py`, reinicie `onigiri-autonomous.service`.
5. Para alterações em um arquivo de `systemd/`, execute `sudo install`, `sudo systemctl daemon-reload` e reinicie/habilite o serviço afetado.
6. Documente e valide a mudança antes de considerar a etapa concluída.

## 12. Itens validados e evolução

Validações concluídas:

- M1, M2 e M3 respondem corretamente.
- LiDAR, barreira frontal, desvio à esquerda e desvio à direita foram testados.
- Autonomia pode ser ativada/desativada por serviço ROS e pelo botão 7.
- Serviços sobem após reboot sem movimentar o robô.

Próximas evoluções:

1. Curso com múltiplos obstáculos.
2. Proteções equivalentes para ré e deslocamento lateral.
3. Câmera, áudio e interface de operação.
4. Odometria/SLAM/navegação por mapa, se sensores adicionais forem incorporados.

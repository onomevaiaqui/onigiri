# Guia de construção do zero — Onigiri

> **Estado do guia:** a instalação e o software estão documentados para
> reprodução. O projeto segue em desenvolvimento; testes físicos, ajustes de
> segurança e correção de bugs continuam obrigatórios antes de uso real.

Este é o caminho de referência para montar uma nova unidade do Onigiri. Faça as
etapas na ordem indicada e não habilite autonomia, missões ou voz antes de
concluir as verificações da seção final.

## 1. Materiais

| Quantidade | Item | Observação |
|---:|---|---|
| 1 | Raspberry Pi 4 | Com fonte de armazenamento e Ubuntu 24.04 ARM64 |
| 1 | Stepper Motor HAT v0.2 | Controlador I2C compatível com PCA9685 |
| 3 | Motor DC JGY370, 12 V, 40 RPM | M1 dianteiro esquerdo, M2 dianteiro direito, M3 traseiro |
| 1 | LiPo 3S, 11,1 V | Alimentação de tração; use carregador apropriado |
| 1 | Tobsun EA75-5V | Entrada 12 V, saída 5 V para o Raspberry por USB-C |
| 1 | RPLIDAR A1M8 | Sensor de obstáculos e mapeamento |
| 1 | Webcam UVC **com microfone integrado** | Vídeo e entrada de voz via USB |
| 1 | Alto-falante + amplificador | Saída de fala do robô |
| 1 | Botão de emergência com contato NC | Deve cortar fisicamente apenas a tração |
| 1 | Logitech F710 + PC Windows | Controle manual pela rede Tailscale |

## 2. Segurança elétrica e montagem

1. Com a LiPo desconectada, encaixe o HAT sobre o GPIO do Raspberry.
2. Ligue M1, M2 e M3 nos bornes correspondentes do HAT.
3. Ligue a LiPo ao HAT, respeitando a polaridade e a faixa de tensão impressa
   na placa.
4. Ligue a mesma LiPo à entrada do Tobsun; a saída de 5 V do Tobsun alimenta o
   Raspberry **somente** pelo USB-C.
5. Não alimente o Raspberry simultaneamente pelo Tobsun e por outro carregador
   ou fonte USB-C.
6. Instale o botão de emergência com contato normalmente fechado (NC) em série
   no positivo da LiPo que segue para o HAT. O Raspberry continua ligado pelo
   Tobsun; ao pressionar o botão, a tração perde energia. Consulte
   [o documento dedicado](BOTAO_DE_EMERGENCIA.md).
7. Conecte o RPLIDAR e a webcam diretamente a portas USB do Raspberry; conecte
   o amplificador ao áudio escolhido para a unidade.

Antes de colocar o robô no chão, meça a saída do Tobsun: ela deve estar próxima
de 5 V e dentro do permitido pelo Raspberry. Faça a primeira energização com as
rodas suspensas.

## 3. Instalar o sistema operacional e ROS 2

1. Grave Ubuntu Server 24.04 ARM64 no cartão/SSD e habilite SSH.
2. Atualize o sistema e instale ROS 2 Jazzy segundo a documentação oficial do
   ROS para Ubuntu 24.04.
3. Crie o usuário operacional `onigiri` e conceda acesso ao I2C e às portas
   seriais:

```bash
sudo usermod -aG i2c,dialout onigiri
```

4. Saia da sessão SSH e entre novamente para aplicar os grupos.
5. Instale os pacotes do projeto:

```bash
sudo apt update
sudo apt install -y git wget unzip v4l-utils i2c-tools python3-smbus python3-pip portaudio19-dev \
  joystick evtest espeak-ng ros-jazzy-rplidar-ros ros-jazzy-nav2-bringup \
  ros-jazzy-slam-toolbox
```

## 4. Baixar o projeto no Raspberry

```bash
git clone https://github.com/onomevaiaqui/onigiri.git /home/onigiri/onigiri
cd /home/onigiri/onigiri
python3 -m pip install --user -r software/raspberry/requirements-voice.txt
```

O diretório `/home/onigiri/onigiri` é o caminho padrão usado pelos serviços.
Não mova os arquivos sem também ajustar os arquivos em `deploy/systemd/`.

## 5. Confirmar HAT, LiDAR, webcam e áudio

### HAT e motores

```bash
sudo i2cdetect -y 1
```

O PCA9685 do HAT deve aparecer em `6f`; `70` pode aparecer como endereço
all-call. A identificação não confirma que os motores estão seguros para rodar:
isso é validado na seção final.

### LiDAR

```bash
ls -l /dev/serial/by-id/
```

O RPLIDAR A1M8 usado no projeto aparece como adaptador CP2102. Se o nome do
link for diferente, ajuste `serial_port` em
`deploy/systemd/onigiri-lidar.service` **antes** de instalar o serviço.

### Webcam e microfone

```bash
v4l2-ctl --list-devices
arecord -l
python3 -c "import sounddevice as sd; print(sd.query_devices())"
```

Se `v4l2-ctl` não existir, instale `v4l-utils`. A webcam precisa aparecer como
vídeo UVC e também como dispositivo de captura de áudio. Anote o nome ou índice
do microfone para configurar `audio_device` no serviço de voz quando necessário.

## 6. Instalar serviços do Raspberry

Copie os serviços do repositório para o `systemd`:

```bash
sudo install -m 644 deploy/systemd/onigiri-udp.service /etc/systemd/system/
sudo install -m 644 deploy/systemd/onigiri-lidar.service /etc/systemd/system/
sudo install -m 644 deploy/systemd/onigiri-autonomous.service /etc/systemd/system/
sudo install -m 644 deploy/systemd/onigiri-speech.service /etc/systemd/system/
sudo install -m 644 deploy/systemd/onigiri-voice.service /etc/systemd/system/
sudo install -m 644 deploy/systemd/onigiri-mission.service /etc/systemd/system/
sudo systemctl daemon-reload
```

Ative inicialmente apenas a base de segurança e percepção:

```bash
sudo systemctl enable --now onigiri-udp.service onigiri-lidar.service onigiri-autonomous.service
```

O serviço autônomo sobe desativado e não deve mover o robô até receber sua
habilitação explícita. Só habilite `onigiri-speech`, `onigiri-voice` e
`onigiri-mission` após concluir as configurações de áudio, modelo Vosk, mapa,
localização e Nav2.

## 7. Configurar voz e áudio

1. Baixe o modelo Vosk pequeno em português e extraia-o em:

```bash
cd /home/onigiri/onigiri
mkdir -p models
wget https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip -O /tmp/onigiri-vosk-pt.zip
unzip /tmp/onigiri-vosk-pt.zip -d models
```

O caminho final precisa ser
`/home/onigiri/onigiri/models/vosk-model-small-pt-0.3/`. O modelo pequeno em
português é listado pelo próprio Vosk como apropriado para Raspberry Pi.

2. Se necessário, informe a webcam como dispositivo de áudio no serviço de voz:

```ini
ExecStart=/bin/bash -lc 'source /opt/ros/jazzy/setup.bash && exec python3 software/raspberry/onigiri_voice_recognizer.py --ros-args -p audio_device:="USB Camera"'
```

3. Execute `sudo systemctl daemon-reload` e, somente quando o microfone for
   reconhecido, habilite os serviços de fala e voz:

```bash
sudo systemctl enable --now onigiri-speech.service onigiri-voice.service
```

O reconhecimento é local, mas ainda deve ser testado quanto a ruído, eco do
alto-falante e sotaques antes de ser usado em uma missão real.

## 8. Mapa, localização e destinos

1. Monte o mapa com `slam_toolbox` e salve-o.
2. Configure uma estratégia de localização adequada ao hardware e ao ambiente.
   O protótipo não possui encoders; portanto, não considere a localização pronta
   antes de demonstrar repetibilidade em testes físicos.
3. Suba o Nav2 com o mapa e a localização já configurados.
4. Para o fluxo recomendado, cadastre destinos pelo painel local. Ele gerará
   `config/destinations.runtime.json`, que não é enviado ao Git. Sem usar o
   painel, a alternativa manual de desenvolvimento é:

```bash
cp config/destinations.example.json config/destinations.json
```

5. Preencha coordenadas reais de `base` e dos ambientes cadastrados no painel
   ou, no fluxo manual, no arquivo JSON.
6. Habilite o gerenciador de missão:

```bash
sudo systemctl enable --now onigiri-mission.service
```

Veja detalhes de frases, destinos e fluxo em
[Missões, destinos e interação por voz](MISSOES_E_DESTINOS.md).

## 9. Controle manual pelo Windows

1. Instale Python 3 e conecte o receptor USB do Logitech F710.
2. Instale a dependência:

```powershell
py -m pip install pygame-ce
```

3. Clone o repositório no PC e inicie a ponte, substituindo o IP Tailscale:

```powershell
py .\software\windows\f710_bridge.py <IP_TAILSCALE_DO_RASPBERRY>
```

O analógico esquerdo controla frente/ré e giro; o direito controla a lateral.
Movimento manual cancela uma missão ativa por prioridade de segurança.

## 10. Verificação antes do primeiro percurso

Não marque nenhuma unidade como pronta sem registrar os resultados em
[Estado, testes e limitações](ESTADO_TESTES_E_LIMITACOES.md). No mínimo, teste:

1. botão de emergência;
2. sentido de M1, M2 e M3;
3. parada LiDAR para frente, ré e duas laterais;
4. perda do LiDAR e perda da rede/controle;
5. volume de fala e reconhecimento de voz;
6. localização repetida no mapa;
7. navegação até cada destino, espera de 15 s e retorno à base.

## 11. Atualizar uma unidade já instalada

```bash
cd /home/onigiri/onigiri
git pull --ff-only
sudo install -m 644 deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart onigiri-udp.service onigiri-lidar.service onigiri-autonomous.service
```

Reinicie apenas os serviços de voz e missão que já tenham sido configurados para
aquela unidade. Após cada atualização, refaça os testes afetados.

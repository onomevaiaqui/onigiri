# Operação robótica: Raspberry Pi 4 e 5 / ROS 2 Jazzy

## Estado da entrega

Implementados: transporte Sabertooth, watchdog, mistura de chassis, extrínsecas medidas, RF2O, integração Nav2, posição no mapa ativo, operação de destinos e retorno à base, instalação/captura Gemini 2, rede inicial, backup, recuperação e construção de imagem SD. Nenhum movimento físico foi testado nesta entrega. A imagem gerada é um **instalador experimental**, com instalação automática pela Internet no primeiro boot; não é uma imagem offline certificada.

## Atualizar um Raspberry existente

Para o Robô sem LiDAR, siga [Robô RGB-D](ROBO_RGBD.md), usando `-InstalarRGBD` em vez de `-InstalarOdometria`.

Execute o instalador PowerShell entregue com o pacote usando `-InstalarRuntime -InstalarOdometria -InstalarCamera`. A compilação da câmera pode demorar e requer espaço livre e alimentação estável. Instalar não habilita o serviço de motores. Guarde mapas em andamento antes de atualizar: o painel será reiniciado. A atualização preserva banco, mapas e plataforma. O instalador guarda backup dos arquivos gerenciados e tenta restaurá-los se a atualização falhar; o ambiente virtual Python não é revertido.

Instalação a partir de um clone em `/home/onigiri/onigiri`:

```bash
bash deploy/scripts/install_admin_web.sh
bash deploy/scripts/install_robot_runtime.sh
bash deploy/scripts/install_lidar_odometry.sh
bash deploy/scripts/install_orbbec.sh
```

## Chassis e ligação serial

Configurações → Plataforma e sensores:

- Onigiri original mantém seu driver/HAT anterior. O novo serviço de base recusa esse perfil e não substitui o driver original.
- Tank: M1 esquerda, M2 direita. Uma Sabertooth 2x32 USB direta ou 2x60 por USB–TTL.
- Mecanum: M1 frente esquerda, M2 frente direita, M3 traseira esquerda, M4 traseira direita; rodas montadas no arranjo X. A orientação física dos roletes precisa corresponder às equações; teste os sentidos com as rodas suspensas.
- Quatro motores exigem dois controladores. Para dois 2x32 USB, selecione uma porta USB para cada placa. Para dois 2x60, pode usar S1 compartilhada com endereços distintos. Endereços padrão no formulário: 128 e 129; precisam coincidir com o hardware.

Prefira `/dev/serial/by-id/...`, listado por `ls -l /dev/serial/by-id/`. O código usa comandos legados Packetized Serial com checksum de sete bits, 8N1. No 2x32, aceite comandos legados na configuração DEScribe, não apenas comandos CRC. O 2x60 recebe autobaud 0xAA; o 2x32 USB não precisa desse byte. O driver configura serial timeout em 300 ms, envia zero ao abrir/fechar e usa trava exclusiva de porta.

## Medições e comissionamento

Cadastre largura/comprimento **externos**, distância entre esteiras/rodas, distância entre eixos, velocidade máxima medida, limite inicial de potência e inversão de cada motor. As velocidades são convertidas em potência por uma aproximação de malha aberta; não há encoders nem controle fechado de RPM. O limite inicial é 20%, não uma calibração do seu robô.

Meça LiDAR e câmera em relação a `base_footprint`: x para frente, y para esquerda, z para cima; roll/pitch/yaw em radianos. Confirme as medições. Sem essa confirmação a stack e o novo serviço da base não iniciam. TFs fixas de teste não são usadas na navegação.

A base inicia desarmada. Para permitir seu uso, configure `ONIGIRI_MOTION_ENABLED=1` em `/etc/onigiri/admin.env` e, após revisar fiação, sentidos e parada física, execute:

```bash
sudo systemctl restart onigiri-admin-web
sudo systemctl start onigiri-base
```

Alterar a configuração enquanto o serviço está ativo o desarma e encerra; reinicie-o explicitamente para adotar os novos valores. O serviço conflita com `onigiri-udp`, para evitar dois drivers simultâneos. Ele não é habilitado automaticamente no boot pelo instalador. Não habilite dois nós publicando comandos de tração ao mesmo tempo. A parada do painel é software; uma parada física independente deve ser ligada conforme o manual do controlador. No 2x60 Packetized Serial, consulte a função de emergência de S2 no manual; não extrapole a ligação para o 2x32.

A base desarma se ficar sem comando por 300 ms, sem scan ou odometria válida por 500 ms ou se houver obstáculo no raio conservador `metade da diagonal externa + 0,10 m`. Isso bloqueia também giro no lugar perto de obstáculos. A emergência fica latched: liberar não rearma. Após armar, há até 10 s para o primeiro comando; depois vale o watchdog de 300 ms.

## Mapear, localizar e navegar

Sem encoders, RF2O estima odometria pelo LiDAR. Corredores sem estrutura, superfícies ruins e cenas degeneradas podem perder a estimativa; a base recusa odometria não finita ou atrasada. Não há estimativa de posição a partir da potência dos motores. A versão RF2O é fixada em `b38c68e...` com patch local para aguardar TF antes de inicializar; outras alterações locais não reconhecidas são preservadas e interrompem a instalação.

1. Mapeie e salve no painel. Capturas de teste parado não são aceitas para navegação.
2. Encerre o SLAM. Em Missões, clique Conectar ROS, selecione o mapa e Iniciar localização e Nav2.
3. Informe x/y/orientação inicial reais. Aguarde Nav2 disponível e posição recebida. O marcador do robô só aparece ao abrir **o mesmo mapa salvo** usado pela stack, enquanto a TF estiver atualizada.
4. Edite os pontos e confira o campo Mapa salvo deste ponto. Destinos antigos sem associação precisam ser associados ao mapa correto; um ponto de outro mapa não pode ser enviado. Arme a base, selecione o destino e clique Ir ao destino. O painel primeiro informa que enfileirou a solicitação; o ROS confirma aceitação ou recusa.
5. Retornar à base envia um objetivo ao ponto marcado como base. Cancelar desarma e cancela o objetivo. Ao chegar, a base é desarmada. O retorno desta interface é explícito, não automático após uma espera.

Nav2 usa AMCL, costmaps com LiDAR e geometria do robô, planejador, DWB e suavizador. O perfil mecanum habilita velocidade lateral e modelo AMCL omnidirecional; os outros perfis usam diferencial. Valores de aceleração e distâncias de inflação ainda precisam ser ajustados e testados no robô. No perfil sem LiDAR com Gemini 2, RTAB-Map fornece odometria/localização e os pontos de profundidade alimentam os costmaps; consulte ROBO_RGBD.md para limites de movimento e campo de visão.

O monitor Gamepad continua local: não transmite movimento. Não execute a navegação com outro programa publicando `/cmd_vel` simultaneamente.

## Gemini 2

O instalador fixa OrbbecSDK_ROS2 em `c153462518ad674650bafa4464fda72c27ab797a`, compila com um processo e instala as regras udev. A instalação habilita os comandos da aba Sensores. Iniciar câmera executa o driver; Observar câmera inicia o assinante do painel. Parar câmera encerra também a prévia. Processos iniciados fora do painel precisam ser encerrados pelo seu responsável para evitar disputar a USB.

RGB até 640×480, profundidade visualizada de 0 a 5 m (preto também indica inválido) e IMU com idade de cada amostra. Campos de ambiente: `ONIGIRI_CAMERA_COLOR_TOPIC`, `ONIGIRI_CAMERA_DEPTH_TOPIC`, `ONIGIRI_CAMERA_IMU_TOPIC`. Confirme tópicos com `ros2 topic list -t`; os padrões são `/camera/color/image_raw`, `/camera/depth/image_raw`, `/camera/gyro_accel/sample`. A IMU não é fundida à odometria automaticamente. `ONIGIRI_CAMERA_AUTOSTART=1` inicia a câmera selecionada junto ao painel.

## Diagnóstico, backup e restauração

```bash
bash deploy/scripts/diagnose_robot.sh
python3 deploy/scripts/user_data.py backup /home/onigiri/meus-dados.tar.gz
sudo systemctl stop onigiri-base onigiri-udp onigiri-admin-web
python3 deploy/scripts/user_data.py restore /home/onigiri/meus-dados.tar.gz
sudo systemctl start onigiri-admin-web
```

Backup inclui SQLite consistente, plataforma, destinos exportados e mapas; exclui credenciais do sistema, ambiente virtual e logs. A restauração guarda um backup anterior e mantém arquivos extras de mapas que já existiam. A base não é reiniciada pela restauração. Diagnóstico de falhas de câmera/Nav2 aparece também em Missões → Diagnóstico dos processos.

## Imagem SD

A imagem `onigiri-pi4-pi5-instalador.img` foi montada a partir da imagem oficial Ubuntu 24.04.5 Server arm64 para Raspberry Pi, com SHA256 de origem conferido. Ela contém o código e um cloud-init de instalação. Use cartão de pelo menos 32 GB. O **boot físico ainda não foi validado** em Pi 4/5 e o instalador ARM64 precisa de teste no hardware.

1. Grave a imagem em um cartão dedicado. Não sobrescreva seu cartão atual sem backup.
2. Ethernet com DHCP e Internet é o padrão. Para Wi-Fi, gere `network-config` em Configurações → Rede da imagem SD e copie para a partição de boot antes do primeiro boot.
3. Ligue o Raspberry e aguarde a instalação. Consulte `cloud-init status --long` e `/var/log/cloud-init-output.log`; a conclusão cria `/var/lib/onigiri/provisioned`.
4. Acesse usando a chave privada entregue localmente, sem senha padrão compartilhada:

```powershell
ssh -i .\onigiri-image-ssh.key -N -L 8081:127.0.0.1:8080 onigiri@onigiri.local
```

Abra `http://localhost:8081`. A chave privada pertence a esta imagem local: preserve-a; não publique a imagem personalizada com essa chave de acesso para terceiros. Para distribuir imagens, gere um par de chaves por usuário/dispositivo. O construtor recebe apenas a chave pública. A imagem compartilhável ainda exige um fluxo de identidade por instalação.

Para reconstruir em Linux/WSL com suporte a loop/mount, use `sudo python3 deploy/scripts/build_sd_image.py --help`. O construtor copia a imagem de origem, valida o SHA256 fornecido e só trabalha em um arquivo .img novo; não grava dispositivos físicos. Os pacotes apt/pip instalados no primeiro boot dependem do repositório daquele momento; a instalação registra suas versões em `/var/lib/onigiri/packages.tsv`.

## Referências oficiais

- https://github.com/orbbec/OrbbecSDK_ROS2
- https://www.dimensionengineering.com/datasheets/Sabertooth2x60.pdf
- https://www.dimensionengineering.com/datasheets/Sabertooth2x32.pdf
- https://docs.nav2.org/
- https://cdimage.ubuntu.com/ubuntu/releases/24.04/release/

## Três opções de montagem

O seletor contém somente 2 motores com esteiras (Tank), 3 motores com omniball (Onigiri) e 4 motores com rodas mecanum. Configurações antigas de quatro rodas fixas exigem uma nova seleção explícita; não são convertidas automaticamente em mecanum. O perfil Onigiri preserva o driver e a fiação originais; os campos de inversão do novo runtime não reconfiguram o HAT legado.

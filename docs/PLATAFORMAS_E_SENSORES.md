# Plataformas e sensores

O guia atualizado está em [Operação robótica](OPERACAO_ROBOTICA.md). Ele cobre os perfis Onigiri, tank, mecanum e quatro rodas fixas, Sabertooth, Gemini 2, Nav2 e a imagem SD.

# Plataformas e sensores

No painel, abra Configurações → Plataforma e sensores. Escolha Raspberry Pi 4 ou 5, Onigiri original ou tank, o controlador e a câmera. O cadastro fica em data/platform.json (ONIGIRI_PLATFORM_FILE permite mudar o caminho) e sobrevive ao reinício. A atualização preserva esse arquivo.

O perfil Onigiri mantém o HAT existente. Tank admite Sabertooth 2x32 e 2x60, duas esteiras, sem movimento lateral. Meça a distância entre os centros das esteiras: 0,30 m é apenas um valor inicial. A função tank_tracks converte velocidades ROS em velocidades lineares das esteiras; ainda não envia comandos ao Sabertooth. O perfil não altera o serviço de motores existente. Os perfis mecanum e quatro rodas fixas têm equações e transporte para quatro motores; consulte o guia atualizado.

## Integração dos motores pendente

Os dois Sabertooth oferecem packetized serial. A ligação e configuração precisam ser confirmadas antes de habilitar movimento: porta serial utilizada, configuração do controlador, endereço, baud rate, sentido de cada motor, parada de emergência e watchdog. Não conectar uma porta RS-232 diretamente ao GPIO TTL do Raspberry. Não foi instalado nem ativado um serviço de motores do tank nesta etapa.

## Orbbec Gemini 2

Driver oficial: https://github.com/orbbec/OrbbecSDK_ROS2 (ramo v2-main). Siga as instruções oficiais de compilação e regras udev para Ubuntu 24.04 / ROS Jazzy. O driver precisa estar instalado no Raspberry, não apenas no WSL. Há suporte upstream a Jazzy e ARM64; esta atualização não valida fisicamente Raspberry Pi 4 ou 5. Use USB 3 e alimentação adequada.

Com o driver compilado e instalado, inicie a captura explicitamente:

```bash
cd /home/onigiri/onigiri
export ONIGIRI_ORBBEC_SETUP=/caminho/do/workspace_orbbec/install/setup.bash
bash deploy/scripts/start_gemini2.sh
```

O script verifica a existência do pacote, inicia RGB, profundidade e IMU e deixa a nuvem de pontos desligada para reduzir processamento. Não inicia motores. Para descobrir os tópicos realmente publicados:

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic list -t
```

O cadastro por si só não confirma conexão. A prévia RGB possui estados próprios de recebimento. A Gemini 2 não fornece automaticamente odometria ao SLAM existente. A montagem câmera/base exige extrínsecas medidas; não foi criada uma TF aproximada. Firmware, modos de imagem, taxa de captura e funcionamento no hardware ainda precisam de validação.

Referências: https://www.dimensionengineering.com/datasheets/Sabertooth2x32.pdf e https://www.dimensionengineering.com/products/sabertooth2x60 .

## Conexões escolhidas para o tank

- Sabertooth 2x32: USB direto ao Raspberry, usando o dispositivo serial exposto pelo controlador.
- Sabertooth 2x60: adaptador USB para serial TTL.

Configurações guarda porta, endereço e baud rate, sem abrir a porta. Prefira o caminho estável listado por `ls -l /dev/serial/by-id/`. O baud rate/endereço e o modo Packetized Serial devem corresponder ao controlador. No 2x32, o codec usa os comandos legados com checksum de 7 bits: a configuração que aceita somente comandos CRC precisa estar desabilitada para esse protocolo. Isso ainda requer teste físico.

Em Configurações, Simulador das esteiras calcula a potência normalizada e mostra os bytes dos dois canais: M1 esquerdo, M2 direito. Frente e giro positivos seguem, respectivamente, avanço e rotação anti-horária. O simulador permite inverter cada lado. Quando há saturação, as duas potências são divididas pelo mesmo fator, preservando a proporção. Não é odometria, nem controle fechado de velocidade; não abre USB nem transmite pacotes. Zerar simulação apenas zera os valores na tela.

## Prévia RGB no painel

Depois de instalar e iniciar o driver, habilite `ONIGIRI_CAMERA_PREVIEW_ENABLED=1` em `/etc/onigiri/admin.env` e reinicie somente o painel. Configure `ONIGIRI_CAMERA_COLOR_TOPIC` para o tópico Image RGB publicado pela sua instalação; padrão `/camera/color/image_raw`. Em Sensores, clique Observar câmera. O painel inicia somente um assinante ROS; Encerrar prévia encerra esse assinante e preserva o driver externo.

A prévia aceita rgb8, bgr8 e mono8, reduz para no máximo 640×480 e processa até quatro imagens por segundo. O painel consulta até duas vezes por segundo, apenas enquanto a aba Sensores está visível. Depois de três segundos sem atualização, a imagem aparece como atrasada. Profundidade e IMU ainda não têm visualização no painel. A habilitação não inicia a câmera automaticamente na inicialização do sistema.

# Robô e plataforma comum Onigiri

O mesmo painel atende três chassis: Onigiri de três rodas omniball, tanque de duas esteiras e mecanum de quatro motores. Selecione Raspberry Pi 4 ou 5 e o controlador compatível. O perfil é persistente; mudar de robô não exige outro painel.

## Atualização do Raspberry existente

No PowerShell, execute o instalador entregue:

```powershell
.\Instalar-Onigiri.ps1 -InstalarRuntime -InstalarCamera -InstalarRGBD
```

A instalação requer Internet. Para um clone já existente no Raspberry, execute na raiz do repositório:

```bash
bash deploy/scripts/install_robot_runtime.sh
bash deploy/scripts/install_orbbec.sh
bash deploy/scripts/install_rgbd.sh
```

O painel reinicia. Mapas, destinos e plataforma persistidos são preservados. A instalação não habilita motores automaticamente.

## Configurar e usar

1. Em **Configurações → Plataforma e sensores**, clique em **Preencher perfil tanque RGB-D**: Raspberry 4, tanque, Sabertooth 2x32 USB, Gemini 2, sem LiDAR.
2. Preencha **Nome do robô**, se desejar. Esse nome serve apenas para organização. Abra **Portas, dimensões e calibração**. Informe a porta real `/dev/serial/by-id/...`, dimensões medidas, distância entre esteiras e posição/orientação da câmera em relação à base. Confirme as medições e salve. O preset não inventa esses valores.
3. Em **Mapas e destinos**, use **Mapear com Gemini 2**. O painel inicia a câmera e RTAB-Map, mostra a prévia e permite salvar a captura. Nenhum comando de movimento é enviado ao iniciar o mapeamento.
4. Salve e abra o mapa. No mesmo painel de posicionamento, cadastre, edite ou exclua destinos e a base. Os pontos ficam associados ao mapa selecionado.
5. Para localização posterior, abra esse mapa: além de YAML/PGM, o sistema guarda `rtabmap.db`. Preserve os três arquivos; somente a imagem não basta para relocalização visual.

Com LiDAR selecionado, continua sendo usado o fluxo LiDAR/RF2O. Sem LiDAR e com Gemini 2 selecionada, o fluxo muda automaticamente para RGB-D. O mapeamento com câmera usa odometria visual, não odometria fictícia de motores.

## Câmera e movimento

RGB, profundidade registrada no RGB e CameraInfo devem ter calibração e sincronização corretas. Padrões: `/camera/color/image_raw`, `/camera/depth/image_raw`, `/camera/color/camera_info`. Ajustes em `/etc/onigiri/admin.env`: `ONIGIRI_CAMERA_COLOR_TOPIC`, `ONIGIRI_CAMERA_DEPTH_TOPIC`, `ONIGIRI_CAMERA_INFO_TOPIC`. O instalador habilita `ONIGIRI_RGBD_ENABLED=1`.

O modo RGB-D usa pontos de profundidade nos costmaps. A câmera cobre apenas a frente; não fornece cobertura de 360 graus. Nesse modo o novo serviço de base bloqueia ré e movimento lateral, limita avanço a 0,1 m/s e rotação a 0,2 rad/s e para com percepção/odometria inválida ou atrasada. A câmera deve estar voltada para frente. A IMU não é fundida automaticamente. O controle Gamepad do navegador continua sendo monitoramento local.

Sabertooth: M1 esquerda e M2 direita; configure o 2x32 para comandos legados Packetized Serial. Medições, sentido dos motores, desempenho visual e distância de parada precisam ser validados no robô físico. A integração foi testada em WSL com ROS real e imagens sintéticas, sem acionar motores; a instalação e operação na Gemini 2/Raspberry ainda precisam dessa validação.

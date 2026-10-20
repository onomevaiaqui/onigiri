# Odometria pelo LiDAR — experimental

Objetivo: testar o deslocamento do sensor e mapear sem encoders, usando RF2O.
Não aciona motores nem inicia navegação. Não certifica posição do centro do robô.

## Arquitetura

- Driver existente publica `/scan` com `frame_id: laser`.
- RF2O estima movimento entre scans, publica `/odom_rf2o` e TF `odom → laser`.
- SLAM Toolbox usa `base_frame: laser`, gerando `map → odom` e `/map`.
- O painel mostra a prévia normalmente e identifica mapas como `lidar-odometry`.

Esta primeira configuração trata o próprio LiDAR como referência móvel, evitando
inventar a transformação física sensor/base. Para navegação do robô ainda será
necessário medir a montagem e integrar a referência da base. Não utilizar com TF
fixa de Teste parado, nem junto a outro publicador concorrente de odometria.

## Instalação no Raspberry Pi 4

Atualizar o pacote e executar o instalador Windows com `-InstalarOdometria`.
O script opcional `deploy/scripts/install_lidar_odometry.sh` instala dependências,
compila RF2O num workspace próprio com um único job e habilita o novo modo apenas
após sucesso. Não substitui um workspace ROS já existente. Arquivos modificados
no checkout RF2O interrompem a atualização, sem resetar alterações.

A revisão fixada é `b38c68e46387b98845ecbfeb6660292f967a00d3`, branch `ros2`, do
[repositório oficial MAPIRlab](https://github.com/MAPIRlab/rf2o_laser_odometry/tree/b38c68e46387b98845ecbfeb6660292f967a00d3).
O código e licença são obtidos diretamente desse repositório.

O script configura `ONIGIRI_LIDAR_ODOMETRY_ENABLED=1` e
`ONIGIRI_ODOMETRY_SETUP=/home/onigiri/onigiri-odometry/rf2o-b38c68e/install/setup.bash`
em `/etc/onigiri/admin.env`, preservando o setup ROS geral. Reinicia somente o
painel. SLAM e RF2O só iniciam por ação explícita na interface. A atualização do
painel encerra qualquer captura atual; salve antes.

## Primeiro teste físico

1. Confirmar leituras `/scan` e LiDAR nivelado, rigidamente montado.
2. Encerrar Teste parado. Em Modo de captura, selecionar Odometria pelo LiDAR.
3. Iniciar e conferir erros antes de qualquer deslocamento.
4. Testar movimento lento em plano horizontal, com tração desativada e método
   de deslocamento manual apropriado à montagem; não tocar na parte giratória.
5. Conferir se `/odom_rf2o` e a prévia mudam coerentemente e se a estimativa volta
   próxima à origem após retornar ao ponto inicial. Perda de tracking e deriva
   são possíveis, sobretudo em corredores, ambientes pouco estruturados ou
   com pessoas/objetos móveis. Não usar para navegação automática sem validação.

## Evidências e limites

Compilado em Ubuntu/ROS Jazzy no WSL (x86_64). Teste sem hardware, isolado por
domínio DDS/local host, recebeu 94 mensagens de odometria e estimou 0,358 m para
um movimento sintético de 0,345 m num ambiente retangular.
Também foi executado o perfil integrado RF2O + SLAM Toolbox com essas leituras:
o SLAM publicou um mapa de 160 × 120 células e recebeu 95 mensagens de odometria.
Esses testes verificam execução
e integração básica dos parâmetros; não demonstra precisão no LiDAR real nem
compilação/desempenho ARM64 no Pi 4. A instalação e os testes físicos são pendentes.

O perfil usa frequência RF2O de 10 Hz e integração SLAM a partir de 0,05 m ou
0,05 rad, para observar pequenos deslocamentos. Esses parâmetros são iniciais.
Um supervisor acompanha RF2O e SLAM; se um processo encerrar, encerra o outro.
Parar o mapeamento também encerra o leitor da prévia e ambos os processos.

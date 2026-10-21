# Mapeamento no painel e imagem SD do Onigiri

Este fluxo é exclusivo do LiDAR do Onigiri original. Para instalação e conexão Wi-Fi atuais, consulte [Primeiro acesso](PRIMEIRO_ACESSO.md). Os exemplos abaixo registram o fluxo de diagnóstico e mapeamento.

Alvo confirmado pelo usuário: Raspberry Pi 4, Ubuntu 24.04.5 LTS e ROS 2 Jazzy.
Confirmar ARM64 na unidade antes de gerar a imagem distribuível.

## Perfil experimental recuperado do histórico

O histórico de terminal enviado pelo usuário contém:

```bash
source /opt/ros/jazzy/setup.bash
ros2 launch slam_toolbox online_async_launch.py
ros2 run nav2_map_server map_saver_cli -f ~/onigiri_map --ros-args -p map_subscribe_transient_local:=true
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap "{name: {data: '/home/onigiri/onigiri_map'}}"
```

Essas linhas mostram tentativas anteriores, não comprovam quais terminaram com
sucesso. Não há referência a um YAML personalizado no comando de lançamento.
O painel agora permite marcar **Usar parâmetros padrão do SLAM — experimental**.
Nesse perfil ele não exige `ONIGIRI_SLAM_PARAMS` e usa explicitamente
`use_sim_time:=false` para o hardware real. O serviço do painel ainda exige
`ONIGIRI_MAPPING_ENABLED=1` no Raspberry; a instalação mantém esse valor em zero.

O histórico também contém TF estáticas de `base_footprint` para `laser` e de
`odom` para `base_footprint`, com deslocamentos nulos. O perfil experimental normal não inicia essas
TF: a segunda fixa a pose, não mede deslocamento, e a primeira precisa refletir
a posição física do sensor. A integração deve fornecer as TF apropriadas.

### Teste parado com TF temporárias

Após confirmar `/scan` com frame `laser` e a ausência de `odom` na unidade, foi
adicionado o modo explícito **Teste parado**. Ele usa as configurações padrão do
SLAM e cria duas TF identidade temporárias: `odom → base_footprint → laser`.
Os deslocamentos nulos são uma aproximação do teste antigo, não uma calibração.
O robô deve permanecer imóvel. O modo não deve ser usado junto a publicadores
de odometria/TF reais nem para mapeamento em movimento ou navegação.

Um supervisor acompanha os três processos; se um terminar, encerra os demais.
Encerrar o mapeamento ou o serviço do painel também encerra as TF temporárias.
Esse modo nunca é escolhido automaticamente, não inicia serviços de motores e
registra mapas salvos como `stationary-preview`, visíveis como **teste parado**.
Para o modo normal, desmarcar Teste parado e fornecer TF/odometria reais.
Mapas capturados no perfil experimental são identificados como experimentais
na biblioteca e ao abrir. Isso não certifica os mapas do perfil configurado.

Para habilitar o serviço **depois de transferir esta versão ao Raspberry**:

```bash
sudo install -d /etc/onigiri
# Se admin.env já existir, editar e preservar as demais opções.
sudo nano /etc/onigiri/admin.env
```

Configurar `ONIGIRI_MAPPING_ENABLED=1` e o diretório de mapas conforme o template
`config/admin.env.example`, instalar o serviço atualizado com `EnvironmentFile`,
então reiniciar `onigiri-admin-web`. Para teste experimental, marcar a opção no
painel antes de iniciar; para perfil configurado, informar o YAML validado.
Esta etapa não instala/inicia o LiDAR nem resolve TF ou odometria.

O [serviço SaveMap do SLAM Toolbox Jazzy](https://github.com/SteveMacenski/slam_toolbox/blob/jazzy/src/map_saver.cpp)
usa internamente `map_saver_cli` com recebimento transient local. O painel chama
diretamente essa ferramenta, limita o tempo e verifica o par YAML/PGM antes de
registrar sucesso; ele não depende apenas da saída do cliente de serviço ROS.

## O que está implementado

Em **Mapas e destinos**, o painel oferece iniciar/encerrar o SLAM, salvar uma
captura ROS com nome, guardar um par YAML/PGM já existente e reabrir mapas salvos.
Os arquivos ficam em `data/maps/<nome>/map.yaml` e `map.pgm`, com referência de
imagem relativa. Nomes repetidos são recusados para não perder um mapa existente.
O mapa reaberto também aparece no dashboard. Os mapas não fazem parte do backup
JSON de destinos: inclua `data/maps` no backup da unidade.

No computador sem ROS configurado, a captura fica indisponível. A biblioteca e
a importação funcionam, sem produzir mapas fictícios. A captura salva um snapshot
do tópico `/map`; a prévia do mapeamento acompanha esse tópico separadamente.
Não há retomada de um pose graph do SLAM.
Salvar não encerra a captura. Use **Encerrar mapeamento** ao terminar.

### Prévia ao vivo

Ao iniciar o SLAM pelo painel, um processo Python do ROS lê `/map` (OccupancyGrid)
sem publicar comandos. Ele transforma o mapa em PNG em memória e disponibiliza
um snapshot temporário, substituído atomicamente. Não cria mapas na biblioteca.
O navegador consulta a prévia a cada 400 ms enquanto a tela está visível;
a atualização real depende da frequência com que o SLAM publica. O leitor limita
o processamento a até cinco imagens por segundo e mapas de até 4 milhões de células.

Branco representa livre, preto ocupado e cinza desconhecido. A prévia não mostra
posição do robô nem mede se o LiDAR está conectado: ela indica recepção de `/map`.
Depois de 15 segundos sem mensagens novas, conserva a última imagem com aviso
**Sem atualização**. Sem mapa, informa para verificar LiDAR, SLAM e TF. Ao encerrar
a captura, o leitor para e o snapshot temporário é removido. A imagem ao vivo é
separada do mapa salvo usado para cadastrar destinos.

O leitor usa `/usr/bin/python3` com `rclpy` e `nav_msgs` do ROS Jazzy; o ambiente
virtual do FastAPI não precisa instalar ROS via pip. A assinatura usa QoS
best-effort/volatile para compatibilidade; ao iniciar tarde, espera a próxima
publicação, em vez de exigir histórico transient-local.

Nenhuma destas operações inicia navegação ou publica comandos aos motores.
O deslocamento durante a coleta precisa ser feito por um método já validado
para o robô. Iniciar SLAM não implica que um mapa utilizável já esteja disponível.
O projeto registra ausência de encoders/odometria física: essa limitação precisa
ser resolvida/validada para navegação confiável; a interface não a substitui.

## Habilitar captura no Raspberry

1. Validar LiDAR, tópico `/scan`, TF e odometria, além do YAML do SLAM da unidade.
   Não iniciar outro SLAM manualmente ao usar o gerenciamento do painel.
2. Confirmar pacotes `slam_toolbox` e `nav2_map_server` no ROS Jazzy.
3. Configurar o serviço do painel para ler `/etc/onigiri/admin.env` (template em
   `config/admin.env.example`). Definir o YAML validado em `ONIGIRI_SLAM_PARAMS`;
   se necessário, informar o setup do workspace em `ONIGIRI_ROS_SETUP`.
4. Somente na unidade validada, definir `ONIGIRI_MAPPING_ENABLED=1` e reiniciar
   o serviço do painel. Manter um único worker Uvicorn: ele é dono do processo SLAM.
5. Abrir pelo túnel SSH/localhost, iniciar a captura, percorrer o ambiente e
   salvar. Em falha, consultar `data/maps/slam.log` e o journal do serviço.

O worker usa comandos fixos, sem interpolar nomes do usuário em shell:

```bash
ros2 launch slam_toolbox online_async_launch.py use_sim_time:=false slam_params_file:=CAMINHO_VALIDADO
ros2 run nav2_map_server map_saver_cli -f DESTINO --fmt pgm --ros-args -p save_map_timeout:=10.0
```

Documentação: [SLAM e salvamento no Nav2](https://docs.nav2.org/tutorials/docs/navigation2_with_slam.html)
e [CLI do map saver Jazzy](https://api.nav2.org/nav2-jazzy/html/main__cli_8cpp_source.html).

## Caminho para plug and play

A imagem `.img` ainda não foi criada. Empacotar apenas o repositório não resolve
drivers, rede, calibração e particularidades de cada montagem. A entrega deve ser
uma imagem versionada para Pi 4 com um assistente inicial:

1. Base ARM64 fixa, ROS e dependências com versões registradas e build reproduzível.
2. Aplicação e serviços instalados; armazenamento gravável separado para mapas,
   destinos, perfis e calibração. Hoje perfis de controle ficam no navegador.
3. Primeiro boot: expandir disco, gerar identidade e chaves SSH únicas, criar
   credenciais próprias e configurar rede, sem embutir segredos de uma unidade.
4. Assistente para testar LiDAR, emergência, áudio, controle, TF e odometria;
   salvar configuração de hardware por unidade, incluindo identificadores USB.
5. Acesso fácil ao painel com descoberta local e autenticação; não expor os
   endpoints atuais em uma rede pública. Acesso remoto permanece por túnel SSH
   enquanto essa camada não for implementada.
6. Fluxo guiado: verificar hardware → mapear → salvar → cadastrar destinos →
   validar localização/navegação. Boot não deve movimentar o robô automaticamente.
7. Backup/restauração de toda a configuração e mapas, atualização com recuperação,
   desligamento seguro e teste após queda de energia.
8. Gerar imagem sem mapas pessoais, históricos, senhas nem chaves do construtor;
   publicar checksum e validar em um cartão novo no hardware real.

Critério de aceite final: gravar o cartão, ligar uma unidade compatível, concluir
o assistente sem terminal, mapear/salvar/reabrir e recuperar configurações após
reiniciar. A instalação atual é uma base de desenvolvimento, não essa entrega final.

### Navegação da prévia

Arrastar move a visualização. A roda do mouse, os botões +/− e a pinça no celular
controlam o zoom. Ajustar à área ou clique duplo restaura o enquadramento. Com a
área focada, setas movem, +/− alteram zoom e 0 ajusta. O enquadramento é mantido
entre mensagens e reiniciado quando a captura para. São operações apenas visuais.

A interface distingue idade da mensagem e idade da última alteração do mapa.
Mensagens periódicas com conteúdo idêntico não contam como alterações. Imagem,
resolução, origem e referencial participam dessa comparação. No Teste parado,
odometria fixa pode impedir novas integrações de scans: mover o sensor não
fornece odometria e não é validado como mapeamento em movimento.

### Mapeamento com odometria do LiDAR

Perfil opcional RF2O + SLAM, com rastreamento de laser no lugar de TF fixa.
Instalação, testes sintéticos e limites: [Odometria LiDAR](ODOMETRIA_LIDAR.md).
Ainda depende de compilação e validação física no Pi 4; não habilita navegação.

### Taxa de atualização e cores

O SLAM publica o mapa a cada 1 segundo nos perfis gerenciados. No perfil LiDAR,
o intervalo mínimo entre leituras processadas é 0,1 s; o gatilho espacial
continua em 0,05 m/rad. O leitor da prévia admite até 5 Hz, e a tela consulta
a cada 400 ms, separadamente da consulta do estado (2 s). Imagens iguais não
são reenviadas ao navegador: o token é a última alteração de conteúdo/geometria.
Zoom e posição continuam preservados. A margem e o desconhecido usam cinza 205
(#cdcdcd), compatível com o mapa PGM padrão; livre/ocupado mantêm seus valores.
No teste ROS integrado no WSL, foram recebidos 7 mapas com intervalo médio
de 1,00 s. O desempenho no Pi e a alteração efetiva de conteúdo ainda dependem
de carga, tracking e novas leituras aceitas pelo SLAM.

### Pontos no mapa: destino e base

Ao selecionar uma célula livre, escolher Destino ou Base antes de Adicionar ponto.
O formulário permite alterar o tipo, nome, coordenadas e demais dados. Clicar
em um marcador existente abre o formulário com Editar/Excluir ponto. A exclusão
pede confirmação e se reflete no mapa e na lista. A troca de base é atômica: a
base anterior vira destino. Para excluir ou rebaixar a base ativa, definir outra
base antes. Marcadores não indicam posição medida do robô.

### Exclusão confirmada no painel

A confirmação usa um diálogo HTML, sem depender de confirm/alert nativos. A base
ativa pode ser removida escolhendo uma substituta na mesma operação atômica.
A seleção temporária é limpa ao salvar/excluir, para não deixar um pino roxo
parecendo um ponto que já foi removido. Limpar seleção remove somente esse pino,
sem apagar cadastros. Os fluxos foram testados com FastAPI e banco temporário.

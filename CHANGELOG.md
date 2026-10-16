# Registro de versões

Este arquivo registra mudanças relevantes da plataforma Onigiri. As versões descrevem o estado do protótipo e não representam um produto final.

## [Em desenvolvimento]

### Adicionado

- Painel web local para cadastrar destinos, sinônimos e frases de solicitação por voz.
- Simulação segura do fluxo de missão no computador, sem ROS 2, Nav2 ou acionamento de motores.
- Exportação de destinos em JSON compatível com o nó de missões do Raspberry Pi.
- Configuração por destino da fala de chegada, tempo de espera e retorno à base.
- Revisão automática do cadastro para identificar frases ambíguas e posições de
  mapa ainda pendentes.
- Backup e restauração local dos destinos cadastrados.
- Reconhecimento de frases por palavras completas, evitando que destinos curtos
  sejam ativados acidentalmente dentro de outras palavras.
- Teste em lote de frases diretamente no painel local.
- Serviço e instalador preparados para o painel no Raspberry Pi, com acesso
  restrito a túnel SSH e sem abertura de porta pública.
- Recarga segura de destinos exportados quando o gerenciador de missões estiver
  ocioso.
- Roteiro de validação local do painel antes da instalação no Raspberry Pi.
- Gerador local de frases sugeridas e editáveis para acelerar o cadastro de
  comandos de voz por destino.
- Revisão de pré-implantação: interface sem interpretação de HTML cadastrado,
  validação de backup malformado e formulário sempre limpo ao abrir.
- Visualizador local do mapa ROS 2: leitura do par `.yaml` e `.pgm`, cálculo de
  coordenadas de destino por clique e bloqueio de posições em obstáculos ou
  regiões ainda desconhecidas.

### Validado

- Cadastro, edição, interpretação, exportação, backup, restauração e simulação
  do painel no Windows, incluindo uma rodada controlada da API.

### Ainda em validação física

- Instalação do painel no Raspberry Pi e integração com a navegação, áudio e reconhecimento de voz.

## [0.2.0] - 2026-10-14

### Adicionado

- Referência técnica ao conceito Omni-Ball da Universidade de Osaka, que inspira as rodas esféricas adaptadas do Onigiri.
- Licença MIT para código e serviços, com CERN-OHL-S v2 para o CAD e hardware original.
- Reconhecimento de voz offline preparado com Vosk e microfone integrado à webcam UVC.
- Modelo CAD do chassi no formato STEP em `cad/Onigiri.step`.
- Organização do repositório por plataforma: Raspberry Pi, Windows, implantação e CAD.
- Página inicial com visão geral do robô e estado de desenvolvimento.
- Documento de arquitetura e guia para uso do modelo CAD.
- Proteção LiDAR para ré e deslocamentos laterais no controlador do Raspberry.
- Procedimento de teste para percurso com múltiplos obstáculos.
- Projeto elétrico e procedimento de validação para o botão de parada de emergência.
- Camada de missão com destinos nomeados, espera de 15 segundos e retorno à base via Nav2.
- Interface ROS para fala e cancelamento de missão pelo controle manual.
- Definição da webcam UVC com microfone integrado como entrada planejada para reconhecimento de voz.

### Validado

- Controle dos três motores DC.
- Leitura do RPLIDAR A1M8 no ROS 2.
- Parada frontal e autonomia reativa experimental.
- Controle manual por Logitech F710 via rede Tailscale.
- Inicialização dos serviços do Raspberry Pi com `systemd`.

## [0.1.0] - 2026-10-08

### Primeira base integrada

- Raspberry Pi 4 com Ubuntu 24.04 e ROS 2 Jazzy.
- Stepper Motor HAT v0.2 e três motores JGY370.
- LiPo 3S, Tobsun EA75-5V e RPLIDAR A1M8.
- Primeiro mapa experimental salvo com `slam_toolbox`.

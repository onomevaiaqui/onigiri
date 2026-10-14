# Registro de versões

Este arquivo registra mudanças relevantes da plataforma Onigiri. As versões descrevem o estado do protótipo e não representam um produto final.

## [0.2.0] - 2026-10-14

### Adicionado

- Modelo CAD do chassi no formato STEP em `cad/Onigiri.step`.
- Organização do repositório por plataforma: Raspberry Pi, Windows, implantação e CAD.
- Página inicial com visão geral do robô, estado de desenvolvimento e próximos marcos.
- Documento de arquitetura e guia para uso do modelo CAD.
- Proteção LiDAR para ré e deslocamentos laterais no controlador do Raspberry.
- Procedimento de teste para percurso com múltiplos obstáculos.

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

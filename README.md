# Onigiri

> **Plataforma aberta de robótica assistiva, em desenvolvimento, para orientar pessoas e navegar com segurança em ambientes internos com ROS 2.**

O Onigiri é mais do que um conjunto de códigos. É uma plataforma aberta que reúne mecânica, eletrônica, software, documentação, CAD e testes para criar um robô-guia acessível, adaptável e reproduzível.

O objetivo é apoiar a orientação de pessoas em empresas, escolas, supermercados, eventos e projetos acadêmicos. No cenário final, uma pessoa poderá solicitar um destino por voz, acompanhar o robô com segurança e receber uma confirmação ao chegar ao local.

## Estado do projeto

O projeto está em desenvolvimento. A base física e de software já foi validada, enquanto a navegação por mapa, a interação por voz e o retorno automático à base seguem como próximas etapas.

### O que já funciona

- Tração com três motores DC: frente, ré, giro e deslocamento lateral.
- Controle remoto por Logitech F710 em um PC Windows, usando rede Tailscale.
- RPLIDAR A1M8 publicando leituras no ROS 2.
- Proteção LiDAR a 35 cm para frente, ré e deslocamentos laterais implementada, pendente de validação física.
- Autonomia reativa experimental para parar e desviar de obstáculos.
- Prioridade para o controle manual.
- Inicialização automática no Raspberry Pi por serviços `systemd`.
- Primeiro mapa experimental gerado com `slam_toolbox`.

### Próximas etapas

1. Validar percursos com múltiplos obstáculos.
2. Integrar câmera, áudio e interface de voz.
3. Localizar o robô no mapa, cadastrar destinos e navegar até eles.
4. Implementar chegada ao destino, espera e retorno à base.

> A autonomia atual é reativa. A navegação por mapa e o retorno automático ainda dependem de configuração e validação; o reconhecimento de voz offline está preparado, mas requer o modelo Vosk e validação do microfone da webcam.

## Plataforma

| Camada | Componentes atuais |
|---|---|
| Computação | Raspberry Pi 4, Ubuntu 24.04 e ROS 2 Jazzy |
| Tração | 3 motores JGY370 12 V, 40 RPM e Stepper Motor HAT v0.2 |
| Percepção | RPLIDAR A1M8 |
| Visão e voz | Webcam UVC com microfone integrado |
| Alimentação | LiPo 3S 11,1 V e conversor Tobsun EA75-5V |
| Controle | Logitech F710 em PC Windows via Tailscale |
| Projeto mecânico | Modelo CAD em STEP compartilhado neste repositório |

## Estrutura do repositório

```text
cad/                    Modelo 3D compartilhado do robô
deploy/systemd/          Serviços de inicialização do Raspberry Pi
docs/                    Manual, especificação e arquitetura
software/raspberry/     Controle de motores e autonomia em ROS 2
software/windows/        Ponte e ferramentas do Logitech F710
config/                 Destinos nomeados e ponto de retorno
CHANGELOG.md             Registro das atualizações do projeto
```

## Comece pelos documentos

- [Manual de construção e operação](docs/MANUAL_DE_CONSTRUCAO.md)
- [Especificação de produto](docs/ESPECIFICACAO_DE_PRODUTO.md)
- [Arquitetura da plataforma](docs/ARQUITETURA.md)
- [Integração do botão de emergência](docs/BOTAO_DE_EMERGENCIA.md)
- [Missões, destinos e interação por voz](docs/MISSOES_E_DESTINOS.md)
- [Modelo CAD em STEP](cad/README.md)
- [Registro de versões](CHANGELOG.md)

## Segurança

- Desligue a bateria LiPo antes de alterar cabos, motores ou o HAT.
- Não conecte outro carregador ou fonte USB-C ao Raspberry enquanto o Tobsun o estiver alimentando.
- Antes de testar, mantenha pessoas, cabos e objetos fora da área de movimento.
- O LiDAR e o software são camadas de proteção. Eles não substituem supervisão humana nem um corte físico de alimentação.
- O [botão de parada de emergência](docs/BOTAO_DE_EMERGENCIA.md) está planejado para cortar fisicamente a tração dos motores.

## Contribuição

O Onigiri evolui por meio de testes, documentação e colaboração. Ao contribuir, registre o que foi alterado, como foi validado e quais limitações ainda permanecem.

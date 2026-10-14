# Estado, testes e limitações

## Aviso de desenvolvimento

O Onigiri é um protótipo aberto em desenvolvimento. Este repositório contém
código, CAD, esquemas de implantação e instruções para reproduzir a plataforma,
mas **não certifica segurança, confiabilidade nem aptidão para uso sem
supervisão**. Há testes físicos pendentes e bugs podem existir.

Não utilize o Onigiri para transportar pessoas, em áreas públicas sem
supervisão, próximo a escadas, desníveis, vias, crianças, animais ou situações
em que uma falha de movimento possa causar dano.

## Implementado no código

- Controle de três motores por UDP e ROS 2.
- Prioridade do controle manual sobre autonomia e missões.
- Proteção por setores LiDAR para frente, ré e laterais.
- Autonomia reativa básica.
- Driver do RPLIDAR A1M8 por serviço.
- Preparação de reconhecimento de voz offline com Vosk e microfone da webcam.
- Fala local com `espeak-ng`.
- Fluxo de missão: destino, chegada, espera de 15 s e retorno à base, dependente
  de Nav2 e localização configurados.
- Botão de emergência definido eletricamente, ainda dependente de instalação e
  teste físico.

## Pendências obrigatórias de validação física

| Área | Critério mínimo de aceitação |
|---|---|
| Botão de emergência | Interrompe M1, M2 e M3 em todos os comandos; Raspberry permanece operacional; rearme consciente. |
| Alimentação | Tensão do Raspberry permanece estável sob partida e frenagem dos motores. |
| Motores | Sentidos e combinações correspondem ao mapa de comandos da documentação. |
| LiDAR | Bloqueia frente, ré e laterais a 0,35 m; para em caso de leitura ausente. |
| Autonomia | Lida com múltiplos obstáculos sem aproximar-se perigosamente e sem perda de controle manual. |
| Comunicação | Perda do F710, Wi-Fi ou Tailscale resulta em parada previsível. |
| Webcam/microfone | Webcam UVC e microfone integrado aparecem no Linux; voz é entendida em ambiente real. |
| Áudio | Fala permanece compreensível sem gerar comandos falsos por eco. |
| Localização | Posição repetível no mapa, incluindo após reinicialização. |
| Missões | Vai ao destino, anuncia chegada, espera 15 s e retorna à base sem colisão. |

## Limitações conhecidas

- Não há encoders nem odometria física dos motores; a localização para Nav2 ainda
  precisa ser demonstrada no ambiente real.
- A autonomia reativa não substitui planejamento de rota e não detecta todos os
  riscos físicos, como escadas, desníveis, objetos muito baixos ou transparentes.
- O reconhecimento de voz usa modelo local e pode falhar com ruído, eco, sotaque
  ou nomes de ambientes semelhantes.
- O código de voz, missão e serviços foi preparado, mas não deve ser marcado como
  validado até passar pelos testes com a webcam, microfone, alto-falante e Nav2.
- A instalação elétrica do botão de emergência ainda é pendente.

## Como registrar bugs e resultados

Para cada teste, registre no GitHub: versão/commit, data, ambiente, bateria,
resultado esperado, resultado observado, log ROS e correção aplicada. Não altere
o estado de uma função para “validada” apenas porque iniciou sem erro.

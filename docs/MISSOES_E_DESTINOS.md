# Missões, destinos e interação por voz

## Fluxo implementado

1. Um reconhecedor de voz, uma interface ou um teste manual publica texto em `/onigiri/voice_command`.
2. `onigiri_mission_manager.py` identifica o destino cadastrado no arquivo JSON.
3. O robô publica “Me siga, por favor” em `/onigiri/speech` e envia o objetivo ao Nav2.
4. Ao chegar, publica o nome do destino e aguarda 15 segundos.
5. Sem nova interação, anuncia “Até mais” e retorna à `base`.
6. Qualquer movimento do Logitech F710 envia `MISSION_CANCEL`, cancelando a missão e preservando prioridade manual.

## Arquivos

| Caminho | Uso |
|---|---|
| `config/destinations.example.json` | Exemplo de casa/base e destinos nomeados |
| `software/raspberry/onigiri_mission_manager.py` | Orquestra pedidos, Nav2, espera e retorno |
| `software/raspberry/onigiri_speech.py` | Converte mensagens ROS em fala local usando `espeak-ng` |

## Preparação futura

1. Copie `config/destinations.example.json` para `config/destinations.json`.
2. Substitua as coordenadas de exemplo por poses medidas no mapa final.
3. Instale a pilha de navegação Nav2 e forneça a transformação de localização no mapa.
4. Instale `espeak-ng` no Raspberry para saída de áudio.
5. Use uma webcam UVC com **microfone integrado**. O microfone da webcam será a entrada de voz do Onigiri.
6. O reconhecedor de voz deverá publicar o texto reconhecido em `/onigiri/voice_command`.

## Teste sem microfone

Após a navegação estar disponível, uma interface pode enviar um pedido de exemplo:

```bash
ros2 topic pub --once /onigiri/mission/request std_msgs/msg/String "{data: 'Onigiri, me leve ao escritorio'}"
```

## Limites

Esta camada não substitui a localização no mapa, a configuração de Nav2 ou o reconhecimento de voz. Ela fornece o fluxo de missão e as interfaces que conectam esses componentes. A webcam escolhida precisa ser compatível com Linux/UVC e disponibilizar seu microfone integrado como dispositivo de áudio USB.

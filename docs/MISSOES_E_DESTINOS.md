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
| `software/admin_web/` | Painel local para cadastrar destinos, frases e comportamento de chegada |
| `software/raspberry/onigiri_mission_manager.py` | Orquestra pedidos, Nav2, espera e retorno |
| `software/raspberry/onigiri_speech.py` | Converte mensagens ROS em fala local usando `espeak-ng` |
| `software/raspberry/onigiri_voice_recognizer.py` | Reconhece voz offline com o microfone da webcam e publica o texto no ROS 2 |

## Preparação futura

1. Copie `config/destinations.example.json` para `config/destinations.json`.
2. Substitua as coordenadas de exemplo por poses medidas no mapa final.
3. Instale a pilha de navegação Nav2 e forneça a transformação de localização no mapa.
4. Instale `espeak-ng` no Raspberry para saída de áudio.
5. Use uma webcam UVC com **microfone integrado**. O microfone da webcam será a entrada de voz do Onigiri.
6. O reconhecedor de voz deverá publicar o texto reconhecido em `/onigiri/voice_command`.

## Painel local de cadastro de destinos

O painel em `software/admin_web/` permite cadastrar, no computador, as frases
que devem ser associadas a cada destino. Por exemplo, as frases “me leve ao
escritório”, “onde fica o escritório” e “quero ir ao escritório” podem apontar
para o mesmo local no mapa.

Ele também permite definir a fala ao chegar, o tempo de espera e se o robô deve
retornar à base. A exportação gera `config/destinations.runtime.json`, compatível
com este nó de missões. A versão atual é exclusivamente local e simulada: ela
não publica comandos ROS, não aciona Nav2 e não movimenta o robô.

Antes da exportação final, a revisão do painel indica frases repetidas entre
destinos, locais sem comandos cadastrados e coordenadas que ainda precisam ser
medidas no mapa. O botão de backup preserva o cadastro editável para que ele
possa ser levado ao Raspberry Pi posteriormente.

Quando a integração no Raspberry Pi for instalada, o serviço de missões usará
`config/destinations.runtime.json`. Ao exportar mudanças no painel, esse arquivo
é substituído de forma atômica e o gerenciador o recarrega apenas no estado
ocioso. Assim, uma missão já iniciada mantém a configuração com que começou.

As instruções para testar o painel no Windows estão em
[`software/admin_web/README.md`](../software/admin_web/README.md).

## Reconhecimento de voz offline preparado

O repositório inclui uma implementação preparada para usar o modelo local
**Vosk** em português. Ela capta áudio do microfone integrado à webcam e publica
somente frases finalizadas em `/onigiri/voice_command`; não depende de nuvem.

No Raspberry Pi, depois de clonar este repositório em `/home/onigiri/onigiri`:

```bash
sudo apt install python3-pip portaudio19-dev
python3 -m pip install --user -r software/raspberry/requirements-voice.txt
mkdir -p models
# Baixe e descompacte o modelo pequeno em português do Vosk dentro de models/.
# O diretório esperado é models/vosk-model-small-pt-0.3/.
python3 software/raspberry/onigiri_voice_recognizer.py
```

Para identificar o microfone que a webcam expôs ao Linux, liste os dispositivos:

```bash
python3 -c "import sounddevice as sd; print(sd.query_devices())"
```

Se a webcam não for o dispositivo padrão, inicie com o parâmetro ROS
`audio_device`, usando o nome ou índice retornado pela lista. Exemplo:

```bash
python3 software/raspberry/onigiri_voice_recognizer.py --ros-args -p audio_device:='USB Camera'
```

Após confirmar o dispositivo e as dependências, o serviço
`deploy/systemd/onigiri-voice.service` pode ser instalado e habilitado. Não o
habilite antes de existir o modelo Vosk e de o microfone da webcam estar
disponível, pois o serviço reiniciará aguardando essa configuração.

## Teste sem microfone

Após a navegação estar disponível, uma interface pode enviar um pedido de exemplo:

```bash
ros2 topic pub --once /onigiri/mission/request std_msgs/msg/String "{data: 'Onigiri, me leve ao escritorio'}"
```

## Limites

Esta camada não substitui a localização no mapa ou a configuração de Nav2. O
reconhecimento de voz offline já está preparado no código, mas ainda depende da
instalação do modelo Vosk e da validação física do microfone. A webcam escolhida
precisa ser compatível com Linux/UVC e disponibilizar seu microfone integrado
como dispositivo de áudio USB.

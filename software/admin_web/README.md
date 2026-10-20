# Painel web de destinos do Onigiri

O painel também contém uma biblioteca de mapas e controles opcionais de captura
SLAM. Consulte [Mapeamento e imagem SD](../../docs/IMAGEM_SD_E_MAPEAMENTO.md) para
configuração no Raspberry Pi 4 e limites atuais. A captura real fica desabilitada
até que o ambiente ROS e o YAML SLAM da unidade sejam validados.

Este painel permite cadastrar locais, sinônimos e frases de voz antes de
conectá-los ao ROS 2. A primeira versão opera somente em **simulação**: ela não
publica tópicos ROS, não chama o Nav2 e não movimenta motores.

## Recursos atuais

- Cadastro, edição e remoção de destinos.
- Definição do ponto de retorno como base.
- Sinônimos e frases completas para cada destino.
- Sugestões editáveis de frases para cada novo destino, como “me leve para...”
  e “onde fica...”.
- Teste de interpretação de texto com correspondência sem diferença entre
  maiúsculas, minúsculas ou acentos, respeitando palavras completas.
- Simulação da sequência de pedido, fala, navegação, chegada, espera e retorno.
- Exportação automática em JSON compatível com o atual nó
  `software/raspberry/onigiri_mission_manager.py`.
- Revisão automática de frases ambíguas, destinos sem frases e posições ainda
  não medidas no mapa.
- Backup e restauração do cadastro local em um arquivo JSON.
- Visualização local do mapa ROS 2 (`.yaml` + `.pgm`) com escolha assistida da
  posição: somente células brancas, já identificadas como área livre, podem ser
  usadas para iniciar o cadastro de um destino.

## Escolhendo destinos no mapa

Após criar o mapa no Raspberry Pi com o SLAM, copie **os dois arquivos do mesmo
mapa** para o computador: por exemplo, `onigiri_map.yaml` e
`onigiri_map.pgm`. No painel, selecione os dois arquivos na área **Mapa e
posicionamento de destinos**.

- Branco representa uma área livre e pode receber um destino.
- Preto representa obstáculo e não pode receber um destino.
- Cinza representa área desconhecida e também não pode receber um destino.

Clique em uma região branca e use **Novo destino neste ponto**. O painel
preenche `X` e `Y` de acordo com a resolução e a origem registradas no mapa; o
ângulo `yaw` ainda deve ser definido conforme a orientação desejada na chegada.
Os arquivos do mapa são lidos somente pelo navegador para auxiliar o cadastro:
não são enviados, alterados ou armazenados pelo painel.

## Teste no computador Windows

No **PowerShell**, dentro da pasta do repositório, execute:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r software/admin_web/requirements.txt
$env:PYTHONPATH = "software/admin_web"
.\.venv\Scripts\python.exe -m unittest discover -s software/admin_web/tests
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir software/admin_web --host 127.0.0.1 --port 8080
```

No **Git Bash**, a única diferença é a linha de teste:

```bash
PYTHONPATH=software/admin_web .venv/Scripts/python.exe -m unittest discover -s software/admin_web/tests
```

Abra `http://127.0.0.1:8080` no navegador.

O primeiro uso cria dois arquivos locais, que não devem ir para o GitHub:

- `data/onigiri_admin.db`: banco editável do painel.
- `config/destinations.runtime.json`: arquivo exportado para a futura execução ROS 2.

## Integração planejada com o Raspberry Pi

Depois da validação no computador, o painel será instalado no Raspberry Pi. O
mesmo arquivo exportado poderá ser entregue ao nó de missões por meio do
parâmetro `destinations_file`. O arquivo também carrega a fala de chegada, o
tempo de espera e a opção de retornar à base cadastrados para cada destino.

A ligação com voz, áudio e Nav2 só será ativada após testes físicos controlados.
Enquanto isso, este painel permanece local, em `127.0.0.1`, e em simulação.

### Pacote preparado para o Raspberry Pi

O repositório já contém, mas **não executa automaticamente**, o instalador
`deploy/scripts/install_admin_web.sh` e o serviço
`deploy/systemd/onigiri-admin-web.service`. Eles serão usados somente na etapa
final de instalação no Raspberry. O serviço fica limitado a `127.0.0.1`; não
abre uma porta pública na rede.

O instalador também atualiza o arquivo do serviço de missões, mas não o reinicia
sozinho. A troca para a configuração exportada ocorre apenas em uma reinicialização
controlada desse serviço, evitando alteração de uma missão que já esteja ativa.

Depois da instalação futura no **Raspberry Pi**, o acesso pelo **computador
Windows** será feito por túnel SSH:

```powershell
ssh -L 8080:127.0.0.1:8080 onigiri@ENDERECO_DO_RASPBERRY
```

Então, no navegador do Windows, abra `http://127.0.0.1:8080`. A configuração
exportada será recarregada pelo gerenciador de missões apenas quando ele estiver
sem uma missão ativa; uma missão em andamento nunca muda de destino no meio do
percurso.


## Controles USB/Bluetooth no WSL2

No terminal Ubuntu/WSL2:

```bash
cd ~/robotica_ws/src/onigiri
git branch --show-current  # feature/controles-universais
python3 -m venv .venv  # somente se ainda não existir
.venv/bin/python -m pip install -r software/admin_web/requirements.txt
PYTHONPATH=software/admin_web .venv/bin/python -m unittest discover -s software/admin_web/tests
.venv/bin/python -m uvicorn app.main:app --app-dir software/admin_web --host 0.0.0.0 --port 8080
```

Abra http://localhost:8080 no Edge/Chrome do Windows e conecte o controle ao
Windows (não é necessário encaminhar USB ao WSL). Clique em **Iniciar teste**
e pressione um botão. A API depende de localhost/HTTPS e de permissão do navegador.
O bind 0.0.0.0 facilita o acesso Windows→WSL; use 127.0.0.1 quando o encaminhamento
localhost funcionar. Não use o IP HTTP da máquina para a Gamepad API.

- Escolha o controle conectado; eixos mostram valores brutos e tratados, botões
  mostram intensidade e destaque quando pressionados.
- Crie um perfil, ajuste deadzone e calibre mantendo os analógicos soltos por
  1,5 segundo. A calibração mede o centro, não o curso máximo dos eixos.
- Capture uma ação, solte os controles e então mova um eixo/pressione um botão.
  A captura expira em 10 segundos; Escape cancela. Entradas duplicadas são recusadas.
- Clique em **Salvar perfil** após editar. Trocar de perfil descarta edições não
  salvas. Perfis, seleção, calibração e mapeamentos ficam em localStorage,
  por navegador/origem; não são compartilhados com outros computadores.
- Parar, desconectar ou ocultar a aba limpa as leituras e cancela capturas.
  Ao retornar à aba, inicie o teste novamente.

Este módulo apenas visualiza entradas e a prévia das ações. Não envia comandos
HTTP/WebSocket/ROS, não aciona motores nem vibração. O app.js existente foi preservado.

Teste automatizado adicional (Node + Playwright com Chromium instalado):

```bash
node software/admin_web/tests/gamepad.browser.cjs
# Para usar o Edge instalado: GAMEPAD_BROWSER_CHANNEL=msedge node software/admin_web/tests/gamepad.browser.cjs
```

O teste simula um controle; a validação física USB/Bluetooth continua sendo manual.

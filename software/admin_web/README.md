# Painel web de destinos do Onigiri

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

Depois da instalação futura no **Raspberry Pi**, o acesso pelo **computador
Windows** será feito por túnel SSH:

```powershell
ssh -L 8080:127.0.0.1:8080 onigiri@ENDERECO_DO_RASPBERRY
```

Então, no navegador do Windows, abra `http://127.0.0.1:8080`. A configuração
exportada será recarregada pelo gerenciador de missões apenas quando ele estiver
sem uma missão ativa; uma missão em andamento nunca muda de destino no meio do
percurso.

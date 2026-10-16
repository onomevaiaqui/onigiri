# Painel web de destinos do Onigiri

Este painel permite cadastrar locais, sinônimos e frases de voz antes de
conectá-los ao ROS 2. A primeira versão opera somente em **simulação**: ela não
publica tópicos ROS, não chama o Nav2 e não movimenta motores.

## Recursos atuais

- Cadastro, edição e remoção de destinos.
- Definição do ponto de retorno como base.
- Sinônimos e frases completas para cada destino.
- Teste de interpretação de texto com correspondência sem diferença entre
  maiúsculas, minúsculas ou acentos.
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

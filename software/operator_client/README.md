# Cliente do operador

Esta pasta reúne os scripts que leem o controle Logitech F710 e enviam os
comandos manuais ao Onigiri pela rede Tailscale. Ela pode ser usada em
**Windows, macOS ou Linux**: o nome não indica um sistema operacional.

## Preparação

1. Clone este repositório no computador que será usado para operar o robô.
2. Conecte o receptor USB do Logitech F710.
3. Instale as dependências.

No Windows, abra o PowerShell na raiz do repositório:

```powershell
py -m pip install -r .\software\operator_client\requirements.txt
```

No macOS ou Linux, abra um terminal na raiz do repositório:

```bash
python3 -m pip install -r software/operator_client/requirements.txt
```

## Operação

Substitua o endereço pelo IP Tailscale do Raspberry Pi.

Windows:

```powershell
py .\software\operator_client\f710_bridge.py <IP_TAILSCALE_DO_RASPBERRY>
```

macOS ou Linux:

```bash
python3 software/operator_client/f710_bridge.py <IP_TAILSCALE_DO_RASPBERRY>
```

O analógico esquerdo controla frente/ré e giro; o direito controla o
deslocamento lateral. O botão 7 ativa ou desativa a autonomia. Ao encerrar a
ponte com `Ctrl+C`, ela envia uma parada e desativa a autonomia.

## Diagnóstico do controle

Use os scripts abaixo no mesmo sistema operacional em que o F710 será usado:

```bash
python3 software/operator_client/f710_axes.py
python3 software/operator_client/f710_buttons.py
```

No Windows, substitua `python3` por `py` caso seja necessário.

Antes de qualquer movimento real, mantenha o robô em uma área livre e siga as
orientações de segurança do [manual de construção](../../docs/MANUAL_DE_CONSTRUCAO.md).

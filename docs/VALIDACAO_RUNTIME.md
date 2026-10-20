# Validação de software — 20/10/2026

Ambiente: WSL2 Ubuntu 24.04 x86_64, ROS 2 Jazzy; navegador Edge por Playwright. Hardware físico não conectado.

- 51 testes Python: persistência, destinos, mapas, PNG RGB/profundidade, mistura dos chassis, limite de potência, parada latched, watchdog, serial POSIX com pseudo-terminal, parâmetros Nav2, cloud-init e backup/restauração SQLite.
- Navegador: perfis de controle, remapeamento/calibração, mapas e prévia, zoom/arraste, edição/exclusão de pontos, tipos base/destino, seleção de plataforma/serial persistente, quatro canais mecanum, recusa de movimento desabilitado e layout móvel.
- Integração ROS isolada (domínio 177): scan e odometria sintéticos → base → serial virtual, expiração de comandos, expiração de odometria apesar de cmd_vel contínuo, ação NavigateToPose contra servidor sintético, chegada, emergência e liberação sem rearme.
- Nav2 real isolado (domínio 178): AMCL e servidores de navegação ativados, RF2O compilado com patch de inicialização TF, mapa de sala e scans sintéticos, TF map → base_footprint disponível. Nenhum motor iniciado e nenhuma navegação física testada.
- Imagem Ubuntu 24.04.5 arm64 Raspberry Pi: SHA256 da origem conferido; imagem .img gerada; partição FAT montada e inspecionada; user-data aprovado por cloud-init schema; pacote embarcado verificado sem banco/mapas/destinos pessoais nem chave SSH privada.
- Pacote de atualização: checksums, sintaxe dos scripts, inicialização do FastAPI em pasta nova, sem clone Git.

Um scan sintético perfeitamente constante e simétrico revelou degeneração no estimador RF2O. O teste de ativação Nav2 usa scans com deslocamento sintético; a base implementa bloqueio por odometria não finita ou sem atualização. Não há promessa de estimativa válida em toda geometria de ambiente.

Ainda exigem validação física: boot e provisionamento completos em Raspberry 4/5, compilação/USB/firmware Gemini 2 no ARM64, baud/address/DEScribe das Sabertooth, sentidos e corrente dos motores, parada física, limite de potência real, geometria/extrínsecas, odometria em diferentes superfícies e navegação com obstáculos. Não foram habilitados motores no Raspberry do usuário.

Reexecutar testes Python:

```bash
PYTHONPATH=software/admin_web .venv/bin/python -m unittest discover -s software/admin_web/tests
```

Os scripts `runtime_ros_integration.py` e `nav2_ros_integration.py` são opcionais e exigem ROS instalado. Execute-os com ROS_DOMAIN_ID exclusivo, após source do ROS; o segundo exige também source do overlay RF2O. O teste serial usa /dev/pts, não dispositivos físicos. Os testes de navegador reais exigem um servidor FastAPI com banco/plataforma/mapas temporários e Playwright instalado.

## RGB-D sem LiDAR

56 testes unitários aprovados. `rgbd_ros_integration.py` usa ROS 2/RTAB-Map reais com RGB-D sintético: odometria, mapa, prévia, gravação atômica YAML/PGM/banco visual e reabertura com localização e Nav2 ativos. Confere que o banco salvo permanece intacto. Não equivale a teste físico da Gemini 2 ou dos motores.

## Primeiro acesso e rede

62 testes unitários aprovados, incluindo recuperação do ponto de acesso, validação de SSID/senha, keyfile privado e autenticação. Teste de navegador cobre cadastro Wi-Fi, remoção da senha do formulário e ordem frame → driver → Raspberry → sensores. Alterações Wi-Fi do teste são simuladas; boot, DHCP e rádio ainda precisam de teste físico.

`panel_auth_integration.py` verifica recusa de acesso anônimo e acesso autenticado às páginas, recursos e APIs em servidor real temporário. O cliente/agente de rede também é testado via socket Unix real, sem alterar interfaces.

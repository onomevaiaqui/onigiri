# Onigiri: painel dedicado ao robô original

O software genérico foi copiado para o repositório privado [Omni Framework](https://github.com/onomevaiaqui/omni-framework). A importação preserva o estado completo no commit `5300df2`, antes da separação.

## Mantido neste projeto

- CAD, documentação mecânica, eletrônica e montagem do Onigiri.
- Driver original do HAT, três motores omniball e cliente de controle existente.
- Painel web com a mesma aparência para acesso, configuração, identidade do robô, Wi-Fi, perfis locais de controle, mapas e destinos do Onigiri.
- Captura e prévia LiDAR do robô original, sem comando de tração pelo painel.
- Construção de imagem SD para Raspberry Pi 4, primeiro acesso por Wi-Fi e instalação automática. O arquivo é `.img`, próprio para cartão SD.
- Backup e diagnóstico. O serviço original dos motores não é iniciado pela instalação do painel.

## Separado

Drivers alternativos, seleção de frames, sensores RGB-D, runtime de motores genérico e navegação pelo novo runtime evoluem apenas no Omni Framework. O painel dedicado não oferece essas rotas HTTP nem opções de hardware. Os arquivos antigos continuam no histórico Git; não foram reescritos commits publicados.

44 testes unitários do painel dedicado e teste de navegador aprovados nesta separação. A imagem continua exigindo teste físico de boot no Raspberry; não houve instalação nem movimentação do robô durante a separação.

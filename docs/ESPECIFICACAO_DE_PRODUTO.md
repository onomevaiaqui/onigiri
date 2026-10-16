# Especificação de produto — Onigiri

## Propósito

O Onigiri é um robô móvel de apoio à acessibilidade e à orientação em ambientes internos. Pode atender empresas de médio e grande porte, escolas, supermercados e projetos acadêmicos.

Ele deve ajudar uma pessoa a encontrar um local sem depender apenas de placas,
mapas impressos ou instruções verbais. A plataforma compartilha seus arquivos
originais para que outras pessoas possam estudar, reproduzir e adaptar a
solução, sem caracterizar como aberto o hardware comercial utilizado.

## Experiência desejada

Antes de operar o robô, a equipe responsável deve:

1. Mapear o local.
2. Nomear os destinos no mapa, por exemplo `escritório` e `refeitório`.
3. Definir o ponto inicial do Onigiri, chamado de `casa`.

Uma interação típica será:

1. A pessoa se aproxima e diz: “Onigiri, me leve ao escritório” ou “Onde é o escritório?”.
2. O Onigiri identifica o destino e responde: “Me siga, por favor.”
3. O robô conduz a pessoa até o destino, respeitando as camadas de segurança.
4. Ao chegar, anuncia o nome do local, por exemplo: “Escritório.”
5. Aguarda 15 segundos.
6. Se não houver uma nova solicitação, despede-se: “Até mais.”
7. Retorna ao ponto `casa`.

## Regras de segurança

- A autonomia nunca substitui supervisão humana durante os testes.
- Um risco próximo, uma leitura LiDAR ausente ou um timeout de comando devem interromper o movimento.
- O controle manual tem prioridade sobre a autonomia.
- O retorno para `casa` deve obedecer às mesmas regras de segurança do deslocamento ao destino.
- O corte físico da alimentação dos motores é obrigatório antes da validação de percursos autônomos.

## Estado de desenvolvimento

O protótipo atual já controla os três motores, recebe o Logitech F710 pela rede, lê o RPLIDAR A1M8 e executa uma autonomia reativa de parada e desvio.

Em 8 de outubro de 2026, o projeto gerou e salvou o primeiro mapa experimental com `slam_toolbox`. O arquivo serve para validar a integração inicial entre LiDAR, TF e SLAM. Ainda não deve ser usado para navegação até destinos, pois a plataforma não tem encoders nem odometria física.

O repositório contém interfaces para voz offline, fala, destinos nomeados,
Nav2, espera de 15 segundos e retorno à base. A integração completa depende da
configuração do mapa, da localização e dos periféricos, seguida de validação
física. Veja o [estado, testes e limitações](ESTADO_TESTES_E_LIMITACOES.md).

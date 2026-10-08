# Especificação de produto — Onigiri

## Propósito

O Onigiri é um robô móvel de apoio à acessibilidade e à orientação em ambientes internos. Pode atender empresas de médio e grande porte, escolas, supermercados e projetos acadêmicos.

Ele deve ajudar uma pessoa a encontrar um local sem depender apenas de placas, mapas impressos ou instruções verbais. O projeto será aberto para que outras pessoas possam estudar, reproduzir e adaptar a solução.

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
- O corte físico da alimentação dos motores continua sendo uma próxima integração necessária.

## Estado atual e próximos marcos

O protótipo atual já controla os três motores, recebe o Logitech F710 pela rede, lê o RPLIDAR A1M8 e executa uma autonomia reativa de parada e desvio.

Para alcançar a experiência desejada, os próximos marcos são:

1. Criar e salvar um mapa do ambiente.
2. Estimar a posição do robô no mapa.
3. Cadastrar `casa` e destinos nomeados.
4. Navegar de forma segura até um destino e retornar.
5. Integrar voz, síntese de fala e a espera de 15 segundos.

> A autonomia atual não realiza SLAM, localização, rota por mapa, reconhecimento de voz nem retorno automático. Esses itens são metas de desenvolvimento.

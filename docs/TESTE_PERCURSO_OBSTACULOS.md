# Teste de percurso com múltiplos obstáculos

Este procedimento valida a primeira etapa de campo do Onigiri. Execute-o somente em uma área plana, livre de pessoas e com um operador pronto para desligar a LiPo.

## Preparação

1. Verifique a fixação da bateria, do LiDAR e de todos os cabos.
2. Ligue o robô e confirme que `onigiri-udp.service`, `onigiri-lidar.service` e `onigiri-autonomous.service` estão ativos.
3. Deixe o controle Logitech F710 disponível. O controle manual tem prioridade e deve ser usado para interromper qualquer comportamento inesperado.
4. Separe caixas ou obstáculos planos que possam ser detectados pelo LiDAR.

## Validação das zonas de segurança

Faça os testes com o robô suspenso primeiro. Em seguida, repita-o no chão e em baixa velocidade.

| Movimento solicitado | Posição do obstáculo | Resultado esperado |
|---|---|---|
| Frente | 25 cm à frente do LiDAR | Avanço bloqueado |
| Ré | 25 cm atrás do LiDAR | Ré bloqueada |
| Lateral direita | 25 cm à direita do LiDAR | Deslocamento à direita bloqueado |
| Lateral esquerda | 25 cm à esquerda do LiDAR | Deslocamento à esquerda bloqueado |
| Giro | Obstáculo próximo em qualquer lado | Giro continua disponível para liberar o robô |

Afaste o obstáculo para pelo menos 50 cm e confirme que o movimento correspondente volta a funcionar.

## Percurso inicial

1. Monte um corredor simples com dois obstáculos, deixando espaço lateral para uma manobra.
2. Ative a autonomia pelo botão 7 do F710.
3. Observe se o robô para ou inicia o desvio antes de atingir o primeiro obstáculo.
4. Desative a autonomia, reposicione o robô e repita o teste pelo menos três vezes.
5. Registre qualquer parada tardia, contato, perda de leitura ou comportamento inconsistente em uma issue ou no próximo registro de versão.

## Critério para avançar

Só avance para navegação por mapa depois de o robô completar o percurso sem contato, manter as quatro zonas de bloqueio ativas e responder imediatamente ao controle manual.

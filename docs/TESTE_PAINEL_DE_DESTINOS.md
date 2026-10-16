# Teste local do painel de destinos

Este roteiro é executado no **computador Windows**, antes de qualquer instalação
no Raspberry Pi. O painel local não se conecta ao ROS 2, ao Nav2 ou aos motores.

## Objetivo

Confirmar que cada frase cadastrada aponta para o destino certo e que frases
desconhecidas não geram uma missão simulada.

## Roteiro

1. Inicie o painel seguindo `software/admin_web/README.md`.
2. Carregue o par `.yaml` e `.pgm` do mapa ROS 2. Clique apenas nas regiões
   brancas do mapa para iniciar o cadastro da `base` e dos destinos. O painel
   bloqueará células de obstáculo (pretas) e área desconhecida (cinzas).
3. Para cada destino, inclua nomes alternativos e frases completas. Exemplo para
   `escritorio`:
   - `escritório`
   - `me leve ao escritório`
   - `onde fica o escritório`
4. Use **Teste em lote** e informe uma frase por linha.
5. Confirme que cada resultado verde aponta para o local pretendido.
6. Inclua uma frase que não pertence a destino algum e confirme que ela aparece
   como “não reconhecida”.
7. Verifique a seção **Revisão do cadastro**. Não avance se houver frase
   ambígua, destino sem comando ou coordenada pendente depois do mapeamento.
8. Use **Simular missão sem mover o robô** e confira a sequência: pedido,
   resposta, navegação simulada, chegada, espera e retorno.
9. Baixe um backup ao final do cadastro.

## Critérios para avançar ao Raspberry Pi

- Uma única base definida.
- Cada destino tem pelo menos uma frase ou sinônimo útil.
- Nenhuma frase é compartilhada por dois destinos.
- Coordenadas selecionadas em área livre do mapa ROS 2 e revisadas no cadastro.
- Backup salvo fora do Raspberry Pi.

## Limite desta etapa

Esta validação confirma apenas o cadastro e a interpretação de texto. Ela não
valida reconhecimento de voz, áudio, localização, Nav2, sensores ou movimento.

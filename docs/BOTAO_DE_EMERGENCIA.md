# Botão de parada de emergência

## Objetivo

O botão de emergência deve interromper fisicamente a energia dos motores, mesmo que o Raspberry Pi, a rede, o ROS 2 ou o software apresentem falha. Ele é uma camada de segurança independente do LiDAR e das proteções de software.

## Componente a adquirir

Use um botão tipo cogumelo de **22 mm**, com **trava mecânica** e liberação por giro ou puxada. O contato utilizado deve ser:

- **NC — normalmente fechado**: conduz com o botão solto e abre o circuito quando pressionado.
- Especificado para **corrente contínua em 12 V** e para a corrente de partida dos três motores.
- Preferencialmente com dois contatos NC, se a versão escolhida permitir redundância futura.

O anúncio consultado apresenta variações de botão com LED. A presença do LED não substitui o contato NC e não deve determinar a escolha. Antes da montagem, confirme no anúncio ou no corpo do componente a identificação dos terminais e a corrente nominal em DC.

> Se a corrente nominal do contato não suportar a corrente de partida dos motores, o botão deve comandar um relé ou contator adequado para corrente contínua. Não use um botão de sinal fraco diretamente no circuito dos motores.

## Ligação elétrica

O botão interrompe **somente a alimentação do HAT e dos motores**. O Raspberry Pi continua energizado pelo Tobsun para manter os registros, a comunicação e o LiDAR disponíveis após uma parada.

```text
LiPo 3S positivo
    |
    +--> fusível adequado --> contato NC do botão de emergência --> + do Motor HAT
    |
    +--> Tobsun EA75-5V --> USB-C --> Raspberry Pi 4

LiPo 3S negativo -----------------------------------------------> GND do Motor HAT
LiPo 3S negativo -----------------------------------------------> - do Tobsun
```

Ao pressionar o botão, o contato NC abre, o HAT deixa de alimentar M1, M2 e M3, e o robô para por corte físico de tração. O Raspberry Pi não deve receber alimentação através do HAT.

## Não fazer

- Não ligar o botão somente a um GPIO do Raspberry Pi.
- Não usar o contato NO como único circuito de parada.
- Não interromper a alimentação USB-C do Raspberry como única ação de emergência.
- Não alimentar o LED sem identificar os terminais e a tensão correta da versão comprada.
- Não testar com o robô apoiado no chão antes de confirmar a continuidade com multímetro.

## Validação antes do uso

1. Com a LiPo desligada, identifique o contato NC com o multímetro: ele deve ter continuidade com o botão solto e circuito aberto quando pressionado.
2. Confirme a polaridade da LiPo e a posição do fusível.
3. Suspenda as rodas.
4. Ligue o robô e acione um motor em baixa velocidade.
5. Pressione o botão: todos os motores devem parar imediatamente.
6. Confirme que o Raspberry continua ligado e que o LiDAR permanece operacional.
7. Solte/destrave o botão, desligue e religue a LiPo antes de retomar os testes.

## Estado

Integração elétrica planejada. A instalação e a validação física dependem da confirmação do modelo exato do botão, da corrente nominal em DC e da chegada do componente.

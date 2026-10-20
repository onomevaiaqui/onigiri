# Primeiro acesso ao Onigiri

## Imagem SD e conexão direta

1. Grave a imagem preparada em um cartão de pelo menos 32 GB. Guarde o arquivo **ONIGIRI-ACESSO.txt**, entregue ao lado da imagem e também na partição de boot. Ele contém credenciais próprias dessa imagem; não publique esse arquivo nem uma imagem personalizada para outras pessoas.
2. Ligue o Raspberry Pi 4 ou 5. No computador ou celular, conecte à rede **Onigiri-Config-XXXXXX** indicada no cartão de acesso, usando a senha indicada. Essa rede pode aparecer como “sem Internet”; mantenha a conexão.
3. Abra **http://192.168.50.1:8080** no navegador. Usuário: **onigiri**. Use a senha do painel indicada no cartão de acesso.
4. Informe o SSID e a senha do Wi-Fi comum. São suportadas redes pessoais WPA/WPA2; redes corporativas com usuário/certificado e portais de login ainda não estão implementadas.
5. Durante a troca a conexão direta encerra. Conecte seu computador à rede Wi-Fi escolhida e abra **http://onigiri.local:8080**. Se o nome não resolver, consulte o IP do Raspberry na lista de dispositivos do roteador e abra **http://IP:8080**. O cartão de acesso continua sendo usado para entrar no painel.
6. Na primeira inicialização, o sistema baixa e instala ROS e os componentes de sensores pela Internet. O portal de primeiro acesso funciona antes dessa instalação; aguarde até o painel completo estar disponível. Não desligue durante essa etapa.

Ethernet com DHCP também pode fornecer acesso e Internet. Para Wi-Fi, o agente usa NetworkManager e mantém o ponto de acesso como alternativa. AP e Wi-Fi comum não são simultâneos na interface interna. Se a conexão escolhida falhar ou o Wi-Fi desconectar, a rede de configuração volta; após perda de rede, aguarde aproximadamente um minuto. Ao ligar novamente, redes conhecidas têm preferência; a rede de configuração é usada quando necessário. Uma rede de configuração ativa permanece disponível até uma nova tentativa pelo usuário.

## Configurar o robô no navegador

Em **Configurações**:

1. **Frame:** três motores com omniball, dois motores com esteiras ou quatro motores com mecanum.
2. **Driver:** HAT original para o Onigiri, Sabertooth 2x32 ou 2x60 para as plataformas compatíveis.
3. **Módulo de controle:** Raspberry Pi 4 ou 5.
4. **Sensores:** LiDAR e/ou Orbbec Gemini 2. Sem LiDAR e com Gemini 2, o sistema usa RGB-D. Outros sensores serão acrescentados ao catálogo posteriormente.
5. **Nome do robô:** opcional, apenas para organização.
6. Abra portas, dimensões e calibração, preencha medições reais e salve.

Depois use **Mapas e destinos** para mapear, salvar e cadastrar destinos e base. O fluxo é comum às plataformas. Instalação e configuração não habilitam motores. O gamepad atual é monitoramento local.

## Acesso pela rede e recuperação

O IP do robô na rede comum aparece em **Configurações → Conexão do robô**, quando essa conexão estiver ativa. O roteador pode reservar esse IP para manter o endereço constante. O acesso por IP funciona na mesma rede ou através de uma VPN já configurada; não configura acesso externo pela Internet automaticamente. Não encaminhe a porta do painel no roteador.

Se a senha do Wi-Fi estiver errada, reconecte à rede Onigiri-Config e corrija pelo navegador. A senha da conexão direta e do painel permanece no cartão de acesso. Para um Raspberry já instalado, use o atualizador com **-InstalarRede**; a mudança do gerenciamento Wi-Fi passa a valer completamente após reiniciar. A autenticação do painel será ativada; as credenciais podem ser consultadas localmente com `sudo cat /etc/onigiri/access.json`.

## Construção e validação

O construtor da imagem exige Linux/WSL com `qemu-user-static`, binfmt ARM64, loop/mount e Internet na máquina de construção. A opção `--credentials` exige um arquivo novo para o cartão de acesso. Os pacotes mínimos de rede são instalados na imagem durante a construção, antes do primeiro boot, e não dependem de Internet no Raspberry para abrir o portal inicial.

Testes de software verificam validação das credenciais, persistência privada, recuperação de conexão e fluxo do navegador. A emissão real do ponto de acesso, DHCP, troca de Wi-Fi e primeiro boot ainda exigem validação física em Raspberry Pi 4 e 5.

Referência técnica: [NetworkManager/nmcli](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nmcli.html).

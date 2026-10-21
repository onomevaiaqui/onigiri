# Primeiro acesso ao Onigiri

## Imagem SD e conexão direta

1. Grave a imagem preparada em um cartão de pelo menos 32 GB. Guarde o arquivo **ONIGIRI-ACESSO.txt**, entregue ao lado da imagem e também na partição de boot. Ele contém credenciais próprias dessa imagem; não publique esse arquivo nem uma imagem personalizada para outras pessoas.
2. Ligue o Raspberry Pi 4 ou 5. No computador ou celular, conecte à rede **Onigiri-Config-XXXXXX** indicada no cartão de acesso, usando a senha indicada. Essa rede pode aparecer como “sem Internet”; mantenha a conexão.
3. Abra **http://192.168.50.1:8080** no navegador. Usuário: **onigiri**. Use a senha do painel indicada no cartão de acesso.
4. Informe o SSID e a senha do Wi-Fi comum. São suportadas redes pessoais WPA/WPA2; redes corporativas com usuário/certificado e portais de login ainda não estão implementadas.
5. Durante a troca a conexão direta encerra. Conecte seu computador à rede Wi-Fi escolhida e abra **http://onigiri.local:8080**. Se o nome não resolver, consulte o IP do Raspberry na lista de dispositivos do roteador e abra **http://IP:8080**. O cartão de acesso continua sendo usado para entrar no painel.
6. Na primeira inicialização, o sistema baixa e instala ROS e os componentes de sensores pela Internet. O portal de primeiro acesso funciona antes dessa instalação; aguarde até o painel completo estar disponível. Não desligue durante essa etapa.

Ethernet com DHCP também pode fornecer acesso e Internet. Para Wi-Fi, o agente usa NetworkManager e mantém o ponto de acesso como alternativa. AP e Wi-Fi comum não são simultâneos na interface interna. Se a conexão escolhida falhar ou o Wi-Fi desconectar, a rede de configuração volta; após perda de rede, aguarde aproximadamente um minuto. Ao ligar novamente, redes conhecidas têm preferência; a rede de configuração é usada quando necessário. Uma rede de configuração ativa permanece disponível até uma nova tentativa pelo usuário.

## Configurar o Onigiri no navegador

Em **Configurações**, registre o Raspberry Pi 4 ou 5, o frame omniball ou
mecanum, o driver dos motores, o LiDAR 2D, a webcam UVC com microfone e a saída
de áudio. O nome do robô é opcional e serve apenas para organização.

O perfil não liga serviços nem aciona motores. O HAT original no frame omniball
é o único adaptador de movimento validado neste momento. RPLIDAR A1/A2/A3/S1
usa o driver já incluído na imagem; LDROBOT e YDLIDAR aparecem no catálogo para
configuração e exigem a instalação do respectivo driver antes do uso. O Onigiri
não usa Gemini 2, Orbbec nem mapeamento RGB-D.

Use **Mapas e destinos** para configurar o mapa e os pontos do Onigiri. O gamepad do painel continua sendo monitoramento e calibração local. O controle físico utiliza o software original em `software/raspberry` e o cliente em `software/operator_client`.

## Acesso pela rede e recuperação

O IP do robô na rede comum aparece em **Configurações → Conexão do robô**, quando essa conexão estiver ativa. O roteador pode reservar esse IP para manter o endereço constante. O acesso por IP funciona na mesma rede ou através de uma VPN já configurada; não configura acesso externo pela Internet automaticamente. Não encaminhe a porta do painel no roteador.

Se a senha do Wi-Fi estiver errada, reconecte à rede Onigiri-Config e corrija pelo navegador. A senha da conexão direta e do painel permanece no cartão de acesso. Para um Raspberry já instalado, use o atualizador com **-InstalarRede**; a mudança do gerenciamento Wi-Fi passa a valer completamente após reiniciar. A autenticação do painel será ativada; as credenciais podem ser consultadas localmente com `sudo cat /etc/onigiri/access.json`.

## Construção e validação

O construtor da imagem exige Linux/WSL com `qemu-user-static`, binfmt ARM64, loop/mount e Internet na máquina de construção. A opção `--credentials` exige um arquivo novo para o cartão de acesso. Os pacotes mínimos de rede são instalados na imagem durante a construção, antes do primeiro boot, e não dependem de Internet no Raspberry para abrir o portal inicial.

Testes de software verificam validação das credenciais, persistência privada, recuperação de conexão e fluxo do navegador. A emissão real do ponto de acesso, DHCP, troca de Wi-Fi e primeiro boot ainda exigem validação física no modelo de Raspberry escolhido.

Referência técnica: [NetworkManager/nmcli](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nmcli.html).

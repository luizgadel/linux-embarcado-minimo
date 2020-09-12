# Sistema Embarcado Linux de Transmissão de dados por MQTT

Este documento descreve os passos necessários para gerar uma imagem Linux pronta para ser embarcada contendo um script que coleta métricas de processamento e uso de memória e então as publica via MQTT.

O método utiliza o Projeto Yocto, um projeto _open-source_ com ferramentas para gerar imagens Linux para qualquer tipo de sistema embarcado.

## Preparação do ambiente

O Yocto requer um ambiente Linux para construir imagens. Optou-se por utilizar o Windows com WSL2 - que disponibiliza uma camada nativa de sistema Linux por meio de uma linha de comando - pois o Yocto garante suporte apenas a um pequeno conjunto de distribuições Linux, dentre elas, o Ubuntu 18.04 (LTS), que está disponível no WSL2.

### Pacotes necessários

Primeiramente, é necessário rodar o seguinte comando para instalar os pacotes necessários para utilizar o Yocto:

    $ sudo apt-get install gawk wget git-core diffstat unzip texinfo gcc-multilib \
    build-essential chrpath socat cpio python3 python3-pip python3-pexpect \
    xz-utils debianutils iputils-ping python3-git python3-jinja2 libegl1-mesa libsdl1.2-dev \
    pylint3 xterm

### Baixar o Poky

O Yocto usa o Poky, uma distribuição de referência, para construir novas imagens. Deve-se baixá-lo via Git com:

    $ git clone git://git.yoctoproject.org/poky

Em seguida, deve-se escolher uma versão do Poky para trabalhar, pois ela será utilizada para corresponder com as versões de outras dependências. Optou-se pela versão recente 3.1, nomeada _dunfell_. Para selecioná-la, basta usar

    $ git cd poky
    $ git checkout dunfell

## Configuração da imagem

Antes de mais nada, deve-se rodar o script `oe-init-build-env` dentro da pasta `poky` para criar o ambiente de construção de imagem

    $ source oe-init-build-env

Esse script também disponibiliza comandos úteis para a construção e emulação da imagem, como `bitbake` e `runqemu`.

Agora existe a pasta `build`, contendo configurações para criação da imagem e futuramente todo o conteúdo gerado durante o processo.

### Adicionar pacotes

O _bitbake_ é uma ferramenta que lê arquivos de receita localizados nas camadas de uma imagem a ser gerada, resolve as dependências e então realiza o ciclo de configuração, compilação e instalação de cada uma no sistema de arquivos final.

Inicialmente, ele já disponibiliza algumas receitas prontas para gerar imagens Linux com diferentes funcionalidades. Para este trabalho, optou-se pela imagem _core-image-full-cmdline_, que gera um sistema Linux com funcionalidade básica (SSH, rede, controle de usuário) porém sem interface ou aplicações de usuário, mais apropriado para um sistema embarcado mínimo.

Para adicionar pacotes à imagem, pode-se alterar o arquivo `build/conf/local.conf` ao adicionar a linha a seguir:

    IMAGE_INSTALL_append = " vim"

Essa linha adiciona o pacote do VIM à receita da imagem atual, que pode ser interessante para editar arquivos dentro da imagem posteriormente. Para adicionar outros pacotes, basta adicionar seus nomes nessa mesma linha separados por um espaço.

### Adicionar dependências do script Python

Um pacote só é reconhecido se existe em uma das camadas definidas em `build/conf/bblayers.conf`. O script Python que coleta as métricas depende dos pacotes _paho-mqtt_ e _psutil_, que não se encontram em nenhuma dessas camadas.

Felizmente, o OpenEmbedded possui receitas de diversos pacotes úteis para sistemas embarcados, incluindo a camada `meta-python`, que por sua vez contém as receitas dos pacotes sob os nomes `python3-paho-mqtt` e `python3-psutil`.

Então, estando na pasta `poky`, deve-se baixar o repositório `meta-openembedded` com

    $ git clone -b dunfell git://git.openembedded.org/meta-openembedded ./sources/meta-openembedded

Com isso, o repositório será baixado na pasta `poky/sources/meta-openembedded` e assumirá a versão _dunfell_, a fim de manter a compatibilidade.

Em seguida, deve-se adicionar as camadas `meta-oe` e `meta-python` no arquivo `build/conf/bblayers.conf`. Essa tarefa é mais facilmente alcançada ao utilizar o comando `bitbake-layers` estando na pasta `build`:

    $ bitbake-layers add-layer ../sources/meta-openembedded/meta-oe
    $ bitbake-layers add-layer ../sources/meta-openembedded/meta-python

Com isso, pode-se finalmente adicionar os pacotes _paho-mqtt_ e _psutil_ no arquivo `local.conf`:

    IMAGE_INSTALL_append = " vim python3-paho-mqtt python3-psutil"

### Criar receita para o script Python

O script é uma aplicação própria que não existe em nenhuma receita de nenhuma camada, por isso, é necessário criar uma nova camada estando na pasta `sources` com

    $ bitbake-layers create-layer meta-mylayer
    $ bitbake-layers add-layer meta-mylayer

Para cada aplicação ou pacote, é necessário uma receita, por isso, deve-se criar uma nova receita e armazená-la numa pasta própria:

    $ mkdir -p meta-mylayer/recipes-core/python/

É importante nomear a pasta que contém a receita no formato `recipes-*/*/`, pois assim ela será automaticamente reconhecida pelo bitbake.

A aplicação é nomeada `gerador-metricas`, e portanto, sua receita também terá esse nome. O arquivo da receita `gerador-metricas.bb` deve conter o seguinte conteúdo:

    SUMMARY = "Publicador de métricas de desempenho"
    DESCRIPTION = "Programa que publica métricas de desempenho via MQTT"
    LICENSE = "CLOSED"
    LIC_FILES_CHKSUM = ""

    SRC_URI = "file://gerador-metricas.py \
        file://gerador-metricas.service \
        "

    inherit systemd

    SYSTEMD_SERVICE_${PN} = "gerador-metricas.service"

    FILES_${PN} += " \
        ${bindir}/gerador-metricas \
        ${systemd_system_unitdir} \
    "

    do_install() {
        # create the /usr/bin folder in the rootfs with default permissions
        install -d ${D}${bindir}/gerador-metricas

        # install the application into the /usr/bin folder with default permissions
        install ${WORKDIR}/gerador-metricas.py ${D}${bindir}/gerador-metricas

        install -d ${D}${systemd_system_unitdir}
        install ${WORKDIR}/gerador-metricas.service ${D}${systemd_system_unitdir}
    }

A variável *SRC_URI* define o caminho ou endereço dos arquivos requeridos pela receita. Para que o script `gerador-metricas.py` seja reconhecido automaticamente pelo bitbake, ele deve estar dentro de uma pasta `files` em `recipes-core/python/`.

Além do script, também há o arquivo `gerador-metricas.service`, que define um serviço de fundo a ser executado pelo sistema operacional toda vez que ele for iniciado. Para isso, a variável *SYSTEMD_SERVICE_${PN}* é utilizada para definir quais arquivos serão adicionados como serviços _systemd_ à imagem Linux.

A função *do_install* copiará os arquivos do script e do serviço para as pastas `\usr\bin\gerador-metricas` e `\lib\systemd\system` do sistema de arquivos final da imagem, respectivamente.

### Adicionar a nova receita à imagem

Agora que existe a receita contendo a aplicação numa camada reconhecida pelo bitbake, pode-se adicionar o pacote `gerador-metricas` ao arquivo `local.conf`, resultando em:

    IMAGE_INSTALL_append = " vim python3-paho-mqtt python3-psutil gerador-metricas"

Além disso, para que o _systemd_ gerencie o serviço, ele precisa ser habilitado ao adicionar as seguintes linhas ao `local.conf`:

    DISTRO_FEATURES_append = " systemd"
    DISTRO_FEATURES_BACKFILL_CONSIDERED += "sysvinit"
    VIRTUAL-RUNTIME_init_manager = "systemd"
    VIRTUAL-RUNTIME_initscripts = "systemd-compat-units"

## Construção da imagem

### Habilitar processamento paralelo

Para otimizar o tempo de construção da imagem pelo bitbake, deve-se adicionar as seguintes linhas ao arquivo `local.conf`, onde o número corresponde à quantidade de núcleos disponíveis na máquina ambiente:

    BB_NUMBER_THREADS = "4"
    PARALLEL_MAKE = "-j 4"

### Construir a imagem

Enfim, para efetivamente construir a imagem final, basta rodar o comando

    $ bitbake core-image-full-cmdline

Ao fim do processo de geração, uma imagem será gerada para o dispositivo alvo definido pela variável _MACHINE_ em `local.conf`, que por padrão é _qemux86-64_, um dispositivo genérico de arquitetura x86-64 pronto para ser emulado pelo software QEMU. A imagem gerada fica em `build/tmp/deploy/images`.

### Emular a imagem

Para emular a imagem, basta usar

    $ runqemu qemux86-64 nographic

Onde o primeiro argumento é o nome da imagem e o segundo especifica uma opção necessária para imagens sem interface gráfica.

A imagem já vem com um servidor SSH instalado, permitindo que um host inicie uma conexão SSH para transmitir comandos utilizando:

    $ ssh root@<<address>>

Onde _address_ é o endereço IP da interface emulada da imagem, obtível com o comando _ifconfig_ na mesma.

Para fechar a linha de comando da emulação e terminá-la, pode-se usar `Ctrl-A + X`.

## Visualização das métricas de desempenho

Com a imagem rodando, podemos visualizar as métricas de desempenho usando uma interface na ferramenta node-red. 

Para isso, no prompt de comando, executamos o comando `node-red` para iniciar a ferramenta. O node-red então disponibiliza um endereço IP para acesso ao servidor onde executará a interface (nesse caso particular, `http://127.0.0.1:1880/`). 

Após acessar o servidor, em configurações (ícone de 3 barras horizontais no canto superior direito), realizamos o import do arquivo `nodered-interface.json` e clicamos em `Deploy`. Em seguida, vamos em dashboard (o botão com ícone de gráfico de barras na barra lateral direita) e, clicando no botão de flecha em diagonal, abrimos o layout da interface em uma nova aba para finalmente visualizar as métricas de desempenho da imagem em execução.
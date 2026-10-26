# SlackUpdate

Interface gráfica para consultar e instalar atualizações do Slackware usando `slackpkg`. A consulta atualiza os metadados e lista candidatos sem instalar nada. A instalação ocorre somente para os pacotes selecionados, após confirmação e autenticação administrativa via Polkit.

Depois da consulta, os identificadores retornados pelo `slackpkg` são exibidos na tabela com pacote instalado, versão disponível e categoria. Atualizações comuns são pré-selecionadas; kernels ficam desmarcados e bloqueados até que a opção específica seja ativada. O botão de instalação só é habilitado quando há uma consulta válida e pelo menos um pacote selecionado.

## Créditos e marcas

Desenvolvido por **JONAS DE OLIVEIRA SALVIANO • VibeCoding**. Este é um aplicativo não oficial e independente. Slackware™ é uma marca de Patrick Volkerding; a menção no aplicativo apenas identifica a distribuição compatível.

Há uma área separada para **Kernel (opcional)**. Ela identifica registros locais de kernel e mantém a opção desmarcada por padrão; atualizações de kernel jamais entram automaticamente em uma futura instalação. A área **Nova versão do Slackware** consulta o índice HTTPS de mirrors do Slackware e informa a versão estável mais recente, sem iniciar qualquer upgrade de distribuição.

## Instalar no sistema

Execute como administrador usando uma das opções disponíveis no Slackware:

```bash
sudo ./install.sh
# ou:
su -c './install.sh'
```

O instalador adiciona o SlackUpdate ao menu **Sistema** do XFCE e do KDE. Também instala o comando `slackupdate`.

## Executar sem instalar

No diretório do projeto, execute:

```bash
python3 app.py
```

Requisitos: Python 3, GTK 3/PyGObject, `slackpkg`, `pkexec`/Polkit e conexão com o mirror configurado.

## Próxima etapa

O histórico das operações é salvo em `~/.local/state/slackupdate/history.log`.

# SlackUpdate — protótipo

Interface gráfica inicial para um futuro atualizador do Slackware. O botão **Ler pacotes instalados** lê somente os nomes registrados em `/var/log/packages`. **Consultar atualizações on-line** solicita autorização administrativa apenas para atualizar os metadados assinados do `slackpkg` e listar candidatos a upgrade. O comando recebe uma resposta obrigatória `não`: não baixa, instala ou remove pacotes.

## Arquivos temporários e cache

**Verificar arquivos** abre uma janela integrada com tamanho, idade e categoria dos arquivos. A consulta em segundo plano verifica `/var/cache/packages`, o cache do usuário (`XDG_CACHE_HOME` ou `~/.cache`), `/tmp` e `/var/tmp`, com limite de 10.000 entradas percorridas. Resultados parciais e erros de acesso são informados. Os temporários e caches são limitados a arquivos do usuário; links simbólicos não são percorridos.

**Excluir selecionados** move os arquivos marcados para a lixeira após confirmação. Feche os aplicativos e navegadores envolvidos antes de continuar, pois temporários podem estar em uso. Arquivos alterados desde a consulta são recusados, e falhas são apresentadas sem recorrer à exclusão permanente. A limpeza não esvazia a lixeira. Pacotes baixados não podem ser selecionados para exclusão nessa janela.

Caches de navegadores conhecidos são identificados dentro da pasta de cache do usuário; pastas de perfil com senhas, cookies e histórico não são consultadas por padrão. Versões de pacotes diferentes das instaladas são sinalizadas para revisão, sem serem automaticamente consideradas antigas.

Depois da consulta, os identificadores retornados pelo `slackpkg` são interpretados e exibidos na tabela com pacote instalado, versão disponível e categoria. Atualizações comuns são selecionadas para uma futura simulação; kernels ficam desmarcados e bloqueados até que a opção específica de kernel seja ativada. O botão de instalação permanece desativado.

## Créditos e marcas

Desenvolvido por **JONAS DE OLIVEIRA SALVIANO • VibeCoding**. Este é um aplicativo não oficial e independente. Slackware™ é uma marca de Patrick Volkerding; a menção no aplicativo apenas identifica a distribuição compatível.

Há uma área separada para **Kernel (opcional)**. Ela identifica registros locais de kernel e mantém a opção desmarcada por padrão; atualizações de kernel jamais entram automaticamente em uma futura instalação. A área **Nova versão do Slackware** consulta o índice HTTPS de mirrors do Slackware e informa a versão estável mais recente, sem iniciar qualquer upgrade de distribuição.

## Executar localmente

No diretório do projeto, execute:

```bash
python3 app.py
```

Requisitos: Python 3, GTK 3 e PyGObject, com uma sessão gráfica disponível.

Para executar os testes de inspeção e limpeza:

```bash
python3 -m unittest discover -s . -p 'test_*.py'
```

## Próxima etapa

Validar a consulta online ao `slackpkg` no ambiente real. A instalação real só será incluída depois de validar essa consulta e exigir confirmação administrativa com Polkit.

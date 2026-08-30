# SlackUpdate — protótipo

Interface gráfica inicial para um futuro atualizador do Slackware. O botão **Ler pacotes instalados** lê somente os nomes registrados em `/var/log/packages`. **Consultar atualizações on-line** solicita autorização administrativa apenas para atualizar os metadados assinados do `slackpkg` e listar candidatos a upgrade. O comando recebe uma resposta obrigatória `não`: não baixa, instala ou remove pacotes. O botão **Limpar atualizações antigas** ainda é uma simulação e, na versão funcional, deverá limpar somente arquivos de pacotes já baixados em cache — nunca pacotes instalados.

## Executar localmente

No diretório do projeto, execute:

```bash
python3 app.py
```

Requisitos já presentes nesta máquina: Python 3 e GTK 3 (PyGObject).

## Próxima etapa

Depois de validar a leitura de `/var/log/packages`, implementar uma consulta online explícita ao `slackpkg`, sem aplicar alterações. A instalação real só será incluída depois de validar essa consulta e exigir confirmação administrativa com Polkit.

# Projetos locais

Coleção de estudos, protótipos e aplicações pessoais em Python.

## Projetos principais

### `historia-pesquisa/`

Aplicação web local **Clio — Laboratório de Pesquisa em História**.

```bash
cd historia-pesquisa
./iniciar.sh
```

Interface estática em `static/` e banco SQLite em `data/`.

### Assistente e IA local

- `assistente_ia.py` — interface do assistente via API.
- `enable_local_ai.py` — habilitação da interface de IA local.
- `teste_ia_local.html` — página de teste.
- `test_assist.py` — teste manual ainda pendente de transformação em teste seguro.

### Utilitários e aplicações de estudo

- Agendas: `agenda_simples.py`, `agenda_visual.py` e `agenda.json`.
- Tarefas e cadastro: `todo.py`, `todo_gui.py`, `tasks.json`, `cadastro.py`, `dados.json`.
- Backup: `Backup.py` e `cloud_backup_gui.py`.
- Rede: `port_scan.py` e `scan_port.py`.
- Estudos introdutórios: `aula_3.py`, `algoritimo.py`, `Boas_Vindas.py`, `Untitled-2.py`.

### Jogos

- `jogo da velha.py`
- `snake.py`
- `space_invader.py`

## Estado atual

- O repositório ainda não possui commits.
- Os ambientes virtuais e caches ficam excluídos pelo `.gitignore`.
- `algoritimo.py` precisa de correção: há texto solto na linha 2, causando erro de sintaxe.
- Ainda não há arquivo de dependências (`requirements.txt` ou `pyproject.toml`).

## Cuidados

Não versionar `credentials.json`, `token.json`, chaves de API ou arquivos `.env`.
Os programas que acessam rede, APIs, navegador ou interfaces gráficas devem ser
executados manualmente, fora da etapa de validação automática.


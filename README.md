# Projetos

Coleção de estudos, protótipos e aplicações pessoais em **Python** (e um app web de história).

## Estrutura

```text
.
├── historia-pesquisa/   # Clio — laboratório de pesquisa em História (app web local)
├── apps/                # Aplicações utilitárias
│   ├── agenda/          # Agenda de contatos (CLI e GUI)
│   ├── todo/            # Lista de tarefas (CLI e GUI)
│   ├── cadastro/        # Cadastro simples em JSON
│   ├── backup/          # Backup local e em nuvem
│   └── assistente/      # Assistente / IA local
├── jogos/               # Snake, Space Invader, Jogo da Velha
├── estudos/             # Exercícios e demos de aprendizado
├── rede/                # Scripts de scan de portas (estudo)
└── assets/              # Imagens e recursos
```

## Projetos principais

### `historia-pesquisa/` — Clio

Aplicação web local de pesquisa em História.

```bash
cd historia-pesquisa
./iniciar.sh
```

Interface em `static/` e banco SQLite gerado em `data/` (não versionado).

### Apps

| Pasta | Descrição |
|-------|-----------|
| `apps/agenda/` | Contatos em JSON — `agenda_simples.py` (CLI) e `agenda_visual.py` (GUI) |
| `apps/todo/` | Tarefas — `todo.py` / `todo_gui.py` |
| `apps/cadastro/` | Cadastro de registros em `dados.json` |
| `apps/backup/` | `backup.py`, `cloud_backup_app.py`, `cloud_backup_gui.py` |
| `apps/assistente/` | Interface com API e testes de IA local |

Exemplos:

```bash
python apps/agenda/agenda_simples.py
python apps/todo/todo.py
python jogos/snake.py
```

### Jogos

- `jogos/jogo_da_velha.py`
- `jogos/snake.py`
- `jogos/space_invader.py`

### Estudos

- `estudos/boas_vindas.py`, `aula_3.py`, `clay_rotina.py`
- `estudos/carnivore_example.py` — exemplo de classe
- `estudos/matplotlib_dashboard.py` — dashboard IBGE (requer `matplotlib`)
- `estudos/algoritmo_pseudocodigo.txt` — pseudocódigo (não é Python)
- `estudos/ollama/rc.ollama` — config de referência

## Dependências

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
```

Nem todos os scripts precisam de todas as dependências. Os de GUI usam `tkinter` (geralmente vem com o Python do sistema).

## Cuidados

- Não versionar `credentials.json`, `token.json`, chaves de API ou arquivos `.env`.
- Scripts de rede, APIs, navegador ou GUI devem ser executados manualmente.
- `apps/assistente/test_assist.py` é um teste manual — use chave de API válida e com cuidado.

## Licença

MIT — veja [LICENSE](LICENSE).

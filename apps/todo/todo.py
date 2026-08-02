import json
from pathlib import Path


TASKS_FILE = Path(__file__).with_name("tasks.json")


def load_tasks():
    if not TASKS_FILE.exists():
        return []

    try:
        with TASKS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_tasks(tasks):
    with TASKS_FILE.open("w", encoding="utf-8") as file:
        json.dump(tasks, file, ensure_ascii=False, indent=2)


def show_tasks(tasks):
    if not tasks:
        print("\nNenhuma tarefa cadastrada.")
        return

    print("\nLista de tarefas:")
    for index, task in enumerate(tasks, start=1):
        status = "X" if task["done"] else " "
        print(f"{index}. [{status}] {task['title']}")


def add_task(tasks):
    title = input("Digite a nova tarefa: ").strip()
    if not title:
        print("A tarefa nao pode ficar vazia.")
        return

    tasks.append({"title": title, "done": False})
    save_tasks(tasks)
    print("Tarefa adicionada.")


def complete_task(tasks):
    show_tasks(tasks)
    if not tasks:
        return

    try:
        index = int(input("Numero da tarefa concluida: ")) - 1
        tasks[index]["done"] = True
        save_tasks(tasks)
        print("Tarefa marcada como concluida.")
    except (ValueError, IndexError):
        print("Numero invalido.")


def remove_task(tasks):
    show_tasks(tasks)
    if not tasks:
        return

    try:
        index = int(input("Numero da tarefa para remover: ")) - 1
        removed = tasks.pop(index)
        save_tasks(tasks)
        print(f"Tarefa removida: {removed['title']}")
    except (ValueError, IndexError):
        print("Numero invalido.")


def main():
    tasks = load_tasks()

    while True:
        print("\n=== Lista de Tarefas ===")
        print("1. Ver tarefas")
        print("2. Adicionar tarefa")
        print("3. Concluir tarefa")
        print("4. Remover tarefa")
        print("5. Sair")

        option = input("Escolha uma opcao: ").strip()

        if option == "1":
            show_tasks(tasks)
        elif option == "2":
            add_task(tasks)
        elif option == "3":
            complete_task(tasks)
        elif option == "4":
            remove_task(tasks)
        elif option == "5":
            print("Saindo...")
            break
        else:
            print("Opcao invalida.")


if __name__ == "__main__":
    main()

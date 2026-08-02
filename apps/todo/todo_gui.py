import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox


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


class TodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lista de Tarefas")
        self.root.geometry("420x420")

        self.tasks = load_tasks()

        self.title_label = tk.Label(root, text="Lista de Tarefas", font=("Helvetica", 16, "bold"))
        self.title_label.pack(pady=10)

        self.input_frame = tk.Frame(root)
        self.input_frame.pack(padx=10, pady=5, fill="x")

        self.task_entry = tk.Entry(self.input_frame)
        self.task_entry.pack(side="left", fill="x", expand=True)
        self.task_entry.bind("<Return>", lambda event: self.add_task())

        self.add_button = tk.Button(self.input_frame, text="Adicionar", command=self.add_task)
        self.add_button.pack(side="left", padx=(8, 0))

        self.listbox = tk.Listbox(root, height=14)
        self.listbox.pack(padx=10, pady=10, fill="both", expand=True)

        self.button_frame = tk.Frame(root)
        self.button_frame.pack(padx=10, pady=5, fill="x")

        self.complete_button = tk.Button(
            self.button_frame, text="Concluir", command=self.complete_task
        )
        self.complete_button.pack(side="left", fill="x", expand=True)

        self.remove_button = tk.Button(
            self.button_frame, text="Remover", command=self.remove_task
        )
        self.remove_button.pack(side="left", fill="x", expand=True, padx=8)

        self.refresh_list()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for task in self.tasks:
            status = "[X]" if task["done"] else "[ ]"
            self.listbox.insert(tk.END, f"{status} {task['title']}")

    def add_task(self):
        title = self.task_entry.get().strip()
        if not title:
            messagebox.showwarning("Aviso", "Digite uma tarefa.")
            return

        self.tasks.append({"title": title, "done": False})
        save_tasks(self.tasks)
        self.task_entry.delete(0, tk.END)
        self.refresh_list()

    def get_selected_index(self):
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione uma tarefa.")
            return None
        return selected[0]

    def complete_task(self):
        index = self.get_selected_index()
        if index is None:
            return

        self.tasks[index]["done"] = True
        save_tasks(self.tasks)
        self.refresh_list()

    def remove_task(self):
        index = self.get_selected_index()
        if index is None:
            return

        self.tasks.pop(index)
        save_tasks(self.tasks)
        self.refresh_list()


def main():
    root = tk.Tk()
    TodoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

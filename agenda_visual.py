import json
import os
import tkinter as tk
from tkinter import messagebox

ARQUIVO = "agenda.json"


# -------------------- CAMADA DE DADOS --------------------
def carregar_agenda():
    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def salvar_agenda(agenda):
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(agenda, f, indent=4, ensure_ascii=False)


def adicionar_contato(agenda, nome, telefone, email):
    agenda.append({"nome": nome, "telefone": telefone, "email": email})
    salvar_agenda(agenda)


def remover_contato_por_indice(agenda, idx):
    agenda.pop(idx)
    salvar_agenda(agenda)


# -------------------- INTERFACE (TKINTER) --------------------
class AgendaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Agenda - Clay")
        self.root.geometry("520x420")

        self.agenda = carregar_agenda()
        self.filtro = ""

        # Campos
        frame_campos = tk.Frame(root)
        frame_campos.pack(pady=10)

        tk.Label(frame_campos, text="Nome").grid(row=0, column=0, sticky="w")
        tk.Label(frame_campos, text="Telefone").grid(row=0, column=1, sticky="w")
        tk.Label(frame_campos, text="Email").grid(row=0, column=2, sticky="w")

        self.entry_nome = tk.Entry(frame_campos, width=18)
        self.entry_tel = tk.Entry(frame_campos, width=15)
        self.entry_email = tk.Entry(frame_campos, width=22)

        self.entry_nome.grid(row=1, column=0, padx=5)
        self.entry_tel.grid(row=1, column=1, padx=5)
        self.entry_email.grid(row=1, column=2, padx=5)

        # Botões
        frame_botoes = tk.Frame(root)
        frame_botoes.pack(pady=5)

        tk.Button(frame_botoes, text="Adicionar", command=self.on_adicionar).grid(row=0, column=0, padx=5)
        tk.Button(frame_botoes, text="Remover Selecionado", command=self.on_remover).grid(row=0, column=1, padx=5)
        tk.Button(frame_botoes, text="Recarregar", command=self.on_recarregar).grid(row=0, column=2, padx=5)

        # Busca
        frame_busca = tk.Frame(root)
        frame_busca.pack(pady=8)

        tk.Label(frame_busca, text="Buscar (por nome):").grid(row=0, column=0, sticky="w")
        self.entry_busca = tk.Entry(frame_busca, width=30)
        self.entry_busca.grid(row=0, column=1, padx=5)

        tk.Button(frame_busca, text="Buscar", command=self.on_buscar).grid(row=0, column=2, padx=5)
        tk.Button(frame_busca, text="Limpar", command=self.on_limpar_busca).grid(row=0, column=3, padx=5)

        # Lista
        self.listbox = tk.Listbox(root, width=70, height=14)
        self.listbox.pack(pady=10)

        self.atualizar_lista()

    def obter_agenda_filtrada(self):
        if not self.filtro:
            return self.agenda
        f = self.filtro.lower()
        return [c for c in self.agenda if f in c["nome"].lower()]

    def atualizar_lista(self):
        self.listbox.delete(0, tk.END)
        for c in self.obter_agenda_filtrada():
            linha = f"{c['nome']}  |  {c['telefone']}  |  {c['email']}"
            self.listbox.insert(tk.END, linha)

    def on_adicionar(self):
        nome = self.entry_nome.get().strip()
        tel = self.entry_tel.get().strip()
        email = self.entry_email.get().strip()

        if not nome or not tel:
            messagebox.showwarning("Atenção", "Nome e telefone são obrigatórios.")
            return

        adicionar_contato(self.agenda, nome, tel, email)
        self.entry_nome.delete(0, tk.END)
        self.entry_tel.delete(0, tk.END)
        self.entry_email.delete(0, tk.END)

        self.atualizar_lista()
        messagebox.showinfo("Sucesso", "Contato adicionado com sucesso.")

    def on_remover(self):
        selecionado = self.listbox.curselection()
        if not selecionado:
            messagebox.showwarning("Atenção", "Selecione um contato para remover.")
            return

        idx_visivel = selecionado[0]
        agenda_filtrada = self.obter_agenda_filtrada()
        contato = agenda_filtrada[idx_visivel]
        idx_real = self.agenda.index(contato)
        remover_contato_por_indice(self.agenda, idx_real)
        self.atualizar_lista()

    def on_recarregar(self):
        self.agenda = carregar_agenda()
        self.atualizar_lista()

    def on_buscar(self):
        self.filtro = self.entry_busca.get().strip()
        self.atualizar_lista()

    def on_limpar_busca(self):
        self.filtro = ""
        self.entry_busca.delete(0, tk.END)
        self.atualizar_lista()


def main():
    root = tk.Tk()
    AgendaApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

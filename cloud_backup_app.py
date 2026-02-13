 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/README.md b/README.md
index 79c0873ce951b1cb9b433535fe190c74467c844d..8938fe5d1ae85db880a368fd65386877a0b19c59 100644
--- a/README.md
+++ b/README.md
@@ -1,5 +1,46 @@
-# Welcome to GitHub Desktop!
+# Nuvem Fácil (Slackware 15)
 
-This is your README. READMEs are where you can communicate what your project is and how to use it.
+Aplicativo desktop amigável para:
+- visualizar arquivos no **Google Drive** e **OneDrive**;
+- escolher pastas do computador para backup;
+- executar backup manual com um botão;
+- configurar backup **diário**, **semanal** ou **mensal**.
 
-Write your name on line 6, save it, and then head back to GitHub Desktop.
+## Requisitos
+
+- Slackware 15
+- Python 3 com Tkinter
+- `rclone` configurado com remotes:
+  - `gdrive` (Google Drive)
+  - `onedrive` (OneDrive)
+- `crontab` para agendamento
+
+## Como usar
+
+1. Configure o rclone:
+   ```bash
+   rclone config
+   ```
+2. Execute o app:
+   ```bash
+   python3 cloud_backup_app.py
+   ```
+3. No app:
+   - confirme os nomes dos remotes (`gdrive` e `onedrive`);
+   - adicione as pastas para backup;
+   - clique em **Atualizar visualizador** para listar arquivos na nuvem;
+   - clique em **Fazer backup agora** para iniciar backup imediato;
+   - escolha a frequência e clique em **Agendar backup**.
+
+## Backup agendado (modo sem interface)
+
+O app grava a lista de pastas em `backup_folders.txt` e agenda uma tarefa para chamar:
+
+```bash
+python3 cloud_backup_app.py --run-scheduled
+```
+
+Variáveis opcionais para o modo agendado:
+- `NUVEM_FACIL_GDRIVE` (default: `gdrive`)
+- `NUVEM_FACIL_ONEDRIVE` (default: `onedrive`)
+- `NUVEM_FACIL_DESTINO` (default: `Backups/<hostname>`)
diff --git a/cloud_backup_app.py b/cloud_backup_app.py
new file mode 100644
index 0000000000000000000000000000000000000000..9655c80889419567db58cebb489d0e7baa360368
--- /dev/null
+++ b/cloud_backup_app.py
@@ -0,0 +1,332 @@
+#!/usr/bin/env python3
+"""Aplicativo amigável para visualizar arquivos na nuvem e agendar backups via rclone.
+
+Compatível com Slackware 15 (Python + Tkinter + cron + rclone).
+"""
+
+from __future__ import annotations
+
+import os
+import shlex
+import socket
+import subprocess
+from datetime import datetime
+from pathlib import Path
+import tkinter as tk
+from tkinter import filedialog, messagebox, ttk
+
+
+class CloudBackupApp(tk.Tk):
+    def __init__(self) -> None:
+        super().__init__()
+        self.title("Nuvem Fácil - Google Drive e OneDrive")
+        self.geometry("1050x700")
+        self.minsize(980, 640)
+        self.configure(bg="#f5f7fb")
+
+        self.folders: list[str] = []
+
+        self.google_remote = tk.StringVar(value="gdrive")
+        self.one_remote = tk.StringVar(value="onedrive")
+        self.remote_folder = tk.StringVar(value=f"Backups/{socket.gethostname()}")
+        self.schedule = tk.StringVar(value="weekly")
+        self.status_text = tk.StringVar(value="Pronto para configurar seu backup ☁️")
+
+        self._build_ui()
+
+    def _build_ui(self) -> None:
+        header = ttk.Frame(self, padding=(18, 16))
+        header.pack(fill="x")
+
+        title = ttk.Label(
+            header,
+            text="Visualizador de Arquivos na Nuvem + Backup Automático",
+            font=("Segoe UI", 18, "bold"),
+        )
+        title.pack(anchor="w")
+        subtitle = ttk.Label(
+            header,
+            text=(
+                "Conecte seus remotes do rclone (Google Drive e OneDrive), "
+                "veja arquivos e faça backup diário, semanal ou mensal."
+            ),
+            font=("Segoe UI", 10),
+        )
+        subtitle.pack(anchor="w", pady=(3, 0))
+
+        body = ttk.Frame(self, padding=(16, 0, 16, 12))
+        body.pack(fill="both", expand=True)
+
+        left = ttk.Frame(body)
+        left.pack(side="left", fill="y", padx=(0, 12))
+
+        right = ttk.Frame(body)
+        right.pack(side="left", fill="both", expand=True)
+
+        self._build_provider_card(left)
+        self._build_folders_card(left)
+        self._build_schedule_card(left)
+        self._build_actions_card(left)
+
+        self._build_viewer(right)
+
+        status_bar = ttk.Label(self, textvariable=self.status_text, padding=(12, 6))
+        status_bar.pack(fill="x", side="bottom")
+
+    def _build_provider_card(self, parent: ttk.Frame) -> None:
+        card = ttk.LabelFrame(parent, text="Nuvens", padding=12)
+        card.pack(fill="x", pady=(0, 10))
+
+        providers = ttk.Frame(card)
+        providers.pack(fill="x")
+
+        self._logo_widget(
+            providers,
+            "Google Drive",
+            ["#0F9D58", "#4285F4", "#F4B400"],
+            "left",
+        )
+        self._logo_widget(
+            providers,
+            "OneDrive",
+            ["#0364B8", "#0078D4", "#50A9FF"],
+            "left",
+        )
+
+        ttk.Label(card, text="Remote Google Drive no rclone:").pack(anchor="w", pady=(8, 0))
+        ttk.Entry(card, textvariable=self.google_remote, width=28).pack(fill="x", pady=(0, 6))
+
+        ttk.Label(card, text="Remote OneDrive no rclone:").pack(anchor="w")
+        ttk.Entry(card, textvariable=self.one_remote, width=28).pack(fill="x", pady=(0, 6))
+
+        ttk.Label(card, text="Pasta de destino na nuvem:").pack(anchor="w")
+        ttk.Entry(card, textvariable=self.remote_folder, width=28).pack(fill="x")
+
+    def _logo_widget(self, parent: ttk.Frame, name: str, colors: list[str], side: str) -> None:
+        frame = ttk.Frame(parent, padding=(0, 0, 10, 0))
+        frame.pack(side=side, anchor="w")
+
+        canvas = tk.Canvas(frame, width=58, height=44, bg="white", highlightthickness=0)
+        canvas.pack()
+        canvas.create_polygon(29, 5, 7, 38, 20, 38, 42, 5, fill=colors[0], outline="")
+        canvas.create_polygon(29, 5, 42, 5, 52, 22, 39, 22, fill=colors[1], outline="")
+        canvas.create_polygon(7, 38, 20, 38, 39, 22, 26, 22, fill=colors[2], outline="")
+
+        ttk.Label(frame, text=name, font=("Segoe UI", 9, "bold")).pack()
+
+    def _build_folders_card(self, parent: ttk.Frame) -> None:
+        card = ttk.LabelFrame(parent, text="Pastas para backup", padding=12)
+        card.pack(fill="x", pady=(0, 10))
+
+        self.folder_list = tk.Listbox(card, height=7)
+        self.folder_list.pack(fill="x")
+
+        row = ttk.Frame(card)
+        row.pack(fill="x", pady=(8, 0))
+        ttk.Button(row, text="Adicionar pasta", command=self.add_folder).pack(side="left")
+        ttk.Button(row, text="Remover selecionada", command=self.remove_selected_folder).pack(
+            side="left", padx=(8, 0)
+        )
+
+    def _build_schedule_card(self, parent: ttk.Frame) -> None:
+        card = ttk.LabelFrame(parent, text="Frequência do backup automático", padding=12)
+        card.pack(fill="x", pady=(0, 10))
+
+        ttk.Radiobutton(card, text="Diário", variable=self.schedule, value="daily").pack(anchor="w")
+        ttk.Radiobutton(card, text="Semanal", variable=self.schedule, value="weekly").pack(anchor="w")
+        ttk.Radiobutton(card, text="Mensal", variable=self.schedule, value="monthly").pack(anchor="w")
+
+    def _build_actions_card(self, parent: ttk.Frame) -> None:
+        card = ttk.LabelFrame(parent, text="Ações", padding=12)
+        card.pack(fill="x", pady=(0, 10))
+
+        ttk.Button(card, text="🔄 Atualizar visualizador", command=self.refresh_all).pack(fill="x")
+        ttk.Button(card, text="☁️ Fazer backup agora", command=self.backup_now).pack(fill="x", pady=(8, 0))
+        ttk.Button(card, text="🗓️ Agendar backup", command=self.schedule_backup).pack(fill="x", pady=(8, 0))
+
+    def _build_viewer(self, parent: ttk.Frame) -> None:
+        card = ttk.LabelFrame(parent, text="Visualizador de arquivos da nuvem", padding=12)
+        card.pack(fill="both", expand=True)
+
+        self.tabs = ttk.Notebook(card)
+        self.tabs.pack(fill="both", expand=True)
+
+        self.google_text = tk.Text(self.tabs, wrap="none")
+        self.onedrive_text = tk.Text(self.tabs, wrap="none")
+        self.tabs.add(self.google_text, text="Google Drive")
+        self.tabs.add(self.onedrive_text, text="OneDrive")
+
+        for widget in [self.google_text, self.onedrive_text]:
+            widget.configure(font=("Consolas", 10), padx=8, pady=8)
+
+    def add_folder(self) -> None:
+        folder = filedialog.askdirectory(title="Selecione uma pasta para backup")
+        if folder and folder not in self.folders:
+            self.folders.append(folder)
+            self.folder_list.insert("end", folder)
+            self.status_text.set(f"Pasta adicionada: {folder}")
+
+    def remove_selected_folder(self) -> None:
+        selected = self.folder_list.curselection()
+        if not selected:
+            return
+
+        idx = selected[0]
+        folder = self.folder_list.get(idx)
+        self.folder_list.delete(idx)
+        self.folders.remove(folder)
+        self.status_text.set(f"Pasta removida: {folder}")
+
+    def _rclone_lsf(self, remote: str) -> str:
+        target = f"{remote}:{self.remote_folder.get()}"
+        cmd = ["rclone", "lsf", target]
+
+        try:
+            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
+        except FileNotFoundError:
+            return "rclone não encontrado. Instale com seu gerenciador de pacotes."
+        except subprocess.CalledProcessError as err:
+            return f"Erro ao listar {target}:\n{err.stderr.strip() or err.stdout.strip()}"
+
+        output = result.stdout.strip()
+        return output if output else "Nenhum arquivo encontrado neste caminho."
+
+    def refresh_all(self) -> None:
+        g_text = self._rclone_lsf(self.google_remote.get())
+        o_text = self._rclone_lsf(self.one_remote.get())
+
+        self._replace_text(self.google_text, g_text)
+        self._replace_text(self.onedrive_text, o_text)
+        self.status_text.set("Visualizador atualizado.")
+
+    @staticmethod
+    def _replace_text(widget: tk.Text, content: str) -> None:
+        widget.delete("1.0", "end")
+        widget.insert("1.0", content)
+
+    def _backup_commands(self) -> list[list[str]]:
+        commands: list[list[str]] = []
+        remote_folder = self.remote_folder.get().strip("/")
+
+        for folder in self.folders:
+            folder_name = Path(folder).name
+            g_target = f"{self.google_remote.get()}:{remote_folder}/{folder_name}"
+            o_target = f"{self.one_remote.get()}:{remote_folder}/{folder_name}"
+            commands.append(["rclone", "sync", folder, g_target, "--progress"])
+            commands.append(["rclone", "sync", folder, o_target, "--progress"])
+
+        return commands
+
+    def backup_now(self) -> None:
+        if not self.folders:
+            messagebox.showwarning("Atenção", "Adicione pelo menos uma pasta para fazer backup.")
+            return
+
+        commands = self._backup_commands()
+        if not commands:
+            return
+
+        errors: list[str] = []
+        for cmd in commands:
+            try:
+                subprocess.run(cmd, check=True, capture_output=True, text=True)
+            except FileNotFoundError:
+                messagebox.showerror("Erro", "rclone não encontrado no sistema.")
+                return
+            except subprocess.CalledProcessError as err:
+                errors.append(
+                    f"{' '.join(shlex.quote(part) for part in cmd)}\n"
+                    f"{err.stderr.strip() or err.stdout.strip()}"
+                )
+
+        if errors:
+            messagebox.showerror("Backup com erros", "\n\n".join(errors[:3]))
+            self.status_text.set("Backup finalizado com erros. Veja detalhes na janela.")
+            return
+
+        self.status_text.set(f"Backup concluído em {datetime.now().strftime('%H:%M:%S')}.")
+        messagebox.showinfo("Sucesso", "Backup concluído para Google Drive e OneDrive!")
+
+    def schedule_backup(self) -> None:
+        if not self.folders:
+            messagebox.showwarning("Atenção", "Adicione pelo menos uma pasta antes de agendar.")
+            return
+
+        script_path = Path(__file__).resolve()
+        config_path = script_path.with_name("backup_folders.txt")
+        config_path.write_text("\n".join(self.folders), encoding="utf-8")
+
+        cron_expr = {
+            "daily": "0 2 * * *",
+            "weekly": "0 2 * * 1",
+            "monthly": "0 2 1 * *",
+        }[self.schedule.get()]
+
+        cron_cmd = (
+            f"{cron_expr} /usr/bin/env python3 {shlex.quote(str(script_path))} --run-scheduled"
+        )
+
+        marker = "# nuvem-facil-backup"
+        new_line = f"{cron_cmd} {marker}"
+
+        try:
+            existing = subprocess.run(["crontab", "-l"], check=False, capture_output=True, text=True)
+            lines = [line for line in existing.stdout.splitlines() if marker not in line]
+            lines.append(new_line)
+            payload = "\n".join(lines) + "\n"
+            subprocess.run(["crontab", "-"], input=payload, check=True, text=True)
+        except FileNotFoundError:
+            messagebox.showerror("Erro", "crontab não encontrado no sistema.")
+            return
+        except subprocess.CalledProcessError as err:
+            messagebox.showerror("Erro", f"Falha ao salvar crontab:\n{err}")
+            return
+
+        self.status_text.set("Backup automático agendado com sucesso.")
+        messagebox.showinfo("Agendamento criado", "Backup automático configurado no crontab.")
+
+
+def run_scheduled_backup() -> int:
+    """Executa backup agendado sem UI, lendo backup_folders.txt."""
+    script_path = Path(__file__).resolve()
+    config_path = script_path.with_name("backup_folders.txt")
+    if not config_path.exists():
+        print("Arquivo backup_folders.txt não encontrado.")
+        return 1
+
+    folders = [line.strip() for line in config_path.read_text(encoding="utf-8").splitlines() if line.strip()]
+    if not folders:
+        print("Nenhuma pasta configurada para backup.")
+        return 1
+
+    google_remote = os.getenv("NUVEM_FACIL_GDRIVE", "gdrive")
+    one_remote = os.getenv("NUVEM_FACIL_ONEDRIVE", "onedrive")
+    remote_folder = os.getenv("NUVEM_FACIL_DESTINO", f"Backups/{socket.gethostname()}").strip("/")
+
+    for folder in folders:
+        folder_name = Path(folder).name
+        targets = [
+            f"{google_remote}:{remote_folder}/{folder_name}",
+            f"{one_remote}:{remote_folder}/{folder_name}",
+        ]
+        for target in targets:
+            cmd = ["rclone", "sync", folder, target]
+            print("Executando:", " ".join(shlex.quote(x) for x in cmd))
+            try:
+                subprocess.run(cmd, check=True)
+            except Exception as err:
+                print("Erro:", err)
+                return 1
+
+    print("Backup agendado concluído com sucesso.")
+    return 0
+
+
+if __name__ == "__main__":
+    import sys
+
+    if "--run-scheduled" in sys.argv:
+        raise SystemExit(run_scheduled_backup())
+
+    app = CloudBackupApp()
+    app.mainloop()
 
EOF
)

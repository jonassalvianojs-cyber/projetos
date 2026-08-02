#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloud Backup GUI (Slackware 15)
- Navega em remotos rclone (Google Drive / OneDrive)
- Cria jobs de backup (rclone sync) com agendamento via crontab do usuário
- Botão "Backup agora"
Requisitos: python3, tkinter, rclone, cron rodando
"""
from __future__ import annotations

import base64
import datetime as _dt
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except Exception as e:
    print("Erro: não consegui importar tkinter. No Slackware, instale tk/tcl e o módulo tkinter do Python.", file=sys.stderr)
    raise


APP_NAME = "NuvemBackup GUI"
APP_DIR = Path.home() / ".config" / "cloud_backup_gui"
CACHE_DIR = Path.home() / ".cache" / "cloud_backup_gui"
CONFIG_FILE = APP_DIR / "config.json"
LOG_FILE = CACHE_DIR / "app.log"

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
GOOGLE_ICON = ASSETS_DIR / "google_drive.png"
ONEDRIVE_ICON = ASSETS_DIR / "onedrive.png"

CRON_BEGIN = "# CLOUD_BACKUP_GUI_BEGIN"
CRON_END = "# CLOUD_BACKUP_GUI_END"


def ensure_dirs() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    ensure_dirs()
    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def run_cmd(cmd: List[str], timeout: int = 120) -> Tuple[int, str, str]:
    """Run subprocess and return (code, stdout, stderr)."""
    log("CMD: " + " ".join(cmd))
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", f"Comando não encontrado: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", "Timeout executando comando."


def human_size(num: int) -> str:
    # 0.. bytes
    units = ["B", "KB", "MB", "GB", "TB"]
    n = float(num)
    for u in units:
        if n < 1024.0 or u == units[-1]:
            return f"{n:.1f} {u}" if u != "B" else f"{int(n)} {u}"
        n /= 1024.0
    return f"{num} B"


@dataclass
class BackupJob:
    id: str
    name: str
    local_path: str
    remote_name: str     # rclone remote name, ex: "gdrive"
    remote_path: str     # path dentro do remote, ex: "Backups/PC"
    schedule: str        # daily | weekly | monthly
    time_hhmm: str       # "02:00"
    weekday: int = 0     # 0=Sunday ... 6=Saturday (cron)
    monthday: int = 1    # 1..31

    def cron_expr(self) -> str:
        hh, mm = parse_hhmm(self.time_hhmm)
        if self.schedule == "daily":
            return f"{mm} {hh} * * *"
        if self.schedule == "weekly":
            return f"{mm} {hh} * * {self.weekday}"
        # monthly
        return f"{mm} {hh} {self.monthday} * *"

    def remote_spec(self) -> str:
        # rclone remote spec: "remote:subpath"
        path = self.remote_path.strip("/")
        return f"{self.remote_name}:{path}" if path else f"{self.remote_name}:"


def parse_hhmm(s: str) -> Tuple[int, int]:
    try:
        hh, mm = s.strip().split(":")
        h = int(hh); m = int(mm)
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        return h, m
    except Exception:
        return 2, 0


class ConfigStore:
    def __init__(self, path: Path):
        self.path = path
        self.data: Dict[str, Any] = {"jobs": []}

    def load(self) -> None:
        ensure_dirs()
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.save()

    def save(self) -> None:
        ensure_dirs()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def jobs(self) -> List[BackupJob]:
        out: List[BackupJob] = []
        for j in self.data.get("jobs", []):
            try:
                out.append(BackupJob(**j))
            except TypeError:
                continue
        return out

    def upsert_job(self, job: BackupJob) -> None:
        jobs = self.data.get("jobs", [])
        for i, j in enumerate(jobs):
            if j.get("id") == job.id:
                jobs[i] = asdict(job)
                self.data["jobs"] = jobs
                self.save()
                return
        jobs.append(asdict(job))
        self.data["jobs"] = jobs
        self.save()

    def delete_job(self, job_id: str) -> None:
        jobs = [j for j in self.data.get("jobs", []) if j.get("id") != job_id]
        self.data["jobs"] = jobs
        self.save()


def rclone_available() -> bool:
    code, out, _ = run_cmd(["rclone", "version"], timeout=10)
    return code == 0 and "rclone" in out.lower()


def rclone_listremotes() -> List[str]:
    code, out, err = run_cmd(["rclone", "listremotes"], timeout=20)
    if code != 0:
        return []
    remotes = []
    for line in out.splitlines():
        x = line.strip()
        if x.endswith(":"):
            remotes.append(x[:-1])
    return remotes


def rclone_lsjson(remote: str, subpath: str = "") -> List[Dict[str, Any]]:
    spec = f"{remote}:{subpath.strip('/')}" if subpath else f"{remote}:"
    cmd = ["rclone", "lsjson", spec, "--max-depth", "1"]
    code, out, err = run_cmd(cmd, timeout=60)
    if code != 0:
        raise RuntimeError(err.strip() or "Falha ao listar arquivos.")
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        raise RuntimeError("Resposta inválida do rclone (JSON).")


def rclone_copyto(src_spec: str, dst_path: str) -> None:
    code, out, err = run_cmd(["rclone", "copyto", src_spec, dst_path], timeout=3600)
    if code != 0:
        raise RuntimeError(err.strip() or "Falha no download (rclone).")


def rclone_sync(local_path: str, remote_spec: str, extra_args: Optional[List[str]] = None) -> Tuple[int, str, str]:
    """Backup padrão: copia arquivos do PC para a nuvem SEM apagar nada na nuvem.
    (Se quiser espelhamento com deleções, troque "copy" por "sync".)
    """
    args = ["rclone", "copy", local_path, remote_spec, "--create-empty-src-dirs"]
    if extra_args:
        args += extra_args
    return run_cmd(args, timeout=24 * 3600)


def xdg_open(path: str) -> None:
    if shutil.which("xdg-open"):
        subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        messagebox.showinfo("Arquivo baixado", f"Arquivo salvo em:\n{path}\n\nInstale xdg-utils para abrir automaticamente.")


def read_user_crontab() -> str:
    code, out, err = run_cmd(["crontab", "-l"], timeout=10)
    if code != 0:
        # Sem crontab ainda → retorna vazio
        return ""
    return out


def write_user_crontab(content: str) -> None:
    p = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
    p.communicate(content)
    if p.returncode != 0:
        raise RuntimeError("Falha ao atualizar crontab do usuário.")


def build_cron_block(script_path: str, jobs: List[BackupJob]) -> str:
    lines = [CRON_BEGIN]
    lines.append(f"# Gerado por {APP_NAME} em {_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    for job in jobs:
        expr = job.cron_expr()
        log_path = str(CACHE_DIR / f"job_{job.id}.log")
        cmd = f'{expr} /usr/bin/env python3 "{script_path}" --run-job "{job.id}" >> "{log_path}" 2>&1'
        lines.append(cmd)
    lines.append(CRON_END)
    return "\n".join(lines) + "\n"


def apply_cron(script_path: str, jobs: List[BackupJob]) -> None:
    current = read_user_crontab().splitlines()
    # Remove bloco antigo
    out_lines: List[str] = []
    inside = False
    for line in current:
        if line.strip() == CRON_BEGIN:
            inside = True
            continue
        if inside and line.strip() == CRON_END:
            inside = False
            continue
        if not inside:
            out_lines.append(line)
    # Adiciona bloco novo no fim
    if jobs:
        out_lines.append(build_cron_block(script_path, jobs).rstrip("\n"))
    new_content = "\n".join(out_lines).rstrip("\n") + "\n"
    write_user_crontab(new_content)


class CloudBackupGUI(tk.Tk):
    def __init__(self, store: ConfigStore):
        super().__init__()
        self.store = store
        self.title(APP_NAME)
        self.geometry("980x640")
        self.minsize(900, 600)

        self.queue: "queue.Queue[Tuple[str, Any]]" = queue.Queue()
        self.current_remote = tk.StringVar(value="")
        self.current_subpath = tk.StringVar(value="")
        self.remote_error = tk.StringVar(value="")
        self.status_text = tk.StringVar(value="Pronto ✅")

        self.icons = {}
        self._load_icons()
        self._build_ui()
        self._poll_queue()

        self._load_remotes()
        self._refresh_jobs_list()

    # ---------- UI ----------
    def _load_icons(self) -> None:
        """Carrega ícones opcionais de `assets/` de forma segura.
        Se os arquivos não existirem ou ocorrer erro, apenas registra e segue sem ícones.
        """
        self.icons = {}
        try:
            # PhotoImage requer que a instância Tk já exista (estamos dentro de __init__ depois de super())
            if GOOGLE_ICON.exists():
                try:
                    self.icons["gdrive"] = tk.PhotoImage(file=str(GOOGLE_ICON))
                except Exception as e:
                    log(f"Falha ao carregar ícone google: {e}")
            if ONEDRIVE_ICON.exists():
                try:
                    self.icons["onedrive"] = tk.PhotoImage(file=str(ONEDRIVE_ICON))
                except Exception as e:
                    log(f"Falha ao carregar ícone onedrive: {e}")
        except Exception as e:
            # Protege qualquer erro inesperado para não quebrar a inicialização da UI
            log(f"Erro em _load_icons: {e}")

    def _build_ui(self) -> None:
        # Top bar
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text=APP_NAME, font=("TkDefaultFont", 16, "bold")).pack(side="left")
        # Logos (opcionais) — coloque assets/google_drive.png e assets/onedrive.png
        if self.icons.get("gdrive"):
            ttk.Label(top, image=self.icons["gdrive"]).pack(side="left", padx=(12, 6))
        else:
            ttk.Label(top, text="Drive").pack(side="left", padx=(12, 6))
        if self.icons.get("onedrive"):
            ttk.Label(top, image=self.icons["onedrive"]).pack(side="left", padx=(0, 10))
        else:
            ttk.Label(top, text="OneDrive").pack(side="left", padx=(0, 10))
        self.lbl_rclone = ttk.Label(top, text="rclone: checando…")
        self.lbl_rclone.pack(side="right")

        # Tabs
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_browser = ttk.Frame(nb, padding=10)
        self.tab_backup = ttk.Frame(nb, padding=10)
        nb.add(self.tab_browser, text="☁️ Visualizador")
        nb.add(self.tab_backup, text="🗂️ Backups")

        self._build_browser_tab(self.tab_browser)
        self._build_backup_tab(self.tab_backup)

        # Status bar
        status = ttk.Frame(self, padding=(10, 0, 10, 10))
        status.pack(fill="x")
        ttk.Label(status, textvariable=self.status_text).pack(side="left")

    def _build_browser_tab(self, parent: ttk.Frame) -> None:
        # Controls
        controls = ttk.Frame(parent)
        controls.pack(fill="x")

        ttk.Label(controls, text="Remote (rclone):").grid(row=0, column=0, sticky="w")
        self.cmb_remote = ttk.Combobox(controls, textvariable=self.current_remote, width=30, state="readonly")
        self.cmb_remote.grid(row=0, column=1, sticky="w", padx=(8, 12))
        self.cmb_remote.bind("<<ComboboxSelected>>", lambda e: self._browser_refresh())

        # Atalhos (com logos se você colocar os PNGs em assets/)
        shortcuts = ttk.Frame(controls)
        shortcuts.grid(row=1, column=1, sticky="w", pady=(8, 0))
        ttk.Button(shortcuts, text="Google Drive", image=self.icons.get("gdrive"), compound="left",
                   command=lambda: self._select_remote_hint("gdrive")).pack(side="left", padx=(0, 8))
        ttk.Button(shortcuts, text="OneDrive", image=self.icons.get("onedrive"), compound="left",
                   command=lambda: self._select_remote_hint("onedrive")).pack(side="left")

        ttk.Label(controls, text="Pasta na nuvem:").grid(row=0, column=2, sticky="w")
        self.ent_path = ttk.Entry(controls, textvariable=self.current_subpath, width=45)
        self.ent_path.grid(row=0, column=3, sticky="we", padx=(8, 8))

        btns = ttk.Frame(controls)
        btns.grid(row=0, column=4, sticky="e")
        ttk.Button(btns, text="⬆️ Voltar", command=self._browser_up).pack(side="left", padx=4)
        ttk.Button(btns, text="🔄 Atualizar", command=self._browser_refresh).pack(side="left", padx=4)

        controls.columnconfigure(3, weight=1)

        # Treeview
        columns = ("nome", "tipo", "tamanho", "modificado")
        self.tree = ttk.Treeview(parent, columns=columns, show="headings", height=16)
        self.tree.heading("nome", text="Nome")
        self.tree.heading("tipo", text="Tipo")
        self.tree.heading("tamanho", text="Tamanho")
        self.tree.heading("modificado", text="Modificado")
        self.tree.column("nome", width=420, anchor="w")
        self.tree.column("tipo", width=90, anchor="w")
        self.tree.column("tamanho", width=90, anchor="e")
        self.tree.column("modificado", width=220, anchor="w")

        self.tree.pack(fill="both", expand=True, pady=(10, 6))
        self.tree.bind("<Double-1>", self._browser_open_or_enter)

        # Actions
        actions = ttk.Frame(parent)
        actions.pack(fill="x")
        ttk.Button(actions, text="📂 Entrar (pasta) / Abrir (arquivo)", command=self._browser_open_selected).pack(side="left")
        ttk.Button(actions, text="⬇️ Baixar (escolher pasta)", command=self._browser_download_selected).pack(side="left", padx=8)
        self.lbl_err = ttk.Label(actions, textvariable=self.remote_error, foreground="red")
        self.lbl_err.pack(side="right")

    def _build_backup_tab(self, parent: ttk.Frame) -> None:
        layout = ttk.Frame(parent)
        layout.pack(fill="both", expand=True)

        left = ttk.Frame(layout)
        left.pack(side="left", fill="both", expand=False, padx=(0, 12))
        right = ttk.Frame(layout)
        right.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text="Jobs cadastrados").pack(anchor="w")
        self.jobs_list = tk.Listbox(left, height=20, width=32)
        self.jobs_list.pack(fill="y", expand=False, pady=(6, 6))
        self.jobs_list.bind("<<ListboxSelect>>", lambda e: self._on_job_select())

        ttk.Button(left, text="➕ Novo job", command=self._new_job_form).pack(fill="x", pady=4)
        ttk.Button(left, text="🗑️ Remover job", command=self._delete_selected_job).pack(fill="x", pady=4)
        ttk.Button(left, text="⏱️ Aplicar agendamento (cron)", command=self._apply_cron_ui).pack(fill="x", pady=12)

        # Form fields (right)
        form = ttk.LabelFrame(right, text="Configurar job", padding=10)
        form.pack(fill="x", pady=(0, 10))

        self.job_id: Optional[str] = None

        self.var_name = tk.StringVar(value="")
        self.var_local = tk.StringVar(value="")
        self.var_remote = tk.StringVar(value="")
        self.var_remote_path = tk.StringVar(value="Backups/MeuPC")
        self.var_schedule = tk.StringVar(value="daily")
        self.var_time = tk.StringVar(value="02:00")
        self.var_weekday = tk.IntVar(value=0)
        self.var_monthday = tk.IntVar(value=1)

        r = 0
        ttk.Label(form, text="Nome:").grid(row=r, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_name, width=40).grid(row=r, column=1, sticky="we", padx=(8, 0), columnspan=3)
        r += 1

        ttk.Label(form, text="Pasta do PC:").grid(row=r, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(form, textvariable=self.var_local, width=50).grid(row=r, column=1, sticky="we", padx=(8, 8), pady=(8, 0), columnspan=2)
        ttk.Button(form, text="📁 Escolher", command=self._pick_local_folder).grid(row=r, column=3, sticky="e", pady=(8, 0))
        r += 1

        ttk.Label(form, text="Remote (rclone):").grid(row=r, column=0, sticky="w", pady=(8, 0))
        self.cmb_job_remote = ttk.Combobox(form, textvariable=self.var_remote, width=28, state="readonly")
        self.cmb_job_remote.grid(row=r, column=1, sticky="w", padx=(8, 8), pady=(8, 0))
        ttk.Label(form, text="Pasta na nuvem:").grid(row=r, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(form, textvariable=self.var_remote_path, width=30).grid(row=r, column=3, sticky="we", pady=(8, 0))
        r += 1

        ttk.Label(form, text="Frequência:").grid(row=r, column=0, sticky="w", pady=(10, 0))
        freq = ttk.Frame(form)
        freq.grid(row=r, column=1, sticky="w", padx=(8, 0), pady=(10, 0), columnspan=3)
        ttk.Radiobutton(freq, text="Diário", value="daily", variable=self.var_schedule, command=self._update_schedule_fields).pack(side="left", padx=6)
        ttk.Radiobutton(freq, text="Semanal", value="weekly", variable=self.var_schedule, command=self._update_schedule_fields).pack(side="left", padx=6)
        ttk.Radiobutton(freq, text="Mensal", value="monthly", variable=self.var_schedule, command=self._update_schedule_fields).pack(side="left", padx=6)
        r += 1

        ttk.Label(form, text="Hora (HH:MM):").grid(row=r, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(form, textvariable=self.var_time, width=10).grid(row=r, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

        self.frm_weekday = ttk.Frame(form)
        self.frm_monthday = ttk.Frame(form)

        ttk.Label(self.frm_weekday, text="Dia da semana:").pack(side="left")
        self.cmb_weekday = ttk.Combobox(self.frm_weekday, width=18, state="readonly",
                                        values=["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"])
        self.cmb_weekday.current(0)
        self.cmb_weekday.pack(side="left", padx=8)

        ttk.Label(self.frm_monthday, text="Dia do mês:").pack(side="left")
        self.spn_monthday = ttk.Spinbox(self.frm_monthday, from_=1, to=31, width=5, textvariable=self.var_monthday)
        self.spn_monthday.pack(side="left", padx=8)

        self.frm_weekday.grid(row=r, column=2, sticky="w", padx=(0, 0), pady=(8, 0), columnspan=2)
        self.frm_monthday.grid(row=r, column=2, sticky="w", padx=(0, 0), pady=(8, 0), columnspan=2)
        r += 1

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        # Buttons
        btnrow = ttk.Frame(right)
        btnrow.pack(fill="x", pady=(0, 10))
        ttk.Button(btnrow, text="💾 Salvar job", command=self._save_job).pack(side="left")
        ttk.Button(btnrow, text="🚀 Backup agora", command=self._run_selected_job_now).pack(side="left", padx=8)

        ttk.Button(btnrow, text="📄 Abrir logs", command=self._open_logs_folder).pack(side="right")

        # Output
        out = ttk.LabelFrame(right, text="Saída / Status", padding=10)
        out.pack(fill="both", expand=True)
        self.txt = tk.Text(out, height=12, wrap="word")
        self.txt.pack(fill="both", expand=True)
        self.txt.insert("end", "Dica: configure seus remotos no rclone (Google Drive/OneDrive) e depois crie jobs aqui. 😊\n")

        self._update_schedule_fields()

    # ---------- Events ----------
    def _poll_queue(self) -> None:
        try:
            while True:
                typ, payload = self.queue.get_nowait()
                if typ == "status":
                    self.status_text.set(payload)
                elif typ == "log":
                    self._append_text(str(payload))
                elif typ == "browser_rows":
                    self._browser_set_rows(payload)
                elif typ == "browser_err":
                    self.remote_error.set(payload)
                elif typ == "rclone_state":
                    self.lbl_rclone.config(text=payload)
        except queue.Empty:
            pass
        self.after(200, self._poll_queue)

    def _append_text(self, s: str) -> None:
        self.txt.insert("end", s + "\n")
        self.txt.see("end")

    # ---------- Initialization ----------
    def _load_remotes(self) -> None:
        def worker():
            ok = rclone_available()
            if not ok:
                self.queue.put(("rclone_state", "rclone: ❌ não encontrado"))
                self.queue.put(("log", "⚠️ Instale o rclone e rode: rclone config"))
                return
            self.queue.put(("rclone_state", "rclone: ✅ ok"))
            remotes = rclone_listremotes()
            if not remotes:
                self.queue.put(("log", "⚠️ Nenhum remote encontrado. Rode: rclone config"))
            self.queue.put(("status", "Remotos carregados ✅"))
            self.queue.put(("remotes", remotes))
            self.after(0, lambda: self._set_remotes(remotes))

        threading.Thread(target=worker, daemon=True).start()

    def _set_remotes(self, remotes: List[str]) -> None:
        self.cmb_remote["values"] = remotes
        self.cmb_job_remote["values"] = remotes
        if remotes and not self.current_remote.get():
            self.current_remote.set(remotes[0])
            self.var_remote.set(remotes[0])
            self._browser_refresh()
        elif remotes and not self.var_remote.get():
            self.var_remote.set(remotes[0])

    def _select_remote_hint(self, kind: str) -> None:
        """Seleciona automaticamente um remote compatível (por nome)."""
        remotes = list(self.cmb_remote["values"])
        if not remotes:
            messagebox.showinfo("Remotes", "Nenhum remote do rclone foi encontrado.")
            return
        kind_l = kind.lower()
        # heurística: procura por onedrive / drive / gdrive etc.
        def score(r: str) -> int:
            rl = r.lower()
            if kind_l == "onedrive":
                return 3 if "onedrive" in rl else (2 if "one" in rl else 0)
            # google drive
            return 3 if rl in ("gdrive", "drive", "google") else (2 if "drive" in rl else (1 if "g" in rl and "drive" in rl else 0))
        best = max(remotes, key=score)
        if score(best) == 0:
            messagebox.showinfo("Dica", f"Não achei um remote parecido com {kind}.\nSelecione manualmente na lista.")
            return
        self.current_remote.set(best)
        self.var_remote.set(best)
        self._browser_refresh()

    # ---------- Browser ----------
    def _browser_refresh(self) -> None:
        remote = self.current_remote.get().strip()
        subpath = self.current_subpath.get().strip().strip("/")
        if not remote:
            return

        self.remote_error.set("")
        self.queue.put(("status", "Listando arquivos… ⏳"))

        def worker():
            try:
                rows = rclone_lsjson(remote, subpath)
                # Normalize rows for UI
                ui_rows = []
                for it in rows:
                    name = it.get("Name") or it.get("Path") or ""
                    is_dir = bool(it.get("IsDir"))
                    size = it.get("Size") or 0
                    mod = it.get("ModTime") or ""
                    typ = "📁 Pasta" if is_dir else "📄 Arquivo"
                    ui_rows.append((name, typ, human_size(int(size)), mod, is_dir))
                # sort dirs first
                ui_rows.sort(key=lambda x: (not x[4], x[0].lower()))
                self.queue.put(("browser_rows", ui_rows))
                self.queue.put(("status", "Pronto ✅"))
            except Exception as e:
                self.queue.put(("browser_err", str(e)))
                self.queue.put(("status", "Falha ao listar ❌"))

        threading.Thread(target=worker, daemon=True).start()

    def _browser_set_rows(self, ui_rows: List[Tuple[str, str, str, str, bool]]) -> None:
        # Clear
        for item in self.tree.get_children():
            self.tree.delete(item)
        # Insert
        # We'll store name + is_dir in iid via a JSON-ish string
        for name, typ, size, mod, is_dir in ui_rows:
            iid = f"{'D' if is_dir else 'F'}::{name}"
            self.tree.insert("", "end", iid=iid, values=(name, typ, size, mod))

    def _browser_selected(self) -> Tuple[Optional[str], Optional[bool]]:
        sel = self.tree.selection()
        if not sel:
            return None, None
        iid = sel[0]
        if "::" not in iid:
            return None, None
        kind, name = iid.split("::", 1)
        return name, (kind == "D")

    def _browser_up(self) -> None:
        p = self.current_subpath.get().strip().strip("/")
        if not p:
            return
        parts = p.split("/")
        self.current_subpath.set("/".join(parts[:-1]))
        self._browser_refresh()

    def _browser_open_or_enter(self, event) -> None:
        self._browser_open_selected()

    def _browser_open_selected(self) -> None:
        name, is_dir = self._browser_selected()
        if name is None:
            return
        if is_dir:
            p = self.current_subpath.get().strip().strip("/")
            newp = f"{p}/{name}".strip("/") if p else name
            self.current_subpath.set(newp)
            self._browser_refresh()
        else:
            self._browser_download(open_after=True)

    def _browser_download_selected(self) -> None:
        self._browser_download(open_after=False)

    def _browser_download(self, open_after: bool) -> None:
        name, is_dir = self._browser_selected()
        if name is None or is_dir:
            messagebox.showinfo("Seleção", "Selecione um arquivo (não uma pasta).")
            return
        remote = self.current_remote.get().strip()
        subpath = self.current_subpath.get().strip().strip("/")
        src = f"{remote}:{(subpath + '/' if subpath else '')}{name}"

        if open_after:
            dst_dir = tempfile.mkdtemp(prefix="cloudview_")
        else:
            dst_dir = filedialog.askdirectory(title="Escolha onde salvar o arquivo")
            if not dst_dir:
                return

        dst_path = str(Path(dst_dir) / name)
        self.queue.put(("status", "Baixando… ⏳"))
        self.remote_error.set("")

        def worker():
            try:
                rclone_copyto(src, dst_path)
                self.queue.put(("log", f"⬇️ Baixado: {dst_path}"))
                self.queue.put(("status", "Download concluído ✅"))
                if open_after:
                    self.after(0, lambda: xdg_open(dst_path))
            except Exception as e:
                self.queue.put(("browser_err", str(e)))
                self.queue.put(("status", "Falha no download ❌"))

        threading.Thread(target=worker, daemon=True).start()

    # ---------- Jobs ----------
    def _refresh_jobs_list(self) -> None:
        self.store.load()
        self.jobs = self.store.jobs()
        self.jobs_list.delete(0, "end")
        for j in self.jobs:
            self.jobs_list.insert("end", j.name)

    def _on_job_select(self) -> None:
        idxs = self.jobs_list.curselection()
        if not idxs:
            return
        j = self.jobs[idxs[0]]
        self.job_id = j.id
        self.var_name.set(j.name)
        self.var_local.set(j.local_path)
        self.var_remote.set(j.remote_name)
        self.var_remote_path.set(j.remote_path)
        self.var_schedule.set(j.schedule)
        self.var_time.set(j.time_hhmm)
        self.var_weekday.set(j.weekday)
        self.var_monthday.set(j.monthday)
        self.cmb_weekday.current(int(j.weekday))
        self._update_schedule_fields()

    def _new_job_form(self) -> None:
        self.job_id = None
        self.var_name.set("")
        self.var_local.set("")
        rem = self.current_remote.get() or (self.cmb_job_remote["values"][0] if self.cmb_job_remote["values"] else "")
        self.var_remote.set(rem)
        self.var_remote_path.set("Backups/MeuPC")
        self.var_schedule.set("daily")
        self.var_time.set("02:00")
        self.var_weekday.set(0)
        self.var_monthday.set(1)
        self.cmb_weekday.current(0)
        self._update_schedule_fields()

    def _pick_local_folder(self) -> None:
        p = filedialog.askdirectory(title="Escolha a pasta do computador")
        if p:
            self.var_local.set(p)

    def _update_schedule_fields(self) -> None:
        sched = self.var_schedule.get()
        # show only relevant frame
        self.frm_weekday.grid_remove()
        self.frm_monthday.grid_remove()
        if sched == "weekly":
            self.frm_weekday.grid()
        elif sched == "monthly":
            self.frm_monthday.grid()

    def _save_job(self) -> None:
        name = self.var_name.get().strip() or "Backup"
        local_path = self.var_local.get().strip()
        remote = self.var_remote.get().strip()
        remote_path = self.var_remote_path.get().strip().strip("/")
        sched = self.var_schedule.get()
        hhmm = self.var_time.get().strip()
        h, m = parse_hhmm(hhmm)
        hhmm = f"{h:02d}:{m:02d}"

        if not local_path or not Path(local_path).exists():
            messagebox.showerror("Pasta inválida", "Escolha uma pasta existente no computador.")
            return
        if not remote:
            messagebox.showerror("Remote", "Selecione um remote do rclone.")
            return

        weekday = int(self.cmb_weekday.current()) if sched == "weekly" else 0
        monthday = int(self.var_monthday.get()) if sched == "monthly" else 1
        monthday = max(1, min(31, monthday))

        job = BackupJob(
            id=self.job_id or str(uuid.uuid4())[:8],
            name=name,
            local_path=local_path,
            remote_name=remote,
            remote_path=remote_path,
            schedule=sched,
            time_hhmm=hhmm,
            weekday=weekday,
            monthday=monthday,
        )
        self.store.upsert_job(job)
        self._refresh_jobs_list()
        self.queue.put(("log", f"💾 Job salvo: {job.name}  →  {job.local_path}  →  {job.remote_spec()}"))
        self.queue.put(("status", "Job salvo ✅"))

    def _delete_selected_job(self) -> None:
        idxs = self.jobs_list.curselection()
        if not idxs:
            return
        j = self.jobs[idxs[0]]
        if messagebox.askyesno("Remover job", f"Remover '{j.name}'?"):
            self.store.delete_job(j.id)
            self._refresh_jobs_list()
            self._new_job_form()
            self.queue.put(("log", f"🗑️ Job removido: {j.name}"))
            self.queue.put(("status", "Job removido ✅"))

    def _apply_cron_ui(self) -> None:
        self.store.load()
        jobs = self.store.jobs()
        script_path = str(Path(sys.argv[0]).resolve())
        try:
            apply_cron(script_path, jobs)
            self.queue.put(("log", "⏱️ Agendamentos aplicados no seu crontab (usuario)."))
            self.queue.put(("status", "Agendamento ok ✅"))
            messagebox.showinfo("Cron", "Agendamentos atualizados no seu crontab.\n\nDica: certifique-se de que o serviço cron (crond) está rodando.")
        except Exception as e:
            messagebox.showerror("Cron", str(e))

    def _run_selected_job_now(self) -> None:
        idxs = self.jobs_list.curselection()
        if not idxs:
            messagebox.showinfo("Seleção", "Selecione um job na lista.")
            return
        job = self.jobs[idxs[0]]
        self._run_job(job)

    def _run_job(self, job: BackupJob) -> None:
        self.queue.put(("status", f"Rodando backup '{job.name}'… ⏳"))
        self.queue.put(("log", f"🚀 Iniciando backup: {job.name}"))
        remote_spec = job.remote_spec()

        def worker():
            code, out, err = rclone_sync(job.local_path, remote_spec, extra_args=["--progress"])
            if out:
                self.queue.put(("log", out.strip()))
            if err:
                self.queue.put(("log", err.strip()))
            if code == 0:
                self.queue.put(("log", f"✅ Backup concluído: {job.name}"))
                self.queue.put(("status", "Backup concluído ✅"))
            else:
                self.queue.put(("log", f"❌ Backup falhou (code={code}): {job.name}"))
                self.queue.put(("status", "Backup falhou ❌"))

        threading.Thread(target=worker, daemon=True).start()

    def _open_logs_folder(self) -> None:
        ensure_dirs()
        xdg_open(str(CACHE_DIR))


def run_job_from_cli(job_id: str) -> int:
    store = ConfigStore(CONFIG_FILE)
    store.load()
    jobs = {j.id: j for j in store.jobs()}
    job = jobs.get(job_id)
    if not job:
        print(f"Job não encontrado: {job_id}", file=sys.stderr)
        return 2
    ensure_dirs()
    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] Rodando job: {job.name}")
    code, out, err = rclone_sync(job.local_path, job.remote_spec(), extra_args=["--stats", "1m"])
    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)
    return code


def main(argv: List[str]) -> int:
    if "--run-job" in argv:
        i = argv.index("--run-job")
        if i + 1 >= len(argv):
            print("Uso: --run-job <job_id>", file=sys.stderr)
            return 2
        return run_job_from_cli(argv[i + 1])

    store = ConfigStore(CONFIG_FILE)
    store.load()
    app = CloudBackupGUI(store)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

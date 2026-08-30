#!/usr/bin/env python3
"""Modo seguro inicial do SlackUpdate: somente leitura de pacotes locais."""

import gi
import subprocess
import threading
from pathlib import Path

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk


APP_NAME = "SlackUpdate — Protótipo"
PACKAGE_DATABASE = Path("/var/log/packages")
SAMPLE_PACKAGES = [
    (True, "openssl", "1.1.1w-x86_64-1", "1.1.1w-x86_64-2_slack15.0", "Segurança", "4,2 MB"),
    (True, "mozilla-firefox", "128.12.0esr-x86_64-1", "128.13.0esr-x86_64-1", "Aplicativo", "76,8 MB"),
    (True, "kernel-firmware", "20240709-noarch-1", "20250613-noarch-1", "Sistema", "98,1 MB"),
    (False, "git", "2.46.0-x86_64-1", "2.47.1-x86_64-1", "Aplicativo", "7,5 MB"),
]


class SlackUpdate(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.slackware.SlackUpdatePrototype")
        self.window = None
        self.store = Gtk.ListStore(bool, str, str, str, str, str)

    def do_activate(self):
        if self.window:
            self.window.present()
            return

        self.window = Gtk.ApplicationWindow(application=self, title=APP_NAME)
        self.window.set_default_size(980, 620)
        self.window.set_border_width(16)
        self.window.connect("delete-event", lambda *_: False)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.window.add(root)

        header = Gtk.Box(spacing=12)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        title = Gtk.Label()
        title.set_markup("<span size='xx-large' weight='bold'>Atualizações disponíveis</span>")
        title.set_halign(Gtk.Align.START)
        subtitle = Gtk.Label(label="Modo seguro: somente leitura. Nenhuma alteração será feita no sistema.")
        subtitle.get_style_context().add_class("dim-label")
        subtitle.set_halign(Gtk.Align.START)
        title_box.pack_start(title, False, False, 0)
        title_box.pack_start(subtitle, False, False, 0)
        header.pack_start(title_box, True, True, 0)
        check_button = Gtk.Button(label="Ler pacotes instalados")
        check_button.connect("clicked", self.on_read_installed_packages)
        header.pack_end(check_button, False, False, 0)
        online_button = Gtk.Button(label="Consultar atualizações on-line")
        online_button.set_tooltip_text("Atualiza apenas os metadados assinados e lista atualizações; não instala pacotes.")
        online_button.connect("clicked", self.on_online_check)
        header.pack_end(online_button, False, False, 0)
        root.pack_start(header, False, False, 0)

        notice = Gtk.InfoBar()
        notice.set_message_type(Gtk.MessageType.INFO)
        notice.get_content_area().add(Gtk.Label(label="Modo seguro ativo: lê apenas /var/log/packages. Consultas online e instalações estão desativadas."))
        root.pack_start(notice, False, False, 0)

        pane = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        pane.set_position(700)
        root.pack_start(pane, True, True, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        tree = self.make_tree()
        scroll.add(tree)
        pane.pack1(scroll, resize=True, shrink=False)

        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=12)
        detail_title = Gtk.Label()
        detail_title.set_markup("<b>Detalhes da atualização</b>")
        detail_title.set_halign(Gtk.Align.START)
        details.pack_start(detail_title, False, False, 0)
        self.detail_label = Gtk.Label(label="Selecione um pacote para ver as informações.")
        self.detail_label.set_halign(Gtk.Align.START)
        self.detail_label.set_valign(Gtk.Align.START)
        self.detail_label.set_line_wrap(True)
        details.pack_start(self.detail_label, False, False, 0)
        pane.pack2(details, resize=False, shrink=False)
        tree.get_selection().connect("changed", self.on_selection_changed)

        updates_frame = Gtk.Frame(label="Pacotes com atualizações (consulta on-line)")
        self.updates_view = Gtk.TextView()
        self.updates_view.set_editable(False)
        self.updates_view.set_cursor_visible(False)
        self.updates_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.updates_view.get_buffer().set_text(
            "Ainda não consultado. Clique em “Consultar atualizações on-line”.\n\n"
            "A consulta atualiza apenas a base de metadados do slackpkg e lista candidatos; "
            "ela não baixa nem instala pacotes."
        )
        updates_scroll = Gtk.ScrolledWindow()
        updates_scroll.set_size_request(-1, 155)
        updates_scroll.add(self.updates_view)
        updates_frame.add(updates_scroll)
        root.pack_start(updates_frame, False, False, 0)

        footer = Gtk.Box(spacing=10)
        self.status = Gtk.Label(label="3 atualizações selecionadas — 179,1 MB para baixar")
        self.status.set_halign(Gtk.Align.START)
        footer.pack_start(self.status, True, True, 0)
        cleanup_button = Gtk.Button(label="Limpar atualizações antigas")
        cleanup_button.set_tooltip_text("Remove somente arquivos de pacotes já baixados; nunca pacotes instalados.")
        cleanup_button.connect("clicked", self.on_cleanup_old_updates)
        footer.pack_end(cleanup_button, False, False, 0)
        self.update_button = Gtk.Button(label="Atualizar selecionados")
        self.update_button.get_style_context().add_class("suggested-action")
        self.update_button.connect("clicked", self.on_update_selected)
        footer.pack_end(self.update_button, False, False, 0)
        root.pack_end(footer, False, False, 0)

        self.window.show_all()

    def make_tree(self):
        for package in SAMPLE_PACKAGES:
            self.store.append(package)
        tree = Gtk.TreeView(model=self.store)
        tree.set_headers_visible(True)
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_toggled)
        tree.append_column(Gtk.TreeViewColumn("Atualizar", renderer_toggle, active=0))
        for index, name in enumerate(("Pacote", "Instalado", "Nova versão", "Tipo", "Download"), start=1):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(name, renderer, text=index)
            column.set_resizable(True)
            tree.append_column(column)
        return tree

    @staticmethod
    def package_name_from_record(record_name):
        """Extrai o nome de um registro Slackware sem abrir nem alterar arquivos."""
        parts = record_name.rsplit("-", 3)
        return parts[0] if len(parts) == 4 else record_name

    def on_read_installed_packages(self, _button):
        if not PACKAGE_DATABASE.is_dir():
            self.status.set_text("Base de pacotes não encontrada: {}".format(PACKAGE_DATABASE))
            return

        try:
            records = sorted(path.name for path in PACKAGE_DATABASE.iterdir() if path.is_file())
        except OSError as error:
            self.status.set_text("Não foi possível ler a base de pacotes: {}".format(error))
            return

        self.store.clear()
        for record in records:
            self.store.append((False, self.package_name_from_record(record), record, "—", "Instalado", "—"))
        self.detail_label.set_text(
            "Lista lida de {}. Selecione um pacote para ver o registro local.".format(PACKAGE_DATABASE)
        )
        self.status.set_text("Modo seguro: {} pacote(s) instalado(s) lido(s). Nenhuma consulta à internet foi feita.".format(len(records)))

    def on_online_check(self, _button):
        self.status.set_text("Consultando o mirror e preparando a lista de atualizações…")
        self.updates_view.get_buffer().set_text("Consulta em andamento. A autenticação do sistema poderá ser solicitada.")
        threading.Thread(target=self.run_online_check, daemon=True).start()

    def run_online_check(self):
        """Atualiza somente metadados e lista upgrades com resposta obrigatória 'não'."""
        update_command = ["pkexec", "/usr/sbin/slackpkg", "update"]
        list_command = [
            "pkexec", "/usr/sbin/slackpkg", "-batch=on", "-default_answer=n",
            "-download_all=off", "-dialog=off", "upgrade-all",
        ]
        try:
            metadata = subprocess.run(update_command, text=True, capture_output=True, timeout=300)
            if metadata.returncode != 0:
                output = (metadata.stdout + "\n" + metadata.stderr).strip()
                GLib.idle_add(self.show_online_result, "Não foi possível atualizar os metadados:\n\n" + output, False)
                return
            result = subprocess.run(list_command, text=True, capture_output=True, timeout=180)
            output = (result.stdout + "\n" + result.stderr).strip()
            if result.returncode not in (0, 20):
                GLib.idle_add(self.show_online_result, "Não foi possível listar atualizações:\n\n" + output, False)
                return
            if not output:
                output = "Nenhuma atualização foi informada pelo slackpkg."
            GLib.idle_add(self.show_online_result, output, True)
        except subprocess.TimeoutExpired:
            GLib.idle_add(self.show_online_result, "A consulta excedeu o tempo limite. Nenhum pacote foi instalado.", False)
        except OSError as error:
            GLib.idle_add(self.show_online_result, "Erro ao iniciar a consulta: {}".format(error), False)

    def show_online_result(self, text, success):
        self.updates_view.get_buffer().set_text(text)
        if success:
            self.status.set_text("Consulta concluída. A lista acima é somente informativa; nenhuma atualização foi instalada.")
        else:
            self.status.set_text("Consulta não concluída. Nenhum pacote foi instalado.")
        return False

    def on_toggled(self, _renderer, path):
        row = self.store[path]
        row[0] = not row[0]
        self.refresh_status()

    def on_selection_changed(self, selection):
        model, tree_iter = selection.get_selected()
        if tree_iter is None:
            return
        package = model[tree_iter]
        self.detail_label.set_markup(
            "<b>{}</b>\n\n{} → {}\n\nCategoria: {}\nDownload: {}\n\n"
            "No produto final, esta área mostrará o changelog e a origem oficial do pacote."
            .format(package[1], package[2], package[3], package[4], package[5])
        )

    def refresh_status(self):
        count = sum(row[0] for row in self.store)
        self.status.set_text("{} atualização(ões) selecionada(s) — protótipo sem instalação".format(count))

    def on_update_selected(self, _button):
        selected = sum(row[0] for row in self.store)
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Simulação concluída",
        )
        dialog.format_secondary_text(
            "{} pacote(s) seriam atualizados. No modo seguro, nenhum comando foi executado e nada foi alterado.".format(selected)
        )
        dialog.run()
        dialog.destroy()

    def on_cleanup_old_updates(self, _button):
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text="Limpar arquivos de atualizações antigas?",
        )
        dialog.format_secondary_text(
            "No produto final, esta ação limpará apenas pacotes baixados em cache. "
            "Ela nunca remove programas ou componentes instalados do Slackware.\n\n"
            "Neste protótipo, a limpeza é apenas simulada."
        )
        dialog.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialog.add_button("Simular limpeza", Gtk.ResponseType.OK)
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            self.status.set_text("Limpeza simulada concluída — 182,4 MB seriam liberados.")


if __name__ == "__main__":
    SlackUpdate().run(None)

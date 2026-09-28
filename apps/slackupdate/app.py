#!/usr/bin/env python3
"""Modo seguro inicial do SlackUpdate: somente leitura de pacotes locais."""

import gi
import re
import subprocess
import threading
from urllib.error import URLError
from urllib.request import urlopen
from pathlib import Path
from file_inspection import default_roots, scan_files, cleanup_identity, trash_selected

gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk


APP_NAME = "SlackUpdate — Protótipo"
DEVELOPER_CREDIT = "Desenvolvido por JONAS DE OLIVEIRA SALVIANO • VibeCoding"
PACKAGE_DATABASE = Path("/var/log/packages")
SLACKWARE_VERSION_FILE = Path("/etc/slackware-version")
SLACKWARE_RELEASE_INDEX = "https://mirrors.slackware.com/slackware/"
PACKAGE_EXTENSIONS = (".tgz", ".tbz", ".tlz", ".txz")
PACKAGE_ARCHITECTURES = re.compile(r"^(?:x86_64|i[3-6]86|noarch|fw)$")


class SlackUpdate(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.slackware.SlackUpdatePrototype")
        self.window = None
        self.inspection_window = None
        self.store = Gtk.ListStore(bool, str, str, str, str, str)

    def do_activate(self):
        if self.window:
            self.window.present()
            return

        self.window = Gtk.ApplicationWindow(application=self, title=APP_NAME)
        self.window.set_default_size(980, 760)
        self.window.set_border_width(16)
        self.window.connect("delete-event", lambda *_: False)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.window.add(root)

        header = Gtk.Box(spacing=12)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        title = Gtk.Label()
        title.set_markup("<span size='xx-large' weight='bold'>Slackware™ Update</span>")
        title.set_halign(Gtk.Align.START)
        subtitle = Gtk.Label(label="Atualizador não oficial • modo seguro, sem alterações automáticas.")
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
        notice.get_content_area().add(Gtk.Label(label="Modo seguro ativo: a consulta on-line só atualiza metadados e nunca instala, remove ou baixa pacotes."))
        root.pack_start(notice, False, False, 0)

        overview = Gtk.Box(spacing=14)
        overview.pack_start(self.make_kernel_panel(), True, True, 0)
        overview.pack_start(self.make_release_panel(), True, True, 0)
        root.pack_start(overview, False, False, 0)

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
        footer_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.status = Gtk.Label(label="Nenhuma consulta realizada.")
        self.status.set_halign(Gtk.Align.START)
        footer_left.pack_start(self.status, False, False, 0)
        credit = Gtk.Label(label=DEVELOPER_CREDIT)
        credit.set_halign(Gtk.Align.START)
        credit.get_style_context().add_class("dim-label")
        footer_left.pack_start(credit, False, False, 0)
        footer.pack_start(footer_left, True, True, 0)
        cleanup_button = Gtk.Button(label="Verificar arquivos")
        cleanup_button.set_image(Gtk.Image.new_from_icon_name("system-search-symbolic", Gtk.IconSize.BUTTON))
        cleanup_button.set_tooltip_text("Consultar temporários, cache e pacotes baixados")
        cleanup_button.connect("clicked", self.on_cleanup_old_updates)
        footer.pack_end(cleanup_button, False, False, 0)
        self.update_button = Gtk.Button(label="Instalação desativada")
        self.update_button.get_style_context().add_class("suggested-action")
        self.update_button.set_sensitive(False)
        self.update_button.set_tooltip_text("A instalação será habilitada somente após a validação do modo seguro.")
        footer.pack_end(self.update_button, False, False, 0)
        root.pack_end(footer, False, False, 0)

        self.window.show_all()

    def make_kernel_panel(self):
        frame = Gtk.Frame(label="Kernel (opcional)")
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, margin=10)
        self.kernel_opt_in = Gtk.CheckButton(label="Incluir atualizações de kernel na instalação")
        self.kernel_opt_in.set_active(False)
        self.kernel_opt_in.connect("toggled", self.on_kernel_opt_in_changed)
        content.pack_start(self.kernel_opt_in, False, False, 0)
        self.kernel_label = Gtk.Label()
        self.kernel_label.set_halign(Gtk.Align.START)
        self.kernel_label.set_line_wrap(True)
        content.pack_start(self.kernel_label, False, False, 0)
        frame.add(content)
        self.refresh_installed_kernel_status()
        return frame

    def make_release_panel(self):
        frame = Gtk.Frame(label="Nova versão do Slackware")
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, margin=10)
        self.release_label = Gtk.Label(label=self.get_installed_slackware_version())
        self.release_label.set_halign(Gtk.Align.START)
        self.release_label.set_line_wrap(True)
        content.pack_start(self.release_label, False, False, 0)
        release_button = Gtk.Button(label="Verificar nova versão")
        release_button.connect("clicked", self.on_check_release)
        content.pack_start(release_button, False, False, 0)
        frame.add(content)
        return frame

    def make_tree(self):
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

    @staticmethod
    def parse_package_identifier(identifier):
        """Retorna nome, versão, arquitetura, build e registro de um pacote Slackware."""
        package = Path(identifier.strip()).name
        for extension in PACKAGE_EXTENSIONS:
            if package.endswith(extension):
                package = package[:-len(extension)]
                break
        parts = package.rsplit("-", 3)
        if len(parts) != 4 or not parts[0] or not PACKAGE_ARCHITECTURES.match(parts[2]):
            return None
        return {
            "name": parts[0],
            "version": parts[1],
            "arch": parts[2],
            "build": parts[3],
            "record": package,
        }

    @classmethod
    def parse_upgrade_candidates(cls, output):
        """Extrai somente identificadores de pacote das linhas do slackpkg."""
        candidates = {}
        for line in output.splitlines():
            value = line.strip()
            if not value or any(character.isspace() for character in value):
                continue
            package = cls.parse_package_identifier(value)
            if package:
                candidates[package["name"]] = package
        return [candidates[name] for name in sorted(candidates)]

    @classmethod
    def installed_package_map(cls):
        packages = {}
        if not PACKAGE_DATABASE.is_dir():
            return packages
        try:
            records = (path.name for path in PACKAGE_DATABASE.iterdir() if path.is_file())
            for record in records:
                package = cls.parse_package_identifier(record)
                if package:
                    packages.setdefault(package["name"], []).append(package["record"])
        except OSError:
            return {}
        return packages

    @staticmethod
    def installed_records_matching(prefix):
        if not PACKAGE_DATABASE.is_dir():
            return []
        try:
            return sorted(path.name for path in PACKAGE_DATABASE.iterdir() if path.is_file() and path.name.startswith(prefix))
        except OSError:
            return []

    def refresh_installed_kernel_status(self):
        kernels = self.installed_records_matching("kernel-")
        if kernels:
            self.kernel_label.set_text("Kernel(es) instalado(s): " + ", ".join(kernels))
        else:
            self.kernel_label.set_text("Nenhum registro de kernel encontrado em /var/log/packages.")

    @staticmethod
    def get_installed_slackware_version():
        try:
            return "Sistema instalado: " + SLACKWARE_VERSION_FILE.read_text(encoding="utf-8").strip()
        except OSError:
            return "Não foi possível identificar a versão instalada do Slackware."

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
        self.refresh_installed_kernel_status()

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
            candidates = self.populate_update_table(text)
            self.show_kernel_candidates(candidates)
            if candidates:
                self.status.set_text(
                    "Consulta concluída: {} atualização(ões) encontrada(s). Nenhuma foi instalada.".format(len(candidates))
                )
            else:
                self.status.set_text("Consulta concluída: nenhuma atualização de pacote foi encontrada.")
        else:
            self.status.set_text("Consulta não concluída. Nenhum pacote foi instalado.")
        return False

    def populate_update_table(self, output):
        candidates = self.parse_upgrade_candidates(output)
        installed = self.installed_package_map()
        self.store.clear()
        for package in candidates:
            is_kernel = package["name"].startswith("kernel-")
            category = "Kernel" if is_kernel else ("Segurança" if "_slack" in package["build"] else "Sistema")
            current = ", ".join(installed.get(package["name"], ["Não identificado"]))
            selected = False if is_kernel else True
            self.store.append((selected, package["name"], current, package["record"], category, "Não informado"))
        return candidates

    def show_kernel_candidates(self, candidates):
        kernel_candidates = [package["record"] for package in candidates if package["name"].startswith("kernel-")]
        if kernel_candidates:
            self.kernel_label.set_text("Atualizações opcionais encontradas: " + ", ".join(kernel_candidates))
        else:
            self.refresh_installed_kernel_status()

    def on_kernel_opt_in_changed(self, button):
        if button.get_active():
            self.status.set_text("Kernel marcado como opcional. Ele só será considerado quando a instalação real for implementada.")
        else:
            self.status.set_text("Kernel desmarcado. Atualizações de kernel permanecerão fora da instalação.")

    def on_check_release(self, _button):
        self.release_label.set_text("Verificando no mirror oficial…")
        threading.Thread(target=self.run_release_check, daemon=True).start()

    def run_release_check(self):
        try:
            with urlopen(SLACKWARE_RELEASE_INDEX, timeout=30) as response:
                index = response.read().decode("utf-8", errors="replace")
            versions = re.findall(r"slackware(?:64)?-([0-9]+(?:\.[0-9]+)+)/", index)
            if not versions:
                raise ValueError("Nenhuma versão estável foi identificada na resposta do mirror.")
            newest = max(versions, key=lambda value: tuple(int(part) for part in value.split(".")))
            message = "Última versão estável encontrada no mirror: Slackware {}. Nenhum upgrade foi iniciado.".format(newest)
        except (OSError, URLError, ValueError) as error:
            message = "Não foi possível verificar a versão mais recente: {}".format(error)
        GLib.idle_add(self.show_release_result, message)

    def show_release_result(self, message):
        self.release_label.set_text(message)
        return False

    def on_toggled(self, _renderer, path):
        row = self.store[path]
        if row[4] == "Kernel" and not self.kernel_opt_in.get_active():
            self.status.set_text("Para selecionar um kernel, marque primeiro a opção “Incluir atualizações de kernel”.")
            return
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

    def on_cleanup_old_updates(self, _button):
        if self.inspection_window is not None:
            self.inspection_window.present()
            return
        window = Gtk.ApplicationWindow(application=self, title="SlackUpdate - Arquivos temporários e pacotes")
        self.inspection_window = window
        window.set_transient_for(self.window)
        window.set_destroy_with_parent(True)
        window.set_default_size(940, 540)
        window.connect("destroy", self.on_inspection_destroy)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=12)
        window.add(box)
        toolbar = Gtk.Box(spacing=10)
        refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        refresh.set_tooltip_text("Consultar arquivos novamente")
        toolbar.pack_start(refresh, False, False, 0)
        delete = Gtk.Button(label="Excluir selecionados")
        delete.set_image(Gtk.Image.new_from_icon_name("user-trash-symbolic", Gtk.IconSize.BUTTON))
        delete.set_sensitive(False)
        toolbar.pack_end(delete, False, False, 0)
        summary = Gtk.Label(label="Consultando arquivos...")
        summary.set_line_wrap(True)
        summary.set_xalign(0)
        toolbar.pack_start(summary, True, True, 0)
        box.pack_start(toolbar, False, False, 0)
        store = Gtk.ListStore(str, str, str, str, str, bool, bool)
        identities = {}
        roots = default_roots()
        tree = Gtk.TreeView(model=store)
        toggle = Gtk.CellRendererToggle()
        tree.append_column(Gtk.TreeViewColumn("", toggle, active=5, activatable=6, sensitive=6))

        def toggled(_renderer, path):
            if store[path][6]:
                store[path][5] = not store[path][5]
            delete.set_sensitive(any(row[5] for row in store))

        toggle.connect("toggled", toggled)
        for index, title in enumerate(("Arquivo", "Categoria", "Tamanho", "Idade", "Situação")):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=index)
            column.set_resizable(True)
            tree.append_column(column)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(tree)
        box.pack_start(scroll, True, True, 0)
        details = Gtk.Label()
        details.set_xalign(0)
        details.set_line_wrap(True)
        details.set_selectable(True)
        box.pack_start(details, False, False, 0)

        def refresh_files(_button=None, report=""):
            refresh.set_sensitive(False)
            delete.set_sensitive(False)
            tree.set_sensitive(False)
            identities.clear()
            summary.set_text("Consultando arquivos...")
            details.set_text("")
            store.clear()

            def finish(rows, warnings, snapshots):
                if self.inspection_window is not window:
                    return False
                for path, category, size, days, status in rows:
                    store.append((path, category, GLib.format_size(size), "{} dias".format(days), status, False, path in snapshots))
                identities.update(snapshots)
                summary.set_text("{} arquivos | {}".format(
                    len(rows), GLib.format_size(sum(row[2] for row in rows))))
                details.set_text("\n".join(filter(None, [report, *warnings[:3]])))
                refresh.set_sensitive(True)
                tree.set_sensitive(True)
                return False

            def work():
                snapshots = {}
                try:
                    rows, warnings = scan_files(roots, self.installed_package_map(), self.parse_package_identifier)
                    for path, category, _size, _days, _status in rows:
                        if category != "Pacote baixado":
                            try:
                                snapshots[path] = cleanup_identity(path, roots)
                            except (OSError, ValueError):
                                pass
                except Exception as error:
                    rows, warnings = [], ["Consulta não concluída: {}".format(error)]
                GLib.idle_add(finish, rows, warnings, snapshots)

            threading.Thread(target=work, daemon=True).start()

        def delete_files(_button):
            items = [(row[0], identities[row[0]]) for row in store if row[5] and row[6]]
            if not items:
                return
            dialog = Gtk.MessageDialog(transient_for=window, modal=True,
                message_type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.CANCEL,
                text="Mover {} arquivos para a lixeira?".format(len(items)))
            dialog.format_secondary_text(
                "Feche os aplicativos e navegadores antes de continuar. Arquivos temporários podem estar em uso.\n\n"
                + "\n".join(path for path, _identity in items[:8])
                + ("\n..." if len(items) > 8 else ""))
            dialog.add_button("Mover para a lixeira", Gtk.ResponseType.OK)
            response = dialog.run()
            dialog.destroy()
            if response != Gtk.ResponseType.OK:
                return
            delete.set_sensitive(False)
            refresh.set_sensitive(False)
            tree.set_sensitive(False)
            summary.set_text("Movendo arquivos para a lixeira...")

            def trash(path):
                try:
                    return Gio.File.new_for_path(path).trash(None)
                except GLib.Error as error:
                    raise RuntimeError(error.message) from error

            def finish_delete(completed, errors):
                if self.inspection_window is window:
                    report = "{} enviados à lixeira; {} falhas.".format(len(completed), len(errors))
                    refresh_files(report="\n".join([report, *errors[:3]]))
                return False

            def work_delete():
                completed, errors = trash_selected(items, roots, trash)
                GLib.idle_add(finish_delete, completed, errors)

            threading.Thread(target=work_delete, daemon=True).start()

        delete.connect("clicked", delete_files)

        refresh.connect("clicked", refresh_files)
        window.show_all()
        refresh_files()

    def on_inspection_destroy(self, _window):
        self.inspection_window = None


if __name__ == "__main__":
    SlackUpdate().run(None)

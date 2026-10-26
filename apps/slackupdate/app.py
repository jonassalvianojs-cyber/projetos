#!/usr/bin/env python3
"""Interface gráfica para consultar e instalar atualizações no Slackware."""

from datetime import datetime
import gi
import re
import subprocess
import threading
from urllib.error import URLError
from urllib.request import urlopen
from pathlib import Path

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk


APP_NAME = "SlackUpdate"
DEVELOPER_CREDIT = "Desenvolvido por JONAS DE OLIVEIRA SALVIANO • VibeCoding"
PACKAGE_DATABASE = Path("/var/log/packages")
PACKAGE_CACHE = Path("/var/cache/packages")
SLACKWARE_VERSION_FILE = Path("/etc/slackware-version")
SLACKWARE_RELEASE_INDEX = "https://mirrors.slackware.com/slackware/"
SLACKPKG = Path("/usr/sbin/slackpkg")
STATE_DIRECTORY = Path.home() / ".local" / "state" / "slackupdate"
LOG_FILE = STATE_DIRECTORY / "history.log"
PACKAGE_EXTENSIONS = (".tgz", ".tbz", ".tlz", ".txz")
PACKAGE_ARCHITECTURES = re.compile(r"^(?:x86_64|i[3-6]86|noarch|fw)$")


class SlackUpdate(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.vibecoding.SlackUpdate")
        self.window = None
        self.store = Gtk.ListStore(bool, str, str, str, str, str)
        self.has_update_results = False
        self.busy = False

    def do_activate(self):
        if self.window:
            self.window.present()
            return

        self.window = Gtk.ApplicationWindow(application=self, title=APP_NAME)
        self.window.set_icon_name("slackupdate")
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
        subtitle = Gtk.Label(label="Atualizador não oficial • alterações somente após confirmação.")
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
        notice.get_content_area().add(Gtk.Label(label="A consulta não instala nada. A instalação exige seleção, confirmação e autenticação administrativa."))
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
        cleanup_button = Gtk.Button(label="Limpar atualizações antigas")
        cleanup_button.set_tooltip_text("Remove somente arquivos de pacotes já baixados; nunca pacotes instalados.")
        cleanup_button.connect("clicked", self.on_cleanup_old_updates)
        footer.pack_end(cleanup_button, False, False, 0)
        self.update_button = Gtk.Button(label="Instalação desativada")
        self.update_button.get_style_context().add_class("suggested-action")
        self.update_button.set_sensitive(False)
        self.update_button.set_tooltip_text("Consulte as atualizações para habilitar a instalação selecionada.")
        self.update_button.connect("clicked", self.on_install_selected)
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
        self.has_update_results = False
        for record in records:
            self.store.append((False, self.package_name_from_record(record), record, "—", "Instalado", "—"))
        self.detail_label.set_text(
            "Lista lida de {}. Selecione um pacote para ver o registro local.".format(PACKAGE_DATABASE)
        )
        self.status.set_text("Modo seguro: {} pacote(s) instalado(s) lido(s). Nenhuma consulta à internet foi feita.".format(len(records)))
        self.refresh_installed_kernel_status()
        self.refresh_install_button()

    def on_online_check(self, _button):
        if self.busy:
            return
        if not SLACKPKG.is_file():
            self.show_error("slackpkg não encontrado", "O executável /usr/sbin/slackpkg não está disponível.")
            return
        self.busy = True
        self.refresh_install_button()
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
        self.busy = False
        self.updates_view.get_buffer().set_text(text)
        if success:
            candidates = self.populate_update_table(text)
            self.has_update_results = bool(candidates)
            self.show_kernel_candidates(candidates)
            if candidates:
                self.status.set_text(
                    "Consulta concluída: {} atualização(ões) encontrada(s). Nenhuma foi instalada.".format(len(candidates))
                )
            else:
                self.status.set_text("Consulta concluída: nenhuma atualização de pacote foi encontrada.")
        else:
            self.has_update_results = False
            self.status.set_text("Consulta não concluída. Nenhum pacote foi instalado.")
        self.refresh_install_button()
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
            self.status.set_text("Kernel liberado para seleção manual. Ele continua desmarcado por padrão.")
        else:
            for row in self.store:
                if row[4] == "Kernel":
                    row[0] = False
            self.status.set_text("Kernel desmarcado. Atualizações de kernel permanecerão fora da instalação.")
        self.refresh_install_button()

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
        self.status.set_text("{} atualização(ões) selecionada(s).".format(count))
        self.refresh_install_button()

    def refresh_install_button(self):
        selected = sum(row[0] for row in self.store) if self.has_update_results else 0
        enabled = self.has_update_results and selected > 0 and not self.busy
        self.update_button.set_sensitive(enabled)
        self.update_button.set_label("Instalar selecionados ({})".format(selected) if enabled else "Instalação desativada")

    def selected_package_names(self):
        return [row[1] for row in self.store if row[0]]

    def on_install_selected(self, _button):
        packages = self.selected_package_names()
        if not packages or self.busy:
            return
        kernel_selected = any(name.startswith("kernel-") for name in packages)
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text="Instalar {} atualização(ões)?".format(len(packages)),
        )
        warning = "Os seguintes pacotes serão atualizados:\n\n{}".format("\n".join(packages))
        if kernel_selected:
            warning += "\n\nATENÇÃO: há pacotes de kernel selecionados. Confirme seu carregador de inicialização após a atualização."
        warning += "\n\nA senha administrativa será solicitada. Não desligue o computador durante a operação."
        dialog.format_secondary_text(warning)
        dialog.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialog.add_button("Instalar", Gtk.ResponseType.OK)
        response = dialog.run()
        dialog.destroy()
        if response != Gtk.ResponseType.OK:
            return
        self.busy = True
        self.refresh_install_button()
        self.status.set_text("Instalando atualizações selecionadas…")
        self.updates_view.get_buffer().set_text("Instalação em andamento. Aguarde a conclusão do slackpkg.")
        threading.Thread(target=self.run_install_selected, args=(packages,), daemon=True).start()

    def run_install_selected(self, packages):
        command = [
            "pkexec", str(SLACKPKG), "-batch=on", "-default_answer=y",
            "-download_all=off", "-dialog=off", "upgrade",
        ] + packages
        try:
            result = subprocess.run(command, text=True, capture_output=True, timeout=1800)
            output = (result.stdout + "\n" + result.stderr).strip()
            success = result.returncode == 0
            self.write_log("upgrade", packages, result.returncode, output)
            GLib.idle_add(self.show_install_result, output, success)
        except subprocess.TimeoutExpired as error:
            output = "A instalação excedeu o limite de tempo. Verifique o sistema antes de tentar novamente."
            self.write_log("upgrade", packages, 124, output)
            GLib.idle_add(self.show_install_result, output, False)
        except OSError as error:
            output = "Não foi possível iniciar a instalação: {}".format(error)
            self.write_log("upgrade", packages, 1, output)
            GLib.idle_add(self.show_install_result, output, False)

    def show_install_result(self, output, success):
        self.busy = False
        self.has_update_results = False
        self.updates_view.get_buffer().set_text(output or "Operação concluída sem saída adicional.")
        self.update_button.set_sensitive(False)
        self.update_button.set_label("Instalação desativada")
        if success:
            self.status.set_text("Atualizações instaladas. Faça uma nova consulta para atualizar a lista.")
            self.show_info("Atualização concluída", "Os pacotes selecionados foram processados pelo slackpkg. Consulte novamente para confirmar o estado.")
        else:
            self.status.set_text("A instalação não foi concluída. Consulte o relatório técnico e o histórico.")
            self.show_error("Falha na atualização", "O slackpkg não concluiu a operação. Nenhuma nova tentativa será feita automaticamente.")
        return False

    @staticmethod
    def write_log(action, packages, return_code, output):
        try:
            STATE_DIRECTORY.mkdir(parents=True, exist_ok=True)
            with LOG_FILE.open("a", encoding="utf-8") as log:
                log.write("\n[{}] action={} return_code={}\n".format(datetime.now().isoformat(timespec="seconds"), action, return_code))
                log.write("packages={}\n".format(",".join(packages)))
                log.write((output or "(sem saída)") + "\n")
        except OSError:
            pass

    def show_info(self, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=self.window, modal=True, message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK, text=title,
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def show_error(self, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=self.window, modal=True, message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK, text=title,
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def on_cleanup_old_updates(self, _button):
        if self.busy:
            return
        if not PACKAGE_CACHE.is_dir():
            self.show_info("Cache vazio", "O diretório /var/cache/packages não foi encontrado.")
            return
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text="Limpar arquivos de atualizações antigas?",
        )
        dialog.format_secondary_text(
            "Esta ação apagará apenas arquivos de pacotes (.txz, .tgz, .tbz e .tlz) guardados em /var/cache/packages. "
            "Ela não remove programas instalados. Os arquivos apagados não poderão ser recuperados por este aplicativo."
        )
        dialog.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialog.add_button("Limpar cache", Gtk.ResponseType.OK)
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            self.busy = True
            self.refresh_install_button()
            self.status.set_text("Limpando arquivos antigos do cache…")
            threading.Thread(target=self.run_cache_cleanup, daemon=True).start()

    def run_cache_cleanup(self):
        command = [
            "pkexec", "/usr/bin/find", str(PACKAGE_CACHE), "-type", "f", "(",
            "-name", "*.txz", "-o", "-name", "*.tgz", "-o", "-name", "*.tbz", "-o", "-name", "*.tlz",
            ")", "-delete",
        ]
        try:
            result = subprocess.run(command, text=True, capture_output=True, timeout=300)
            output = (result.stdout + "\n" + result.stderr).strip()
            self.write_log("clean-cache", [], result.returncode, output)
            GLib.idle_add(self.show_cleanup_result, result.returncode == 0, output)
        except (subprocess.TimeoutExpired, OSError) as error:
            GLib.idle_add(self.show_cleanup_result, False, str(error))

    def show_cleanup_result(self, success, output):
        self.busy = False
        self.refresh_install_button()
        if success:
            self.status.set_text("Cache de pacotes antigos limpo com sucesso.")
        else:
            self.status.set_text("Não foi possível limpar o cache: {}".format(output or "erro desconhecido"))
        return False


if __name__ == "__main__":
    SlackUpdate().run(None)

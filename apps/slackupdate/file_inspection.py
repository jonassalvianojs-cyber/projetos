"""Bounded file inspection and validation for user-requested cleanup."""

import os
import stat
import time
from pathlib import Path


def scan_files(roots, installed, parse_package, limit=10000):
    rows = []
    warnings = []
    visited = set()
    inspected = 0
    now = time.time()
    for root, category, only_owned in roots:
        root = Path(root)
        if root.is_symlink() or not root.exists():
            continue
        pending = [root]
        while pending:
            directory = pending.pop()
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        inspected += 1
                        if inspected > limit:
                            warnings.append("Limite de consulta atingido; resultado parcial.")
                            return rows, warnings
                        if entry.is_symlink():
                            continue
                        info = entry.stat(follow_symlinks=False)
                        if only_owned and info.st_uid != os.getuid():
                            continue
                        if stat.S_ISDIR(info.st_mode):
                            pending.append(Path(entry.path))
                            continue
                        if not stat.S_ISREG(info.st_mode):
                            continue
                        identity = (info.st_dev, info.st_ino)
                        if identity in visited:
                            continue
                        visited.add(identity)
                        package = None
                        if entry.name.endswith((".tgz", ".tbz", ".tlz", ".txz")):
                            package = parse_package(entry.name)
                        if category == "Pacote baixado" and not package:
                            continue
                        status = "Idade não indica que pode ser excluído"
                        kind = category
                        if category == "Cache de aplicativo" and any(
                            name in ("google-chrome", "chromium", "mozilla", "BraveSoftware", "microsoft-edge")
                            for name in Path(entry.path).relative_to(root).parts[:-1]
                        ):
                            kind = "Cache de navegador"
                        if package:
                            kind = "Pacote baixado"
                            records = installed.get(package["name"], [])
                            if package["record"] in records:
                                status = "Mesma versão instalada"
                            elif records:
                                status = "Versão diferente da instalada; revisar"
                            else:
                                status = "Sem registro instalado correspondente"
                        days = max(0, int((now - info.st_mtime) / 86400))
                        rows.append((entry.path, kind, info.st_size, days, status))
            except OSError as error:
                warnings.append("{}: {}".format(directory, error.strerror))
    return rows, warnings


def cleanup_identity(path, roots):
    path = Path(path)
    allowed = any(
        category != "Pacote baixado" and Path(root) in path.parents
        for root, category, _owned in roots
    )
    if not allowed or any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError("Arquivo fora das pastas permitidas ou contém link simbólico")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError("Arquivo não pertence ao usuário ou não é regular")
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def trash_selected(items, roots, trash):
    completed, errors = [], []
    for path, expected in items:
        try:
            if cleanup_identity(path, roots) != expected:
                raise ValueError("Arquivo alterado desde a consulta; consulte novamente")
            if not trash(path):
                raise ValueError("Não foi possível mover para a lixeira")
            completed.append(path)
        except (OSError, ValueError, RuntimeError) as error:
            errors.append("{}: {}".format(path, error))
    return completed, errors


def default_roots():
    cache = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    if not cache.is_absolute():
        cache = Path.home() / ".cache"
    return [
        (Path("/var/cache/packages"), "Pacote baixado", False),
        (cache, "Cache de aplicativo", True),
        (Path("/tmp"), "Temporário", True),
        (Path("/var/tmp"), "Temporário", True),
    ]

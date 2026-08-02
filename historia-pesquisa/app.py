#!/usr/bin/env python3
"""Clio — Laboratório de Pesquisa em História."""

import json
import os
import re
import sqlite3
import subprocess
import threading
import webbrowser
from datetime import datetime
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
DB_PATH = DATA_DIR / "pesquisa.db"
PORT = 8765


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def conectar():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with conectar() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projetos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                tema TEXT,
                periodo TEXT,
                descricao TEXT,
                status TEXT DEFAULT 'em_andamento',
                criado_em TEXT,
                atualizado_em TEXT
            );

            CREATE TABLE IF NOT EXISTS fontes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                projeto_id INTEGER,
                tipo TEXT,
                titulo TEXT NOT NULL,
                autores TEXT,
                ano TEXT,
                local TEXT,
                editora TEXT,
                revista TEXT,
                volume TEXT,
                numero TEXT,
                paginas TEXT,
                url TEXT,
                arquivo TEXT,
                citacao TEXT,
                notas_critica TEXT,
                classificacao TEXT,
                consultado_em TEXT,
                tags TEXT,
                criado_em TEXT,
                FOREIGN KEY (projeto_id) REFERENCES projetos(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                projeto_id INTEGER,
                fonte_id INTEGER,
                titulo TEXT,
                conteudo TEXT,
                pagina TEXT,
                tags TEXT,
                criado_em TEXT,
                FOREIGN KEY (projeto_id) REFERENCES projetos(id) ON DELETE CASCADE,
                FOREIGN KEY (fonte_id) REFERENCES fontes(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                projeto_id INTEGER,
                data TEXT,
                titulo TEXT NOT NULL,
                descricao TEXT,
                importancia TEXT DEFAULT 'media',
                fonte_id INTEGER,
                criado_em TEXT,
                FOREIGN KEY (projeto_id) REFERENCES projetos(id) ON DELETE CASCADE,
                FOREIGN KEY (fonte_id) REFERENCES fontes(id) ON DELETE SET NULL
            );
            """
        )


def row_to_dict(row):
    return dict(row) if row else None


def rows_to_list(rows):
    return [dict(r) for r in rows]


def gerar_abnt(fonte):
    autores = (fonte.get("autores") or "").strip()
    titulo = (fonte.get("titulo") or "").strip()
    ano = (fonte.get("ano") or "s.d.").strip()
    local = (fonte.get("local") or "s.l.").strip()
    editora = (fonte.get("editora") or "s.e.").strip()
    revista = (fonte.get("revista") or "").strip()
    volume = (fonte.get("volume") or "").strip()
    numero = (fonte.get("numero") or "").strip()
    paginas = (fonte.get("paginas") or "").strip()
    url = (fonte.get("url") or "").strip()
    consultado = (fonte.get("consultado_em") or "").strip()
    tipo = fonte.get("tipo") or "outro"

    autor_ref = autores or "S.A."

    if tipo == "livro":
        referencia = f"{autor_ref}. **{titulo}**. {local}: {editora}, {ano}."
    elif tipo == "artigo":
        vol = f", v. {volume}" if volume else ""
        num = f", n. {numero}" if numero else ""
        pag = f", p. {paginas}" if paginas else ""
        referencia = (
            f"{autor_ref}. {titulo}. **{revista or 'Periódico'}**"
            f"{vol}{num}{pag}, {ano}."
        )
    elif tipo == "capitulo":
        referencia = (
            f"{autor_ref}. {titulo}. In: "
            f"{fonte.get('citacao') or 'ORGANIZADOR(ES)'}. "
            f"**{fonte.get('arquivo') or 'Título do livro'}**. "
            f"{local}: {editora}, {ano}. p. {paginas or 's.p.'}."
        )
    elif tipo == "tese":
        referencia = (
            f"{autor_ref}. **{titulo}**. {ano}. "
            f"Dissertação (Mestrado em História) — {editora or 'Instituição'}, {local}."
        )
    elif tipo == "arquivo":
        referencia = (
            f"{titulo}. {ano}. Documento. Acervo: {editora or 'Arquivo'}, {local}. "
            f"{'Ref.: ' + paginas if paginas else ''}"
        ).strip()
    elif tipo == "site":
        data_acesso = consultado or datetime.now().strftime("%d %b. %Y")
        referencia = (
            f"{autor_ref or titulo}. **{titulo}**. Disponível em: {url or 's.d.'}. "
            f"Acesso em: {data_acesso}."
        )
    elif tipo == "oral":
        referencia = (
            f"Depoimento de {autores or 'informante'}. {titulo}. "
            f"Entrevista concedida a {fonte.get('citacao') or 'pesquisador'}, "
            f"{local}, {ano}."
        )
    else:
        referencia = f"{autor_ref}. **{titulo}**. {local}, {ano}."

    return re.sub(r"\s+", " ", referencia).strip()


class DuckDuckGoParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resultados = []
        self._em_titulo = False
        self._em_resumo = False
        self._buffer = ""

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        classe = atributos.get("class", "")
        if tag == "a" and "result__a" in classe:
            self._em_titulo = True
            self._buffer = ""
            self.resultados.append(
                {"titulo": "", "url": atributos.get("href", ""), "resumo": ""}
            )
        elif tag == "a" and "result__snippet" in classe:
            self._em_resumo = True
            self._buffer = ""

    def handle_endtag(self, tag):
        if tag == "a" and self._em_titulo:
            self._em_titulo = False
            if self.resultados:
                self.resultados[-1]["titulo"] = self._buffer.strip()
        elif tag == "a" and self._em_resumo:
            self._em_resumo = False
            if self.resultados:
                self.resultados[-1]["resumo"] = self._buffer.strip()

    def handle_data(self, data):
        if self._em_titulo or self._em_resumo:
            self._buffer += data


def pesquisar_internet(termo, limite=12):
    termo = termo.strip()
    if not termo:
        return []

    from urllib.parse import urlencode

    dados = urlencode({"q": termo}).encode("utf-8")
    requisicao = Request(
        "https://html.duckduckgo.com/html/",
        data=dados,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; ClioHistoriador/1.0)",
            "Accept-Language": "pt-BR,pt;q=0.9",
        },
        method="POST",
    )

    try:
        with urlopen(requisicao, timeout=20) as resposta:
            html = resposta.read().decode("utf-8", errors="replace")
    except URLError as erro:
        raise RuntimeError(f"Não foi possível conectar à internet: {erro}") from erro

    parser = DuckDuckGoParser()
    parser.feed(html)

    vistos = set()
    resultados = []
    for item in parser.resultados:
        url = item.get("url", "").strip()
        titulo = item.get("titulo", "").strip()
        if not url or not titulo or url in vistos:
            continue
        vistos.add(url)
        resultados.append(
            {
                "titulo": titulo,
                "url": url,
                "resumo": item.get("resumo", "").strip(),
            }
        )
        if len(resultados) >= limite:
            break

    return resultados


class ClioHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _serve_static(self, rel_path):
        path = (STATIC_DIR / rel_path).resolve()
        if not str(path).startswith(str(STATIC_DIR.resolve())) or not path.is_file():
            self.send_error(404)
            return

        mime = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
        }.get(path.suffix, "application/octet-stream")

        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        qs = parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            return self._serve_static("index.html")
        if path.startswith("/static/"):
            return self._serve_static(path[len("/static/") :])

        if path == "/api/projetos":
            with conectar() as conn:
                rows = conn.execute(
                    "SELECT * FROM projetos ORDER BY atualizado_em DESC, id DESC"
                ).fetchall()
            return self._json_response(rows_to_list(rows))

        if path.startswith("/api/projetos/"):
            pid = path.split("/")[-1]
            if pid.isdigit():
                with conectar() as conn:
                    projeto = conn.execute(
                        "SELECT * FROM projetos WHERE id = ?", (pid,)
                    ).fetchone()
                    if not projeto:
                        return self._json_response({"erro": "Projeto não encontrado"}, 404)
                    fontes = conn.execute(
                        "SELECT * FROM fontes WHERE projeto_id = ? ORDER BY criado_em DESC",
                        (pid,),
                    ).fetchall()
                    notas = conn.execute(
                        "SELECT * FROM notas WHERE projeto_id = ? ORDER BY criado_em DESC",
                        (pid,),
                    ).fetchall()
                    eventos = conn.execute(
                        "SELECT * FROM eventos WHERE projeto_id = ? ORDER BY data ASC",
                        (pid,),
                    ).fetchall()
                return self._json_response(
                    {
                        "projeto": row_to_dict(projeto),
                        "fontes": rows_to_list(fontes),
                        "notas": rows_to_list(notas),
                        "eventos": rows_to_list(eventos),
                    }
                )

        if path == "/api/pesquisa-web":
            termo = qs.get("q", [""])[0].strip()
            if not termo:
                return self._json_response({"erro": "Informe um termo de pesquisa"}, 400)
            try:
                resultados = pesquisar_internet(termo)
            except RuntimeError as erro:
                return self._json_response({"erro": str(erro)}, 502)
            return self._json_response({"termo": termo, "resultados": resultados, "total": len(resultados)})

        if path == "/api/busca":
            termo = qs.get("q", [""])[0].strip()
            projeto_id = qs.get("projeto_id", [None])[0]
            if not termo:
                return self._json_response({"resultados": []})
            like = f"%{termo}%"
            with conectar() as conn:
                fontes_sql = "SELECT 'fonte' as tipo, id, titulo, autores as detalhe, projeto_id FROM fontes WHERE titulo LIKE ? OR autores LIKE ? OR tags LIKE ? OR notas_critica LIKE ?"
                notas_sql = "SELECT 'nota' as tipo, id, titulo, substr(conteudo,1,120) as detalhe, projeto_id FROM notas WHERE titulo LIKE ? OR conteudo LIKE ? OR tags LIKE ?"
                eventos_sql = "SELECT 'evento' as tipo, id, titulo, data as detalhe, projeto_id FROM eventos WHERE titulo LIKE ? OR descricao LIKE ?"
                params_f = [like] * 4
                params_n = [like] * 3
                params_e = [like] * 2
                if projeto_id:
                    fontes_sql += " AND projeto_id = ?"
                    notas_sql += " AND projeto_id = ?"
                    eventos_sql += " AND projeto_id = ?"
                    params_f.append(projeto_id)
                    params_n.append(projeto_id)
                    params_e.append(projeto_id)
                resultados = []
                resultados += rows_to_list(conn.execute(fontes_sql, params_f).fetchall())
                resultados += rows_to_list(conn.execute(notas_sql, params_n).fetchall())
                resultados += rows_to_list(conn.execute(eventos_sql, params_e).fetchall())
            return self._json_response({"resultados": resultados})

        if path == "/api/bibliografia":
            projeto_id = qs.get("projeto_id", [None])[0]
            if not projeto_id:
                return self._json_response({"erro": "projeto_id obrigatório"}, 400)
            with conectar() as conn:
                fontes = conn.execute(
                    "SELECT * FROM fontes WHERE projeto_id = ? ORDER BY autores, titulo",
                    (projeto_id,),
                ).fetchall()
            refs = [gerar_abnt(dict(f)) for f in fontes]
            return self._json_response({"referencias": refs, "total": len(refs)})

        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        data = self._read_json()
        ts = agora()

        with conectar() as conn:
            if path == "/api/projetos":
                cur = conn.execute(
                    """INSERT INTO projetos (titulo, tema, periodo, descricao, status, criado_em, atualizado_em)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        data.get("titulo", "").strip(),
                        data.get("tema", ""),
                        data.get("periodo", ""),
                        data.get("descricao", ""),
                        data.get("status", "em_andamento"),
                        ts,
                        ts,
                    ),
                )
                return self._json_response({"id": cur.lastrowid, "ok": True}, 201)

            if path == "/api/fontes":
                cur = conn.execute(
                    """INSERT INTO fontes
                       (projeto_id, tipo, titulo, autores, ano, local, editora, revista,
                        volume, numero, paginas, url, arquivo, citacao, notas_critica,
                        classificacao, consultado_em, tags, criado_em)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        data.get("projeto_id"),
                        data.get("tipo", "livro"),
                        data.get("titulo", "").strip(),
                        data.get("autores", ""),
                        data.get("ano", ""),
                        data.get("local", ""),
                        data.get("editora", ""),
                        data.get("revista", ""),
                        data.get("volume", ""),
                        data.get("numero", ""),
                        data.get("paginas", ""),
                        data.get("url", ""),
                        data.get("arquivo", ""),
                        data.get("citacao", ""),
                        data.get("notas_critica", ""),
                        data.get("classificacao", "secundaria"),
                        data.get("consultado_em", ""),
                        data.get("tags", ""),
                        ts,
                    ),
                )
                conn.execute(
                    "UPDATE projetos SET atualizado_em = ? WHERE id = ?",
                    (ts, data.get("projeto_id")),
                )
                fonte = dict(
                    conn.execute("SELECT * FROM fontes WHERE id = ?", (cur.lastrowid,)).fetchone()
                )
                return self._json_response(
                    {"id": cur.lastrowid, "abnt": gerar_abnt(fonte), "ok": True}, 201
                )

            if path == "/api/notas":
                cur = conn.execute(
                    """INSERT INTO notas (projeto_id, fonte_id, titulo, conteudo, pagina, tags, criado_em)
                       VALUES (?,?,?,?,?,?,?)""",
                    (
                        data.get("projeto_id"),
                        data.get("fonte_id"),
                        data.get("titulo", "").strip(),
                        data.get("conteudo", ""),
                        data.get("pagina", ""),
                        data.get("tags", ""),
                        ts,
                    ),
                )
                conn.execute(
                    "UPDATE projetos SET atualizado_em = ? WHERE id = ?",
                    (ts, data.get("projeto_id")),
                )
                return self._json_response({"id": cur.lastrowid, "ok": True}, 201)

            if path == "/api/eventos":
                cur = conn.execute(
                    """INSERT INTO eventos
                       (projeto_id, data, titulo, descricao, importancia, fonte_id, criado_em)
                       VALUES (?,?,?,?,?,?,?)""",
                    (
                        data.get("projeto_id"),
                        data.get("data", ""),
                        data.get("titulo", "").strip(),
                        data.get("descricao", ""),
                        data.get("importancia", "media"),
                        data.get("fonte_id"),
                        ts,
                    ),
                )
                conn.execute(
                    "UPDATE projetos SET atualizado_em = ? WHERE id = ?",
                    (ts, data.get("projeto_id")),
                )
                return self._json_response({"id": cur.lastrowid, "ok": True}, 201)

        self.send_error(404)

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        data = self._read_json()
        ts = agora()
        parts = path.strip("/").split("/")

        if len(parts) != 3 or parts[0] != "api":
            return self.send_error(404)

        recurso, rid = parts[1], parts[2]
        if not rid.isdigit():
            return self.send_error(400)

        with conectar() as conn:
            if recurso == "projetos":
                conn.execute(
                    """UPDATE projetos SET titulo=?, tema=?, periodo=?, descricao=?, status=?, atualizado_em=?
                       WHERE id=?""",
                    (
                        data.get("titulo", "").strip(),
                        data.get("tema", ""),
                        data.get("periodo", ""),
                        data.get("descricao", ""),
                        data.get("status", "em_andamento"),
                        ts,
                        rid,
                    ),
                )
            elif recurso == "fontes":
                conn.execute(
                    """UPDATE fontes SET tipo=?, titulo=?, autores=?, ano=?, local=?, editora=?,
                       revista=?, volume=?, numero=?, paginas=?, url=?, arquivo=?, citacao=?,
                       notas_critica=?, classificacao=?, consultado_em=?, tags=? WHERE id=?""",
                    (
                        data.get("tipo"),
                        data.get("titulo", "").strip(),
                        data.get("autores", ""),
                        data.get("ano", ""),
                        data.get("local", ""),
                        data.get("editora", ""),
                        data.get("revista", ""),
                        data.get("volume", ""),
                        data.get("numero", ""),
                        data.get("paginas", ""),
                        data.get("url", ""),
                        data.get("arquivo", ""),
                        data.get("citacao", ""),
                        data.get("notas_critica", ""),
                        data.get("classificacao", ""),
                        data.get("consultado_em", ""),
                        data.get("tags", ""),
                        rid,
                    ),
                )
            elif recurso == "notas":
                conn.execute(
                    """UPDATE notas SET titulo=?, conteudo=?, pagina=?, tags=?, fonte_id=? WHERE id=?""",
                    (
                        data.get("titulo", "").strip(),
                        data.get("conteudo", ""),
                        data.get("pagina", ""),
                        data.get("tags", ""),
                        data.get("fonte_id"),
                        rid,
                    ),
                )
            elif recurso == "eventos":
                conn.execute(
                    """UPDATE eventos SET data=?, titulo=?, descricao=?, importancia=?, fonte_id=? WHERE id=?""",
                    (
                        data.get("data", ""),
                        data.get("titulo", "").strip(),
                        data.get("descricao", ""),
                        data.get("importancia", "media"),
                        data.get("fonte_id"),
                        rid,
                    ),
                )
            else:
                return self.send_error(404)

        return self._json_response({"ok": True})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        parts = path.strip("/").split("/")

        if len(parts) != 3 or parts[0] != "api":
            return self.send_error(404)

        recurso, rid = parts[1], parts[2]
        if not rid.isdigit():
            return self.send_error(400)

        tabelas = {"projetos": "projetos", "fontes": "fontes", "notas": "notas", "eventos": "eventos"}
        if recurso not in tabelas:
            return self.send_error(404)

        with conectar() as conn:
            conn.execute(f"DELETE FROM {tabelas[recurso]} WHERE id = ?", (rid,))

        return self._json_response({"ok": True})


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


def abrir_navegador(url):
    """Abre a interface no navegador sem impedir a subida do servidor."""
    candidatos = (
        ["xdg-open", url],
        ["gio", "open", url],
        ["sensible-browser", url],
    )

    for comando in candidatos:
        try:
            subprocess.Popen(
                comando,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except FileNotFoundError:
            continue
        except OSError:
            continue

    try:
        return webbrowser.open(url)
    except Exception:
        return False


def main():
    init_db()
    try:
        server = ReusableHTTPServer(("127.0.0.1", PORT), ClioHandler)
    except OSError as erro:
        raise SystemExit(
            f"Não foi possível iniciar o servidor na porta {PORT}: {erro}"
        ) from erro
    url = f"http://127.0.0.1:{PORT}"
    print("=" * 50)
    print("  Clio — Laboratório de Pesquisa em História")
    print("=" * 50)
    print(f"  Acesse: {url}")
    print("  Pressione Ctrl+C para encerrar")
    print("=" * 50)
    threading.Timer(0.8, abrir_navegador, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrado.")
        server.server_close()


if __name__ == "__main__":
    main()

const API = "";
let projetos = [];
let projetoAtual = null;
let dadosProjeto = { fontes: [], notas: [], eventos: [] };

// ── Navegação ──
document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById(btn.dataset.section).classList.add("active");
    });
});

function toast(msg) {
    const el = document.getElementById("toast");
    el.textContent = msg;
    el.classList.add("show");
    setTimeout(() => el.classList.remove("show"), 2500);
}

function fecharModal(id) {
    document.getElementById(id).classList.remove("open");
}

function abrirModal(id) {
    document.getElementById(id).classList.add("open");
}

async function api(url, opts = {}) {
    const res = await fetch(API + url, {
        headers: { "Content-Type": "application/json" },
        ...opts,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.erro || "Erro na requisição");
    }
    return res.json();
}

// ── Projetos ──
async function carregarProjetos() {
    projetos = await api("/api/projetos");
    renderProjetos();
    atualizarSelects();
}

function renderProjetos() {
    const el = document.getElementById("lista-projetos");
    if (!projetos.length) {
        el.innerHTML = `<div class="empty"><div class="icon">📜</div><p>Nenhum projeto ainda. Crie seu primeiro!</p></div>`;
        return;
    }
    el.innerHTML = projetos.map(p => `
        <div class="card">
            <h3>${esc(p.titulo)}</h3>
            <div class="meta">
                ${p.periodo ? `📅 ${esc(p.periodo)}` : ""}
                ${p.tema ? ` · ${esc(p.tema)}` : ""}
            </div>
            <p class="desc">${esc(p.descricao || "Sem descrição")}</p>
            <span class="badge badge-status">${statusLabel(p.status)}</span>
            <div class="actions" style="margin-top:1rem">
                <button class="btn btn-primary btn-sm" onclick="abrirProjeto(${p.id})">Abrir</button>
                <button class="btn btn-secondary btn-sm" onclick="editarProjeto(${p.id})">Editar</button>
                <button class="btn btn-danger btn-sm" onclick="excluirProjeto(${p.id})">Excluir</button>
            </div>
        </div>
    `).join("");
}

function statusLabel(s) {
    return { em_andamento: "Em andamento", revisao: "Em revisão", concluido: "Concluído" }[s] || s;
}

function abrirModalProjeto() {
    document.getElementById("projeto-id").value = "";
    document.getElementById("projeto-titulo").value = "";
    document.getElementById("projeto-tema").value = "";
    document.getElementById("projeto-periodo").value = "";
    document.getElementById("projeto-descricao").value = "";
    document.getElementById("projeto-status").value = "em_andamento";
    document.getElementById("titulo-modal-projeto").textContent = "Novo Projeto";
    abrirModal("modal-projeto");
}

function editarProjeto(id) {
    const p = projetos.find(x => x.id === id);
    if (!p) return;
    document.getElementById("projeto-id").value = p.id;
    document.getElementById("projeto-titulo").value = p.titulo;
    document.getElementById("projeto-tema").value = p.tema || "";
    document.getElementById("projeto-periodo").value = p.periodo || "";
    document.getElementById("projeto-descricao").value = p.descricao || "";
    document.getElementById("projeto-status").value = p.status || "em_andamento";
    document.getElementById("titulo-modal-projeto").textContent = "Editar Projeto";
    abrirModal("modal-projeto");
}

async function salvarProjeto() {
    const id = document.getElementById("projeto-id").value;
    const body = {
        titulo: document.getElementById("projeto-titulo").value,
        tema: document.getElementById("projeto-tema").value,
        periodo: document.getElementById("projeto-periodo").value,
        descricao: document.getElementById("projeto-descricao").value,
        status: document.getElementById("projeto-status").value,
    };
    if (!body.titulo.trim()) return toast("Informe o título do projeto");
    if (id) {
        await api(`/api/projetos/${id}`, { method: "PUT", body: JSON.stringify(body) });
        toast("Projeto atualizado!");
    } else {
        await api("/api/projetos", { method: "POST", body: JSON.stringify(body) });
        toast("Projeto criado!");
    }
    fecharModal("modal-projeto");
    await carregarProjetos();
}

async function excluirProjeto(id) {
    if (!confirm("Excluir este projeto e todos os dados vinculados?")) return;
    await api(`/api/projetos/${id}`, { method: "DELETE" });
    toast("Projeto excluído");
    await carregarProjetos();
}

async function abrirProjeto(id) {
    projetoAtual = id;
    document.querySelector('[data-section="fontes"]').click();
    document.getElementById("sel-projeto-fontes").value = id;
    await carregarDadosProjeto(id);
    carregarFontes();
}

function atualizarSelects() {
    const opts = projetos.map(p =>
        `<option value="${p.id}">${esc(p.titulo)}</option>`
    ).join("");
    const base = `<option value="">Selecione um projeto...</option>`;
    ["sel-projeto-fontes", "sel-projeto-notas", "sel-projeto-eventos",
     "sel-projeto-bib", "sel-busca-projeto"].forEach(id => {
        const el = document.getElementById(id);
        const val = el.value;
        el.innerHTML = (id === "sel-busca-projeto"
            ? `<option value="">Todos os projetos</option>`
            : base) + opts;
        if (val) el.value = val;
    });
}

async function carregarDadosProjeto(id) {
    if (!id) { dadosProjeto = { fontes: [], notas: [], eventos: [] }; return; }
    const data = await api(`/api/projetos/${id}`);
    dadosProjeto = data;
}

function projetoSelecionado(selectId) {
    return document.getElementById(selectId).value;
}

// ── Fontes ──
async function carregarFontes() {
    const id = projetoSelecionado("sel-projeto-fontes");
    const el = document.getElementById("lista-fontes");
    if (!id) {
        el.innerHTML = `<div class="empty"><p>Selecione um projeto para ver as fontes.</p></div>`;
        return;
    }
    await carregarDadosProjeto(id);
    if (!dadosProjeto.fontes.length) {
        el.innerHTML = `<div class="empty"><div class="icon">📖</div><p>Nenhuma fonte cadastrada.</p></div>`;
        return;
    }
    el.innerHTML = dadosProjeto.fontes.map(f => `
        <div class="card">
            <div style="display:flex;justify-content:space-between;align-items:start;gap:1rem">
                <div>
                    <h3>${esc(f.titulo)}</h3>
                    <div class="meta">${esc(f.autores || "Autor desconhecido")} · ${esc(f.ano || "s.d.")}</div>
                </div>
                <span class="badge badge-${f.classificacao || 'secundaria'}">${f.classificacao || 'secundaria'}</span>
            </div>
            <div class="meta">Tipo: ${tipoLabel(f.tipo)} ${f.tags ? `· ${esc(f.tags)}` : ""}</div>
            ${f.notas_critica ? `<p class="desc"><em>Análise:</em> ${esc(f.notas_critica)}</p>` : ""}
            <div class="actions">
                <button class="btn btn-secondary btn-sm" onclick="editarFonte(${f.id})">Editar</button>
                <button class="btn btn-danger btn-sm" onclick="excluirFonte(${f.id})">Excluir</button>
            </div>
        </div>
    `).join("");
}

function tipoLabel(t) {
    return {
        livro: "Livro", artigo: "Artigo", capitulo: "Capítulo",
        tese: "Tese/Dissertação", arquivo: "Arquivo", site: "Site",
        oral: "História oral", outro: "Outro"
    }[t] || t;
}

function ajustarCamposFonte() {
    const tipo = document.getElementById("fonte-tipo").value;
    document.getElementById("campos-periodico").style.display =
        (tipo === "artigo") ? "grid" : "none";
    document.getElementById("campo-url").style.display =
        (tipo === "site") ? "block" : "none";
}

function abrirModalFonte() {
    const pid = projetoSelecionado("sel-projeto-fontes");
    if (!pid) return toast("Selecione um projeto primeiro");
    document.getElementById("fonte-id").value = "";
    ["fonte-titulo","fonte-autores","fonte-ano","fonte-local","fonte-editora",
     "fonte-revista","fonte-volume","fonte-numero","fonte-paginas",
     "fonte-url","fonte-critica","fonte-tags"].forEach(id => {
        document.getElementById(id).value = "";
    });
    document.getElementById("fonte-tipo").value = "livro";
    document.getElementById("fonte-classificacao").value = "secundaria";
    document.getElementById("titulo-modal-fonte").textContent = "Nova Fonte";
    ajustarCamposFonte();
    abrirModal("modal-fonte");
}

function editarFonte(id) {
    const f = dadosProjeto.fontes.find(x => x.id === id);
    if (!f) return;
    document.getElementById("fonte-id").value = f.id;
    document.getElementById("fonte-tipo").value = f.tipo || "livro";
    document.getElementById("fonte-classificacao").value = f.classificacao || "secundaria";
    document.getElementById("fonte-titulo").value = f.titulo || "";
    document.getElementById("fonte-autores").value = f.autores || "";
    document.getElementById("fonte-ano").value = f.ano || "";
    document.getElementById("fonte-local").value = f.local || "";
    document.getElementById("fonte-editora").value = f.editora || "";
    document.getElementById("fonte-revista").value = f.revista || "";
    document.getElementById("fonte-volume").value = f.volume || "";
    document.getElementById("fonte-numero").value = f.numero || "";
    document.getElementById("fonte-paginas").value = f.paginas || "";
    document.getElementById("fonte-url").value = f.url || "";
    document.getElementById("fonte-critica").value = f.notas_critica || "";
    document.getElementById("fonte-tags").value = f.tags || "";
    document.getElementById("titulo-modal-fonte").textContent = "Editar Fonte";
    ajustarCamposFonte();
    abrirModal("modal-fonte");
}

async function salvarFonte() {
    const id = document.getElementById("fonte-id").value;
    const projeto_id = projetoSelecionado("sel-projeto-fontes");
    const body = {
        projeto_id: parseInt(projeto_id),
        tipo: document.getElementById("fonte-tipo").value,
        classificacao: document.getElementById("fonte-classificacao").value,
        titulo: document.getElementById("fonte-titulo").value,
        autores: document.getElementById("fonte-autores").value,
        ano: document.getElementById("fonte-ano").value,
        local: document.getElementById("fonte-local").value,
        editora: document.getElementById("fonte-editora").value,
        revista: document.getElementById("fonte-revista").value,
        volume: document.getElementById("fonte-volume").value,
        numero: document.getElementById("fonte-numero").value,
        paginas: document.getElementById("fonte-paginas").value,
        url: document.getElementById("fonte-url").value,
        notas_critica: document.getElementById("fonte-critica").value,
        tags: document.getElementById("fonte-tags").value,
        consultado_em: new Date().toLocaleDateString("pt-BR"),
    };
    if (!body.titulo.trim()) return toast("Informe o título da fonte");
    if (id) {
        await api(`/api/fontes/${id}`, { method: "PUT", body: JSON.stringify(body) });
        toast("Fonte atualizada!");
    } else {
        const res = await api("/api/fontes", { method: "POST", body: JSON.stringify(body) });
        toast(`Fonte salva! Referência ABNT gerada.`);
    }
    fecharModal("modal-fonte");
    await carregarFontes();
}

async function excluirFonte(id) {
    if (!confirm("Excluir esta fonte?")) return;
    await api(`/api/fontes/${id}`, { method: "DELETE" });
    toast("Fonte excluída");
    await carregarFontes();
}

// ── Notas ──
async function carregarNotas() {
    const id = projetoSelecionado("sel-projeto-notas");
    const el = document.getElementById("lista-notas");
    if (!id) {
        el.innerHTML = `<div class="empty"><p>Selecione um projeto.</p></div>`;
        return;
    }
    await carregarDadosProjeto(id);
    atualizarSelectFontes("nota-fonte-id");
    if (!dadosProjeto.notas.length) {
        el.innerHTML = `<div class="empty"><div class="icon">📝</div><p>Nenhuma nota registrada.</p></div>`;
        return;
    }
    el.innerHTML = dadosProjeto.notas.map(n => {
        const fonte = dadosProjeto.fontes.find(f => f.id === n.fonte_id);
        return `
        <div class="card">
            <h3>${esc(n.titulo)}</h3>
            <div class="meta">
                ${fonte ? `📖 ${esc(fonte.titulo)}` : ""}
                ${n.pagina ? ` · ${esc(n.pagina)}` : ""}
                ${n.tags ? ` · ${esc(n.tags)}` : ""}
            </div>
            <p class="desc">${esc(n.conteudo)}</p>
            <div class="actions">
                <button class="btn btn-secondary btn-sm" onclick="editarNota(${n.id})">Editar</button>
                <button class="btn btn-danger btn-sm" onclick="excluirNota(${n.id})">Excluir</button>
            </div>
        </div>`;
    }).join("");
}

function atualizarSelectFontes(selectId) {
    const sel = document.getElementById(selectId);
    const val = sel.value;
    sel.innerHTML = `<option value="">Nenhuma</option>` +
        dadosProjeto.fontes.map(f =>
            `<option value="${f.id}">${esc(f.titulo)}</option>`
        ).join("");
    if (val) sel.value = val;
}

function abrirModalNota() {
    const pid = projetoSelecionado("sel-projeto-notas");
    if (!pid) return toast("Selecione um projeto primeiro");
    document.getElementById("nota-id").value = "";
    document.getElementById("nota-titulo").value = "";
    document.getElementById("nota-conteudo").value = "";
    document.getElementById("nota-pagina").value = "";
    document.getElementById("nota-tags").value = "";
    document.getElementById("nota-fonte-id").value = "";
    document.getElementById("titulo-modal-nota").textContent = "Nova Nota";
    atualizarSelectFontes("nota-fonte-id");
    abrirModal("modal-nota");
}

function editarNota(id) {
    const n = dadosProjeto.notas.find(x => x.id === id);
    if (!n) return;
    document.getElementById("nota-id").value = n.id;
    document.getElementById("nota-titulo").value = n.titulo || "";
    document.getElementById("nota-conteudo").value = n.conteudo || "";
    document.getElementById("nota-pagina").value = n.pagina || "";
    document.getElementById("nota-tags").value = n.tags || "";
    atualizarSelectFontes("nota-fonte-id");
    document.getElementById("nota-fonte-id").value = n.fonte_id || "";
    document.getElementById("titulo-modal-nota").textContent = "Editar Nota";
    abrirModal("modal-nota");
}

async function salvarNota() {
    const id = document.getElementById("nota-id").value;
    const fonteVal = document.getElementById("nota-fonte-id").value;
    const body = {
        projeto_id: parseInt(projetoSelecionado("sel-projeto-notas")),
        fonte_id: fonteVal ? parseInt(fonteVal) : null,
        titulo: document.getElementById("nota-titulo").value,
        conteudo: document.getElementById("nota-conteudo").value,
        pagina: document.getElementById("nota-pagina").value,
        tags: document.getElementById("nota-tags").value,
    };
    if (!body.titulo.trim()) return toast("Informe o título da nota");
    if (id) {
        await api(`/api/notas/${id}`, { method: "PUT", body: JSON.stringify(body) });
        toast("Nota atualizada!");
    } else {
        await api("/api/notas", { method: "POST", body: JSON.stringify(body) });
        toast("Nota salva!");
    }
    fecharModal("modal-nota");
    await carregarNotas();
}

async function excluirNota(id) {
    if (!confirm("Excluir esta nota?")) return;
    await api(`/api/notas/${id}`, { method: "DELETE" });
    toast("Nota excluída");
    await carregarNotas();
}

// ── Eventos / Cronologia ──
async function carregarEventos() {
    const id = projetoSelecionado("sel-projeto-eventos");
    const el = document.getElementById("lista-eventos");
    if (!id) {
        el.innerHTML = `<div class="empty"><p>Selecione um projeto.</p></div>`;
        return;
    }
    await carregarDadosProjeto(id);
    if (!dadosProjeto.eventos.length) {
        el.innerHTML = `<div class="empty"><div class="icon">📅</div><p>Nenhum evento na cronologia.</p></div>`;
        return;
    }
    el.innerHTML = dadosProjeto.eventos.map(e => `
        <div class="timeline-item ${e.importancia || 'media'}">
            <div class="data">${esc(e.data || "Data indefinida")}</div>
            <h3 style="margin:0.3rem 0">${esc(e.titulo)}</h3>
            ${e.descricao ? `<p class="desc">${esc(e.descricao)}</p>` : ""}
            <div class="actions" style="margin-top:0.5rem">
                <button class="btn btn-secondary btn-sm" onclick="editarEvento(${e.id})">Editar</button>
                <button class="btn btn-danger btn-sm" onclick="excluirEvento(${e.id})">Excluir</button>
            </div>
        </div>
    `).join("");
}

function abrirModalEvento() {
    const pid = projetoSelecionado("sel-projeto-eventos");
    if (!pid) return toast("Selecione um projeto primeiro");
    document.getElementById("evento-id").value = "";
    document.getElementById("evento-data").value = "";
    document.getElementById("evento-titulo").value = "";
    document.getElementById("evento-descricao").value = "";
    document.getElementById("evento-importancia").value = "media";
    document.getElementById("titulo-modal-evento").textContent = "Novo Evento";
    abrirModal("modal-evento");
}

function editarEvento(id) {
    const e = dadosProjeto.eventos.find(x => x.id === id);
    if (!e) return;
    document.getElementById("evento-id").value = e.id;
    document.getElementById("evento-data").value = e.data || "";
    document.getElementById("evento-titulo").value = e.titulo || "";
    document.getElementById("evento-descricao").value = e.descricao || "";
    document.getElementById("evento-importancia").value = e.importancia || "media";
    document.getElementById("titulo-modal-evento").textContent = "Editar Evento";
    abrirModal("modal-evento");
}

async function salvarEvento() {
    const id = document.getElementById("evento-id").value;
    const body = {
        projeto_id: parseInt(projetoSelecionado("sel-projeto-eventos")),
        data: document.getElementById("evento-data").value,
        titulo: document.getElementById("evento-titulo").value,
        descricao: document.getElementById("evento-descricao").value,
        importancia: document.getElementById("evento-importancia").value,
    };
    if (!body.titulo.trim()) return toast("Informe o título do evento");
    if (id) {
        await api(`/api/eventos/${id}`, { method: "PUT", body: JSON.stringify(body) });
        toast("Evento atualizado!");
    } else {
        await api("/api/eventos", { method: "POST", body: JSON.stringify(body) });
        toast("Evento adicionado à cronologia!");
    }
    fecharModal("modal-evento");
    await carregarEventos();
}

async function excluirEvento(id) {
    if (!confirm("Excluir este evento?")) return;
    await api(`/api/eventos/${id}`, { method: "DELETE" });
    toast("Evento excluído");
    await carregarEventos();
}

// ── Pesquisa ──
function trocarAbaBusca(aba) {
    document.querySelectorAll("[data-busca-tab]").forEach(t => {
        t.classList.toggle("active", t.dataset.buscaTab === aba);
    });
    document.getElementById("painel-internet").classList.toggle("active", aba === "internet");
    document.getElementById("painel-local").classList.toggle("active", aba === "local");
}

async function pesquisarInternet() {
    const q = document.getElementById("input-pesquisa-web").value.trim();
    const status = document.getElementById("status-pesquisa-web");
    const el = document.getElementById("resultados-web");
    const btn = document.getElementById("btn-pesquisa-web");

    if (!q) return toast("Digite o que deseja pesquisar");

    btn.disabled = true;
    btn.textContent = "Pesquisando...";
    status.innerHTML = `<span class="loading">Buscando na internet por "${esc(q)}"...</span>`;
    el.innerHTML = "";

    try {
        const data = await api(`/api/pesquisa-web?q=${encodeURIComponent(q)}`);
        if (!data.resultados.length) {
            status.textContent = `Nenhum resultado encontrado para "${q}". Tente outros termos.`;
            el.innerHTML = `<div class="empty"><p>Tente reformular a busca com sinônimos ou termos mais específicos.</p></div>`;
            return;
        }
        status.textContent = `${data.total} resultado(s) para "${data.termo}"`;
        el.innerHTML = data.resultados.map((r, i) => `
            <div class="web-result">
                <h4><a href="${escAttr(r.url)}" target="_blank" rel="noopener noreferrer">${esc(r.titulo)}</a></h4>
                <div class="url">${esc(r.url)}</div>
                <p class="resumo">${esc(r.resumo || "Sem descrição disponível.")}</p>
                <div class="actions">
                    <a class="btn btn-primary btn-sm" href="${escAttr(r.url)}" target="_blank" rel="noopener noreferrer">Abrir site</a>
                    <button class="btn btn-secondary btn-sm" onclick="salvarResultadoComoFonte(${i})">Salvar como fonte</button>
                </div>
            </div>
        `).join("");
        window._ultimosResultadosWeb = data.resultados;
    } catch (err) {
        status.textContent = "Erro na pesquisa.";
        el.innerHTML = `<div class="empty"><p>${esc(err.message)}</p><p>Verifique sua conexão com a internet e tente novamente.</p></div>`;
    } finally {
        btn.disabled = false;
        btn.textContent = "Pesquisar na internet";
    }
}

function salvarResultadoComoFonte(indice) {
    const r = (window._ultimosResultadosWeb || [])[indice];
    if (!r) return;

    if (!projetos.length) {
        toast("Crie um projeto antes de salvar fontes");
        document.querySelector('[data-section="projetos"]').click();
        return;
    }

    document.querySelector('[data-section="fontes"]').click();

    let pid = projetoSelecionado("sel-projeto-fontes");
    if (!pid && projetos.length === 1) {
        pid = String(projetos[0].id);
        document.getElementById("sel-projeto-fontes").value = pid;
    }
    if (!pid) {
        toast("Selecione um projeto na aba Fontes");
        return;
    }

    document.getElementById("fonte-id").value = "";
    document.getElementById("fonte-tipo").value = "site";
    document.getElementById("fonte-classificacao").value = "secundaria";
    document.getElementById("fonte-titulo").value = r.titulo || "";
    document.getElementById("fonte-autores").value = "";
    document.getElementById("fonte-ano").value = "";
    document.getElementById("fonte-local").value = "";
    document.getElementById("fonte-editora").value = "";
    document.getElementById("fonte-revista").value = "";
    document.getElementById("fonte-volume").value = "";
    document.getElementById("fonte-numero").value = "";
    document.getElementById("fonte-paginas").value = "";
    document.getElementById("fonte-url").value = r.url || "";
    document.getElementById("fonte-critica").value = r.resumo || "";
    document.getElementById("fonte-tags").value = "pesquisa-web";
    document.getElementById("titulo-modal-fonte").textContent = "Salvar fonte da internet";
    ajustarCamposFonte();
    abrirModal("modal-fonte");
}

function escAttr(str) {
    return esc(str).replace(/"/g, "&quot;");
}

async function executarBusca() {
    const q = document.getElementById("input-busca").value.trim();
    const projeto_id = document.getElementById("sel-busca-projeto").value;
    const el = document.getElementById("resultados-busca");
    if (!q) return toast("Digite um termo de busca");
    let url = `/api/busca?q=${encodeURIComponent(q)}`;
    if (projeto_id) url += `&projeto_id=${projeto_id}`;
    const { resultados } = await api(url);
    if (!resultados.length) {
        el.innerHTML = `<div class="empty"><p>Nenhum resultado para "${esc(q)}"</p></div>`;
        return;
    }
    el.innerHTML = resultados.map(r => `
        <div class="search-result" onclick="irParaResultado('${r.tipo}', ${r.projeto_id})">
            <div class="tipo">${r.tipo}</div>
            <strong>${esc(r.titulo)}</strong>
            <div class="meta">${esc(r.detalhe || "")}</div>
        </div>
    `).join("");
}

function irParaResultado(tipo, projetoId) {
    const map = { fonte: "fontes", nota: "notas", evento: "cronologia" };
    const sec = map[tipo];
    if (!sec) return;
    document.querySelector(`[data-section="${sec}"]`).click();
    const selId = { fontes: "sel-projeto-fontes", notas: "sel-projeto-notas", cronologia: "sel-projeto-eventos" }[sec];
    document.getElementById(selId).value = projetoId;
    if (sec === "fontes") carregarFontes();
    else if (sec === "notas") carregarNotas();
    else carregarEventos();
}

// ── Bibliografia ──
let bibAtual = [];

async function carregarBibliografia() {
    const id = projetoSelecionado("sel-projeto-bib");
    const el = document.getElementById("lista-bibliografia");
    if (!id) {
        el.innerHTML = `<div class="empty"><p>Selecione um projeto.</p></div>`;
        return;
    }
    const { referencias } = await api(`/api/bibliografia?projeto_id=${id}`);
    bibAtual = referencias;
    if (!referencias.length) {
        el.innerHTML = `<div class="empty"><p>Nenhuma fonte para gerar bibliografia.</p></div>`;
        return;
    }
    el.innerHTML = referencias.map((ref, i) =>
        `<div class="bib-item">${i + 1}. ${ref.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")}</div>`
    ).join("");
}

function copiarBibliografia() {
    if (!bibAtual.length) return toast("Nenhuma referência para copiar");
    const texto = bibAtual.map((r, i) => `${i + 1}. ${r.replace(/\*\*/g, "")}`).join("\n\n");
    navigator.clipboard.writeText(texto).then(() => toast("Bibliografia copiada!"));
}

function exportarBibliografia() {
    if (!bibAtual.length) return toast("Nenhuma referência para exportar");
    const pid = projetoSelecionado("sel-projeto-bib");
    const projeto = projetos.find(p => p.id == pid);
    const texto = `REFERÊNCIAS — ${projeto ? projeto.titulo : "Projeto"}\n${"=".repeat(50)}\n\n` +
        bibAtual.map((r, i) => `${i + 1}. ${r.replace(/\*\*/g, "")}`).join("\n\n");
    const blob = new Blob([texto], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `bibliografia-${pid}.txt`;
    a.click();
    toast("Arquivo exportado!");
}

function esc(str) {
    if (!str) return "";
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
}

// ── Init ──
carregarProjetos();
const state = {
  config: null,
  manifest: null,
  worker: null,
  pending: new Map(),
  requestId: 0,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const nf = new Intl.NumberFormat("pt-BR");
const df = new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short" });
const dateOnly = new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeZone: "UTC" });

const KIND_LABELS = {
  arquivo: "Arquivo",
  arquivo_historico: "Arquivo histórico",
  ato_oficial: "Ato oficial",
  comissao: "Comissão",
  contrato: "Contrato",
  decreto: "Decreto",
  diario: "Diário oficial",
  documento_fiscal: "Documento fiscal",
  documento_orcamentario: "Documento orçamentário",
  lei: "Lei",
  licitacao: "Licitação",
  noticia: "Notícia",
  pagina_web: "Página pública",
  presenca: "Presença",
  proposicao: "Proposição",
  secretaria: "Secretaria",
  sessao: "Sessão",
  vereador: "Vereador",
};

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  }[char]));
}

async function json(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

function displayDate(value) {
  if (!value) return "Data não informada";
  const raw = String(value);
  const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return raw;
  try {
    return dateOnly.format(new Date(`${match[1]}-${match[2]}-${match[3]}T00:00:00Z`));
  } catch (_) {
    return raw;
  }
}

function kindLabel(kind) {
  return KIND_LABELS[kind] || String(kind || "Registro");
}

async function bootData() {
  const [config, manifest] = await Promise.all([
    json("./config.json", { cache: "no-store" }).catch(() => ({ api_base: "", static_api_base: "./api" })),
    json("./data/manifest.json", { cache: "no-store" }).catch(() => null),
  ]);
  state.config = config;
  state.manifest = manifest;
  fillStats();
  fillLatest();
  fillStatus();
  configureDeveloperExamples();
}

function fillStats() {
  if (!state.manifest) return;
  $$('[data-stat]').forEach(node => {
    const key = node.dataset.stat;
    const value = state.manifest[key];
    if (typeof value === "number") node.textContent = nf.format(value);
    else if (value) node.textContent = value;
  });
  $$('[data-generated]').forEach(node => {
    if (!state.manifest.generated_at) return;
    node.textContent = df.format(new Date(state.manifest.generated_at));
  });
}

function fillLatest() {
  const list = $("[data-latest-list]");
  if (!list || !state.manifest?.latest) return;
  list.innerHTML = state.manifest.latest.slice(0, 8).map(item => `
    <li class="result">
      <div class="result-meta"><span class="tag">${escapeHtml(kindLabel(item.kind))}</span><time>${escapeHtml(displayDate(item.effective_date || item.date || item.year))}</time></div>
      <h3 class="result-title"><a href="${escapeHtml(item.source_url)}" rel="noopener noreferrer">${escapeHtml(item.title)}</a></h3>
      <div class="result-meta"><span>${escapeHtml(item.source_name)}</span></div>
    </li>`).join("");
}

function initWorker() {
  if (state.worker) return state.worker;
  const worker = new Worker("./assets/search-worker.js", { type: "classic" });
  worker.onmessage = event => {
    const handler = state.pending.get(event.data.id);
    if (!handler) return;
    state.pending.delete(event.data.id);
    event.data.ok ? handler.resolve(event.data.result) : handler.reject(new Error(event.data.error));
  };
  state.worker = worker;
  return worker;
}

function staticSearch(payload) {
  const worker = initWorker();
  const id = ++state.requestId;
  return new Promise((resolve, reject) => {
    state.pending.set(id, { resolve, reject });
    worker.postMessage({ id, payload });
  });
}

async function apiSearch(payload) {
  const base = (state.config?.api_base || "").replace(/\/$/, "");
  if (!base) throw new Error("Camada consultiva não configurada");
  let endpoint = "/v1/records";
  if (payload.scope === "legislation") endpoint = "/v1/legislation";
  else if (payload.scope === "documents") endpoint = "/v1/documents";
  else if (payload.query) endpoint = "/v1/search";

  const params = new URLSearchParams({ limit: String(payload.limit), offset: String(payload.offset) });
  if (payload.query && endpoint !== "/v1/records") params.set("q", payload.query);
  if (payload.kind) params.set("kind", payload.kind);
  if (payload.year) params.set("year", payload.year);
  if (payload.date_from) params.set("date_from", payload.date_from);
  if (payload.date_to) params.set("date_to", payload.date_to);
  if (payload.sort) params.set("sort", payload.sort);
  params.set("date_mode", "effective");

  const data = await json(`${base}${endpoint}?${params}`, { signal: AbortSignal.timeout(5500) });
  return {
    total: data.page?.total ?? data.items?.length ?? 0,
    items: (data.items || []).map(item => ({
      id: item.id,
      kind: item.kind,
      title: item.title,
      date: item.date,
      effective_date: item.date || (item.year ? `${item.year}-01-01` : ""),
      date_basis: item.date ? "record" : (item.year ? "year" : "observed"),
      year: item.year,
      source_name: item.source?.name,
      source_url: item.source?.url,
      summary: item.summary || ""
    }))
  };
}

function renderResults(target, data, mode) {
  const count = $("[data-result-count]");
  if (count) count.textContent = `${nf.format(data.total)} resultado${data.total === 1 ? "" : "s"}`;
  const modeNode = $("[data-search-mode]");
  if (modeNode) modeNode.textContent = mode === "api" ? "API consultiva v1.1" : "índice público publicado";
  if (!data.items.length) {
    target.innerHTML = `<div class="empty"><strong>Nenhum resultado encontrado.</strong><p>Tente remover filtros, ampliar o período ou verificar outra grafia.</p></div>`;
    return;
  }
  target.innerHTML = `<ul class="result-list">${data.items.map(item => `
    <li class="result">
      <div class="result-meta">
        <span class="tag">${escapeHtml(kindLabel(item.kind))}</span>
        <time>${escapeHtml(displayDate(item.effective_date || item.date || item.year))}</time>
        ${item.date_basis === "year" ? `<span title="A fonte informa o ano, mas não uma data completa.">data por ano</span>` : ""}
      </div>
      <h2 class="result-title"><a href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)}</a></h2>
      ${item.summary ? `<p>${escapeHtml(item.summary).slice(0, 420)}</p>` : ""}
      <div class="result-actions"><a href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener noreferrer">Abrir fonte original</a><span>${escapeHtml(item.source_name || "Fonte pública")}</span></div>
    </li>`).join("")}</ul>`;
}

function formPayload(form) {
  const read = name => form.querySelector(`[name="${name}"]`)?.value?.trim?.() || "";
  return {
    query: read("q"),
    scope: read("scope"),
    kind: read("kind"),
    year: read("year"),
    date_from: read("date_from"),
    date_to: read("date_to"),
    sort: read("sort") || "date_desc",
    limit: 40,
    offset: 0,
  };
}

async function runSearch(form, { updateUrl = true } = {}) {
  const target = $("[data-results]");
  if (!target) return;
  const payload = formPayload(form);

  if (payload.date_from && payload.date_to && payload.date_from > payload.date_to) {
    target.innerHTML = `<div class="empty"><strong>Período inválido.</strong><p>A data inicial precisa ser anterior ou igual à data final.</p></div>`;
    return;
  }

  if (updateUrl && (location.pathname.endsWith("explorar.html") || location.pathname.endsWith("legislacao.html"))) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(payload)) {
      if (["limit", "offset"].includes(key) || !value || (key === "sort" && value === "date_desc")) continue;
      params.set(key === "query" ? "q" : key, String(value));
    }
    history.replaceState(null, "", params.size ? `?${params}` : location.pathname.split("/").pop());
  }

  target.innerHTML = `<p class="loading" role="status">Pesquisando o acervo…</p>`;
  let result;
  let mode = "api";
  try {
    result = await apiSearch(payload);
  } catch (_) {
    mode = "static";
    try {
      result = await staticSearch(payload);
    } catch (error) {
      target.innerHTML = `<div class="empty"><strong>Não foi possível abrir o índice de pesquisa.</strong><p>${escapeHtml(error.message)}</p></div>`;
      return;
    }
  }
  renderResults(target, result, mode);
}

function wireSearch() {
  $$('[data-search-form]').forEach(form => {
    form.addEventListener("submit", event => {
      event.preventDefault();
      if (!location.pathname.endsWith("explorar.html") && !location.pathname.endsWith("legislacao.html") && form.dataset.searchHome === "true") {
        const query = form.querySelector('[name="q"]')?.value.trim();
        if (query) location.href = `./explorar.html?q=${encodeURIComponent(query)}`;
        return;
      }
      runSearch(form);
    });
  });

  const explore = $("[data-explore-form]");
  if (explore) {
    const params = new URLSearchParams(location.search);
    for (const name of ["q", "scope", "kind", "year", "date_from", "date_to", "sort"]) {
      const element = explore.querySelector(`[name="${name}"]`);
      if (element && params.get(name)) element.value = params.get(name);
    }
    $$('select, input[type="date"]', explore).forEach(element => element.addEventListener("change", () => runSearch(explore)));
    runSearch(explore, { updateUrl: false });
  }
}

function fillStatus() {
  const node = $("[data-system-status]");
  if (!node) return;
  if (!state.manifest) {
    node.innerHTML = `<span class="status-dot bad"></span> Metadados do índice indisponíveis`;
    return;
  }
  node.innerHTML = `<span class="status-dot ok"></span> Índice publicado disponível · ${nf.format(state.manifest.records || 0)} registros`;
  const table = $("[data-status-table]");
  if (table) {
    table.innerHTML = `
      <tr><th>Última geração</th><td>${state.manifest.generated_at ? escapeHtml(df.format(new Date(state.manifest.generated_at))) : "—"}</td></tr>
      <tr><th>Registros</th><td>${nf.format(state.manifest.records || 0)}</td></tr>
      <tr><th>Documentos e arquivos</th><td>${nf.format(state.manifest.documents || 0)}</td></tr>
      <tr><th>Leis, decretos e proposições</th><td>${nf.format(state.manifest.legislation || 0)}</td></tr>
      <tr><th>Tipos</th><td>${nf.format(Object.keys(state.manifest.counts_by_kind || {}).length)}</td></tr>
      <tr><th>Fontes</th><td>${nf.format(state.manifest.sources || 0)}</td></tr>
      <tr><th>Ordenação padrão</th><td>Data efetiva, mais recente primeiro</td></tr>
      <tr><th>Modo de publicação</th><td>Snapshot validado + Data API + índice web derivado</td></tr>`;
  }
  probeApi();
}

async function probeApi() {
  const node = $("[data-api-status]");
  if (!node) return;
  const dynamicBase = (state.config?.api_base || "").replace(/\/$/, "");
  const staticBase = (state.config?.static_api_base || "./api").replace(/\/$/, "");

  if (dynamicBase) {
    try {
      const result = await json(`${dynamicBase}/health/ready`, { signal: AbortSignal.timeout(4000), cache: "no-store" });
      if (result.ready) {
        node.innerHTML = `<span class="status-dot ok"></span> API consultiva operacional · ${nf.format(result.documents || 0)} documentos · ${nf.format(result.legislation || 0)} itens legislativos`;
        return;
      }
    } catch (_) {}
  }

  try {
    const result = await json(`${staticBase}/health/ready.json`, { signal: AbortSignal.timeout(4000), cache: "no-store" });
    node.innerHTML = `<span class="status-dot ${result.ready ? "ok" : "warn"}"></span> Data API pública ${result.ready ? "operacional" : "degradada"} · ${nf.format(result.documents || 0)} documentos · busca local ativa`;
  } catch (_) {
    node.innerHTML = `<span class="status-dot bad"></span> Data API indisponível; o último índice local permanece utilizável.`;
  }
}

function configureDeveloperExamples() {
  const dynamicBase = (state.config?.api_base || "").replace(/\/$/, "");
  const staticBase = (state.config?.static_api_base || "./api").replace(/\/$/, "");
  $$('[data-api-base]').forEach(node => node.textContent = dynamicBase || "API consultiva não publicada neste host");
  $$('[data-static-api-base]').forEach(node => node.textContent = staticBase);
  $$('[data-api-link]').forEach(node => {
    if (dynamicBase) {
      node.href = `${dynamicBase}/docs`;
      node.removeAttribute("aria-disabled");
    } else {
      node.href = `${staticBase}/v1/index.json`;
      node.textContent = "Abrir catálogo da Data API";
      node.removeAttribute("aria-disabled");
    }
  });
}

function registerServiceWorker() {
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("./sw.js").catch(() => {});
}

document.documentElement.classList.add("js");
document.addEventListener("DOMContentLoaded", async () => {
  wireSearch();
  await bootData();
  registerServiceWorker();
});

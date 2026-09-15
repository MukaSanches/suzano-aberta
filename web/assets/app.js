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

async function bootData() {
  const [config, manifest] = await Promise.all([
    json("./config.json", { cache: "no-store" }).catch(() => ({ api_base: "" })),
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
  list.innerHTML = state.manifest.latest.slice(0, 6).map(item => `
    <li class="result">
      <div class="result-meta"><span class="tag">${escapeHtml(item.kind)}</span><span>${escapeHtml(item.date || item.year || "Data não informada")}</span></div>
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
  if (!base) throw new Error("API pública não configurada");
  const params = new URLSearchParams({ q: payload.query, limit: String(payload.limit), offset: String(payload.offset) });
  if (payload.kind) params.set("kind", payload.kind);
  if (payload.year) params.set("year", payload.year);
  const data = await json(`${base}/v1/search?${params}`, { signal: AbortSignal.timeout(5500) });
  return {
    total: data.page?.total ?? data.items?.length ?? 0,
    items: (data.items || []).map(item => ({
      id: item.id, kind: item.kind, title: item.title, date: item.date, year: item.year,
      source_name: item.source?.name, source_url: item.source?.url, summary: item.summary || ""
    }))
  };
}

function renderResults(target, data, mode) {
  const count = $("[data-result-count]");
  if (count) count.textContent = `${nf.format(data.total)} resultado${data.total === 1 ? "" : "s"}`;
  const modeNode = $("[data-search-mode]");
  if (modeNode) modeNode.textContent = mode === "api" ? "API v1" : "índice publicado";
  if (!data.items.length) {
    target.innerHTML = `<div class="empty"><strong>Nenhum resultado encontrado.</strong><p>Tente termos mais curtos, remova filtros ou verifique outra grafia.</p></div>`;
    return;
  }
  target.innerHTML = `<ul class="result-list">${data.items.map(item => `
    <li class="result">
      <div class="result-meta"><span class="tag">${escapeHtml(item.kind)}</span>${item.year ? `<span>${escapeHtml(item.year)}</span>` : ""}${item.date ? `<span>${escapeHtml(item.date)}</span>` : ""}</div>
      <h2 class="result-title"><a href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)}</a></h2>
      ${item.summary ? `<p>${escapeHtml(item.summary).slice(0, 360)}</p>` : ""}
      <div class="result-actions"><a href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener noreferrer">Abrir fonte original</a><span>${escapeHtml(item.source_name || "Fonte pública")}</span></div>
    </li>`).join("")}</ul>`;
}

async function runSearch(form, { updateUrl = true } = {}) {
  const target = $("[data-results]");
  if (!target) return;
  const query = form.querySelector('[name="q"]')?.value.trim() || "";
  const kind = form.querySelector('[name="kind"]')?.value || "";
  const year = form.querySelector('[name="year"]')?.value || "";
  if (!query) return;

  if (updateUrl && location.pathname.endsWith("explorar.html")) {
    const params = new URLSearchParams({ q: query });
    if (kind) params.set("kind", kind);
    if (year) params.set("year", year);
    history.replaceState(null, "", `?${params}`);
  }

  target.innerHTML = `<p class="loading" role="status">Pesquisando o acervo…</p>`;
  const payload = { query, kind, year, limit: 40, offset: 0 };
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
      if (!location.pathname.endsWith("explorar.html") && form.dataset.searchHome === "true") {
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
    for (const name of ["q", "kind", "year"]) {
      const element = explore.querySelector(`[name="${name}"]`);
      if (element && params.get(name)) element.value = params.get(name);
    }
    if (params.get("q")) runSearch(explore, { updateUrl: false });
    $$('select', explore).forEach(select => select.addEventListener("change", () => runSearch(explore)));
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
      <tr><th>Tipos</th><td>${nf.format(Object.keys(state.manifest.counts_by_kind || {}).length)}</td></tr>
      <tr><th>Fontes</th><td>${nf.format(state.manifest.sources || 0)}</td></tr>
      <tr><th>Modo de publicação</th><td>Snapshot validado + índice web derivado</td></tr>`;
  }
  probeApi();
}

async function probeApi() {
  const node = $("[data-api-status]");
  if (!node) return;
  const base = (state.config?.api_base || "").replace(/\/$/, "");
  if (!base) {
    node.innerHTML = `<span class="status-dot warn"></span> API pública ainda não configurada neste portal; busca local está ativa.`;
    return;
  }
  try {
    const result = await json(`${base}/health/ready`, { signal: AbortSignal.timeout(4000), cache: "no-store" });
    node.innerHTML = `<span class="status-dot ${result.ready ? "ok" : "warn"}"></span> API ${result.ready ? "operacional" : "degradada"}`;
  } catch (_) {
    node.innerHTML = `<span class="status-dot warn"></span> API indisponível; o portal continua usando o índice local.`;
  }
}

function configureDeveloperExamples() {
  const base = (state.config?.api_base || "https://api.exemplo.suzanoaberta").replace(/\/$/, "");
  $$('[data-api-base]').forEach(node => node.textContent = base);
  $$('[data-api-link]').forEach(node => {
    if (state.config?.api_base) node.href = `${base}/docs`;
    else node.setAttribute("aria-disabled", "true");
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

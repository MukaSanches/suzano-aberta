(() => {
  "use strict";

  if ((location.pathname.split("/").pop() || "index.html") !== "legislacao.html") return;

  const $ = (selector, root = document) => root?.querySelector?.(selector) || null;
  const $$ = (selector, root = document) => root?.querySelectorAll ? [...root.querySelectorAll(selector)] : [];
  const nf = new Intl.NumberFormat("pt-BR");
  const dateFmt = new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeZone: "UTC" });
  const PAGE_SIZE = 40;
  const mobileQuery = matchMedia("(max-width: 900px)");

  let sequence = 0;
  let worker = null;
  let requestId = 0;
  const pending = new Map();
  let legacyDatasetPromise = null;
  const legacyPrepared = new WeakMap();

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, char => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
    }[char]));
  }

  function fold(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("pt-BR")
      .replace(/[^a-z0-9\s./-]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function displayDate(value) {
    const raw = String(value || "");
    const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!match) return raw || "Data não informada";
    try {
      return dateFmt.format(new Date(`${match[1]}-${match[2]}-${match[3]}T00:00:00Z`));
    } catch (_) {
      return raw;
    }
  }

  function effectiveDate(item) {
    if (item?.effective_date) return String(item.effective_date);
    if (item?.date) return String(item.date);
    if (item?.year) return `${item.year}-01-01`;
    return "";
  }

  function itemSource(item) {
    const source = item?.source || {};
    return {
      name: String(source.name || item?.source_name || "Fonte pública"),
      url: String(item?.document_url || source.url || item?.source_url || ""),
      pageUrl: String(source.url || item?.source_url || item?.document_url || ""),
    };
  }

  function readPayload(form) {
    const read = name => form.querySelector(`[name="${name}"]`)?.value?.trim?.() || "";
    const rawOffset = Number(form.dataset.offset || 0);
    return {
      query: read("q"),
      kind: read("kind"),
      year: read("year"),
      date_from: read("date_from"),
      date_to: read("date_to"),
      sort: read("sort") || (read("q") ? "relevance" : "date_desc"),
      limit: PAGE_SIZE,
      offset: Number.isFinite(rawOffset) && rawOffset >= 0 ? rawOffset : 0,
    };
  }

  function initWorker() {
    if (worker) return worker;
    worker = new Worker("./assets/legislation-worker-v9.js", { type: "classic" });
    worker.onmessage = event => {
      const handler = pending.get(event.data?.id);
      if (!handler) return;
      pending.delete(event.data.id);
      if (event.data.ok) handler.resolve(event.data.result);
      else handler.reject(new Error(event.data.error || "Falha na busca legislativa."));
    };
    worker.onerror = error => {
      for (const [, handler] of pending) handler.reject(error instanceof Error ? error : new Error("Worker legislativo indisponível."));
      pending.clear();
      worker?.terminate();
      worker = null;
    };
    return worker;
  }

  function fastSearch(payload) {
    const activeWorker = initWorker();
    const id = ++requestId;
    return new Promise((resolve, reject) => {
      pending.set(id, { resolve, reject });
      activeWorker.postMessage({ id, payload });
    });
  }

  async function loadLegacyDataset() {
    if (!legacyDatasetPromise) {
      legacyDatasetPromise = fetch("./data/legislation.json?v=2", { cache: "no-cache" })
        .then(response => {
          if (!response.ok) throw new Error(`HTTP ${response.status} ao carregar legislação`);
          return response.json();
        })
        .then(payload => {
          if (!Array.isArray(payload?.items)) throw new Error("Feed legislativo de contingência inválido.");
          return payload;
        });
    }
    return legacyDatasetPromise;
  }

  function legacyPrepare(item) {
    let cached = legacyPrepared.get(item);
    if (cached) return cached;
    const source = itemSource(item);
    const title = fold(item?.title);
    const summary = fold(item?.summary);
    const sourceText = fold(source.name);
    cached = {
      title,
      summary,
      source: sourceText,
      text: `${title} ${summary} ${sourceText} ${fold(item?.id)}`.trim(),
      date: effectiveDate(item),
      year: Number(item?.year || String(effectiveDate(item)).slice(0, 4) || 0),
    };
    legacyPrepared.set(item, cached);
    return cached;
  }

  function queryTokens(query) {
    return [...new Set(fold(query).split(" ").filter(token => token.length >= 2))].slice(0, 10);
  }

  function legacyScore(item, clean, tokens) {
    const fields = legacyPrepare(item);
    let score = 0;
    if (fields.title === clean) score += 1000;
    else if (fields.title.includes(clean)) score += 650;
    if (fields.summary.includes(clean)) score += 320;
    if (fields.source.includes(clean)) score += 80;
    for (const token of tokens) {
      if (fields.title.includes(token)) score += 110;
      else if (fields.summary.includes(token)) score += 45;
      else if (fields.source.includes(token)) score += 12;
    }
    return score;
  }

  async function legacySearch(payload) {
    const dataset = await loadLegacyDataset();
    const clean = fold(payload.query);
    const tokens = queryTokens(clean);
    const year = Number(payload.year || 0);
    let items = [];

    for (const item of dataset.items) {
      if (!item || !["lei", "decreto", "proposicao"].includes(String(item.kind || ""))) continue;
      if (payload.kind && item.kind !== payload.kind) continue;
      const fields = legacyPrepare(item);
      if (year && fields.year !== year) continue;
      if (payload.date_from && (!fields.date || fields.date < payload.date_from)) continue;
      if (payload.date_to && (!fields.date || fields.date > payload.date_to)) continue;
      if (clean && !fields.text.includes(clean) && !(tokens.length && tokens.every(token => fields.text.includes(token)))) continue;
      items.push(item);
    }

    if (payload.sort === "date_asc") {
      items = items.slice().reverse();
    } else if (payload.sort === "relevance" && clean) {
      items = items
        .map(item => ({ item, score: legacyScore(item, clean, tokens) }))
        .sort((a, b) => b.score - a.score || effectiveDate(b.item).localeCompare(effectiveDate(a.item)))
        .map(entry => entry.item);
    }

    const total = items.length;
    return {
      total,
      items: items.slice(payload.offset, payload.offset + payload.limit),
      meta: dataset.meta || {},
      contingency: true,
    };
  }

  function internalUrl(item) {
    if (!["lei", "decreto"].includes(String(item?.kind || ""))) return itemSource(item).pageUrl;
    const source = itemSource(item).pageUrl;
    return `./norma.html?id=${encodeURIComponent(item.id || "")}&source=${encodeURIComponent(source)}`;
  }

  function kindLabel(kind) {
    return ({ lei: "Lei", decreto: "Decreto", proposicao: "Proposição" })[kind] || "Registro";
  }

  function renderPagination(target, result, form, payload) {
    const pages = Math.max(1, Math.ceil(result.total / payload.limit));
    const current = Math.min(pages, Math.floor(payload.offset / payload.limit) + 1);
    if (pages <= 1) return;

    const nav = document.createElement("nav");
    nav.className = "pagination";
    nav.setAttribute("aria-label", "Paginação dos resultados legislativos");
    nav.innerHTML = `
      <span class="pagination-status">Página <strong>${nf.format(current)}</strong> de <strong>${nf.format(pages)}</strong></span>
      <div class="pagination-group">
        <button type="button" data-page-offset="${Math.max(0, payload.offset - payload.limit)}" ${current <= 1 ? "disabled" : ""}>← Anterior</button>
        <button type="button" data-page-offset="${payload.offset + payload.limit}" ${current >= pages ? "disabled" : ""}>Próxima →</button>
      </div>`;
    nav.addEventListener("click", event => {
      const button = event.target instanceof Element ? event.target.closest("button[data-page-offset]") : null;
      if (!(button instanceof HTMLButtonElement) || button.disabled) return;
      form.dataset.offset = String(Number(button.dataset.pageOffset || 0));
      runSearch(form).then(() => {
        const top = target.getBoundingClientRect().top + scrollY - 110;
        scrollTo({
          top: Math.max(0, top),
          behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
        });
      });
    });
    target.append(nav);
  }

  function renderResultList(target, result, form, payload, mode) {
    const count = $("[data-result-count]");
    if (count) count.textContent = `${nf.format(result.total)} resultado${result.total === 1 ? "" : "s"}`;
    const modeNode = $("[data-search-mode]");
    if (modeNode) modeNode.textContent = mode;

    if (!result.items.length) {
      target.innerHTML = `<div class="empty"><strong>Nenhum resultado encontrado.</strong><p>Remova filtros, amplie o período ou tente outra grafia.</p></div>`;
      return;
    }

    target.innerHTML = `<ul class="result-list">${result.items.map(item => {
      const source = itemSource(item);
      const internal = internalUrl(item);
      const titleHref = internal || source.pageUrl || source.url || "#";
      const internalAction = ["lei", "decreto"].includes(String(item.kind || ""))
        ? `<a data-detail-link href="${escapeHtml(internal)}">Visualizar ${item.kind === "decreto" ? "decreto" : "lei"}</a>`
        : "";
      const official = source.pageUrl || source.url;
      return `
        <li class="result">
          <div class="result-meta">
            <span class="tag">${escapeHtml(kindLabel(item.kind))}</span>
            <time datetime="${escapeHtml(effectiveDate(item))}">${escapeHtml(displayDate(effectiveDate(item)))}</time>
            ${item.date_basis === "year" ? `<span title="A fonte informa somente o ano.">data por ano</span>` : ""}
          </div>
          <h2 class="result-title"><a href="${escapeHtml(titleHref)}"${item.kind === "proposicao" ? ' target="_blank" rel="noopener noreferrer"' : ""}>${escapeHtml(item.title || "Registro legislativo")}</a></h2>
          ${item.summary ? `<p>${escapeHtml(item.summary).slice(0, 520)}</p>` : ""}
          <div class="result-actions">
            ${internalAction}
            ${official ? `<a href="${escapeHtml(official)}" target="_blank" rel="noopener noreferrer">Fonte oficial</a>` : ""}
            <span>${escapeHtml(source.name)}</span>
          </div>
        </li>`;
    }).join("")}</ul>`;
    renderPagination(target, result, form, payload);
  }

  function expectedCount(result, payload) {
    if (payload.query || payload.year || payload.date_from || payload.date_to) return null;
    if (!payload.kind) return Number(result.meta?.total || 0);
    return Number(result.meta?.counts_by_kind?.[payload.kind] || 0);
  }

  function updateUrl(payload) {
    const params = new URLSearchParams();
    if (payload.query) params.set("q", payload.query);
    if (payload.kind && payload.kind !== "lei") params.set("kind", payload.kind);
    if (!payload.kind) params.set("kind", "");
    if (payload.year) params.set("year", payload.year);
    if (payload.date_from) params.set("date_from", payload.date_from);
    if (payload.date_to) params.set("date_to", payload.date_to);
    if (payload.sort && payload.sort !== "date_desc") params.set("sort", payload.sort);
    if (payload.offset > 0) params.set("page", String(Math.floor(payload.offset / payload.limit) + 1));
    history.replaceState(null, "", params.toString() ? `?${params}` : "legislacao.html");
  }

  function updateHeading(form, query) {
    const heading = $(".legislation-results-head h2");
    if (!heading) return;
    if (query) {
      heading.textContent = `Resultados para “${query}”`;
      return;
    }
    const kind = $("[name='kind']", form)?.value || "";
    heading.textContent = kind === "lei" ? "Leis mais recentes"
      : kind === "decreto" ? "Decretos mais recentes"
      : kind === "proposicao" ? "Proposições mais recentes"
      : "Legislação mais recente";
  }

  function syncSwitcher(form) {
    const kind = $("[name='kind']", form)?.value || "";
    $$("[data-kind-shortcut]").forEach(link => {
      if ((link.dataset.kindShortcut || "") === kind) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
  }

  async function runSearch(form, { updateHistory = true } = {}) {
    const target = $("[data-results]");
    if (!target) return;
    const payload = readPayload(form);
    const current = ++sequence;
    updateHeading(form, payload.query);
    syncSwitcher(form);

    if (payload.date_from && payload.date_to && payload.date_from > payload.date_to) {
      target.innerHTML = `<div class="empty"><strong>Período inválido.</strong><p>A data inicial precisa ser anterior ou igual à data final.</p></div>`;
      return;
    }

    if (updateHistory) updateUrl(payload);
    target.innerHTML = `<p class="loading" role="status">Pesquisando legislação…</p>`;

    try {
      const result = await fastSearch(payload);
      if (current !== sequence) return;
      const expected = expectedCount(result, payload);
      if (expected !== null && expected > 0 && result.total === 0) {
        throw new Error(`Inconsistência detectada: o índice declara ${expected} registros para esta coleção.`);
      }
      renderResultList(target, result, form, payload, "índice legislativo rápido");
      return;
    } catch (primaryError) {
      try {
        const result = await legacySearch(payload);
        if (current !== sequence) return;
        renderResultList(target, result, form, payload, "modo de contingência");
        return;
      } catch (_) {
        if (current !== sequence) return;
        const message = primaryError instanceof Error ? primaryError.message : String(primaryError);
        const count = $("[data-result-count]");
        if (count) count.textContent = "Índice temporariamente indisponível";
        target.innerHTML = `<div class="empty legislation-source-error"><strong>Não foi possível abrir a coleção legislativa publicada.</strong><p>${escapeHtml(message)}</p><p><a href="https://leis.camarasuzano.sp.gov.br/szn/legislacao/" target="_blank" rel="noopener noreferrer">Consultar leis na Câmara</a> · <a href="https://suzano.sp.gov.br/leis-e-decretos/" target="_blank" rel="noopener noreferrer">Consultar atos na Prefeitura</a></p></div>`;
      }
    }
  }

  function hydrateFromUrl(form) {
    const params = new URLSearchParams(location.search);
    for (const name of ["q", "kind", "year", "date_from", "date_to", "sort"]) {
      if (!params.has(name)) continue;
      const field = form.querySelector(`[name="${name}"]`);
      if (field) field.value = params.get(name) || "";
    }
    const q = $("[name='q']", form)?.value?.trim() || "";
    const sort = $("[name='sort']", form);
    if (sort && !params.has("sort")) sort.value = q ? "relevance" : "date_desc";
    const page = Math.max(1, Number(params.get("page") || 1));
    form.dataset.offset = String(Number.isFinite(page) ? (page - 1) * PAGE_SIZE : 0);
  }

  function repairLayout(form) {
    const shell = form.closest(".results-shell");
    const column = $("[data-results-column]", shell);
    if (!shell || !column) return;
    shell.classList.add("search-layout-v7", "legislation-browser-v8", "legislation-browser-v9");
    const active = $(":scope > .active-filter-bar", shell);
    if (active && active.parentElement !== column) column.prepend(active);
  }

  function ensureMobileToggle(form) {
    const shell = form.closest(".results-shell");
    if (!shell) return;
    let button = $(".search-filter-toggle", shell);
    if (!button) {
      if (!form.id) form.id = "legislation-filters";
      button = document.createElement("button");
      button.type = "button";
      button.className = "search-filter-toggle";
      button.setAttribute("aria-controls", form.id);
      shell.insertBefore(button, form);
      button.addEventListener("click", () => {
        const expanded = button.getAttribute("aria-expanded") === "true";
        button.setAttribute("aria-expanded", String(!expanded));
        button.textContent = expanded ? "Mostrar filtros" : "Ocultar filtros";
        form.classList.toggle("is-v7-collapsed", expanded);
      });
    }

    const apply = () => {
      if (mobileQuery.matches) {
        if (!form.dataset.v9MobileInitialized) {
          form.classList.add("is-v7-collapsed");
          form.dataset.v9MobileInitialized = "true";
        }
        const expanded = !form.classList.contains("is-v7-collapsed");
        button.setAttribute("aria-expanded", String(expanded));
        button.textContent = expanded ? "Ocultar filtros" : "Mostrar filtros";
      } else {
        form.classList.remove("is-v7-collapsed");
        button.setAttribute("aria-expanded", "true");
        button.textContent = "Filtros";
      }
    };

    apply();
    if (typeof mobileQuery.addEventListener === "function") mobileQuery.addEventListener("change", apply);
  }

  function init() {
    const form = $("[data-legislation-form]");
    if (!(form instanceof HTMLFormElement)) return;

    hydrateFromUrl(form);
    repairLayout(form);
    ensureMobileToggle(form);
    syncSwitcher(form);

    form.addEventListener("submit", event => {
      event.preventDefault();
      form.dataset.offset = "0";
      runSearch(form);
    });

    $$('select, input[type="date"], input[type="number"]', form).forEach(field => {
      field.addEventListener("change", () => {
        form.dataset.offset = "0";
        runSearch(form);
      });
    });

    const shell = form.closest(".results-shell");
    if (shell) new MutationObserver(() => repairLayout(form)).observe(shell, { childList: true });

    runSearch(form, { updateHistory: false });
  }

  document.documentElement.classList.add("legislation-v9");
  document.addEventListener("DOMContentLoaded", init);
  addEventListener("pagehide", () => worker?.terminate(), { once: true });
})();

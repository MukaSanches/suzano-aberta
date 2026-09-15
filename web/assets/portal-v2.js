(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const NEWS_REFRESH_MS = 30 * 60 * 1000;
  const dateFmt = new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium" });
  const dateTimeFmt = new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short" });

  const KIND_LABELS = {
    lei: "Lei",
    decreto: "Decreto",
    proposicao: "Proposição",
    licitacao: "Licitação",
    contrato: "Contrato",
    noticia: "Notícia",
    arquivo: "Arquivo",
    diario: "Diário oficial",
  };

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, char => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
    }[char]));
  }

  function displayDate(value) {
    if (!value) return "Data não informada";
    const raw = String(value);
    const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (match) {
      try {
        return dateFmt.format(new Date(`${match[1]}-${match[2]}-${match[3]}T12:00:00Z`));
      } catch (_) {}
    }
    try {
      const parsed = new Date(raw);
      if (!Number.isNaN(parsed.getTime())) return dateFmt.format(parsed);
    } catch (_) {}
    return raw;
  }

  function canonicalUrl(value) {
    try {
      const url = new URL(String(value || ""), location.href);
      url.hash = "";
      url.search = "";
      url.pathname = url.pathname.replace(/\/+$/, "") || "/";
      return url.toString().replace(/\/$/, "");
    } catch (_) {
      return String(value || "").replace(/[?#].*$/, "").replace(/\/+$/, "");
    }
  }

  async function fetchJsonGzip(url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    if (!("DecompressionStream" in window)) {
      throw new Error("Seu navegador não oferece a descompressão necessária para esta consulta.");
    }
    const stream = response.body.pipeThrough(new DecompressionStream("gzip"));
    return new Response(stream).json();
  }

  function shardFor(recordId) {
    let total = 0;
    for (const char of String(recordId || "")) {
      total = (((total * 33) >>> 0) + char.codePointAt(0)) >>> 0;
    }
    return (total & 15).toString(16);
  }

  async function loadDetail(recordId) {
    if (!recordId) return null;
    const shard = shardFor(recordId);
    const data = await fetchJsonGzip(`./data/details/${shard}.json.gz`);
    return data[recordId] || null;
  }

  async function loadRelations(recordId) {
    if (!recordId) return [];
    const shard = shardFor(recordId);
    const data = await fetchJsonGzip(`./data/relations/${shard}.json.gz`);
    return data[recordId] || [];
  }

  function internalUrl(item) {
    const kind = String(item?.kind || "");
    const source = item?.source?.url || item?.source_url || "";
    if (["lei", "decreto"].includes(kind)) {
      return `./norma.html?id=${encodeURIComponent(item.id || "")}&source=${encodeURIComponent(source)}`;
    }
    if (["licitacao", "contrato"].includes(kind)) {
      return `./contratacoes.html?id=${encodeURIComponent(item.id || "")}&source=${encodeURIComponent(source)}`;
    }
    return source || "./explorar.html";
  }

  function renderRelations(target, relations) {
    if (!target) return;
    if (!relations.length) {
      target.innerHTML = `<div class="empty"><strong>Nenhuma relação determinística encontrada.</strong><p>O portal só cria vínculos quando existe evidência como CNPJ, número de processo, identificador, fornecedor, norma citada ou fonte comum.</p></div>`;
      return;
    }
    target.innerHTML = `<ul class="relation-list">${relations.map(item => `
      <li>
        <span class="tag">${escapeHtml(KIND_LABELS[item.kind] || item.kind || "Registro")}</span>
        <div>
          <a href="${escapeHtml(internalUrl(item))}"><strong>${escapeHtml(item.title || "Registro relacionado")}</strong></a>
          <span>${escapeHtml(item.reason || "Relação documental")}${item.date ? ` · ${escapeHtml(displayDate(item.date))}` : ""}</span>
        </div>
      </li>`).join("")}</ul>`;
  }

  async function loadNews() {
    const list = $("[data-news-list]");
    if (!list) return;
    const status = $("[data-news-generated]");
    try {
      const response = await fetch(`./data/news.json?t=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!Array.isArray(data.items) || data.items.length !== 5) {
        throw new Error("feed incompleto");
      }
      list.innerHTML = data.items.map(item => `
        <article class="news-item">
          <div class="result-meta">
            <span class="tag">${escapeHtml(item.origin === "prefeitura" ? "Fonte oficial" : "Web")}</span>
            <time>${escapeHtml(displayDate(item.published_at))}</time>
          </div>
          <h3><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)}</a></h3>
          <p>${escapeHtml(item.publisher || "Fonte pública")}</p>
        </article>`).join("");
      if (status) {
        status.textContent = data.generated_at
          ? `Atualizado ${dateTimeFmt.format(new Date(data.generated_at))} · atualização programada a cada 30 minutos`
          : "Atualização programada a cada 30 minutos";
      }
    } catch (error) {
      list.innerHTML = `<div class="empty"><strong>As notícias não puderam ser atualizadas agora.</strong><p>O restante do acervo continua disponível normalmente.</p></div>`;
      if (status) status.textContent = "Última tentativa de atualização falhou.";
    }
  }

  function enhanceRenderedResults(root = document) {
    $$(".result:not([data-portal-v2])", root).forEach(result => {
      result.dataset.portalV2 = "true";
      const tag = $(".tag", result)?.textContent?.trim().toLocaleLowerCase("pt-BR") || "";
      const titleLink = $(".result-title a", result);
      if (!titleLink) return;
      const sourceUrl = titleLink.href;

      let internal = "";
      if (tag === "lei" || tag === "decreto") {
        internal = `./norma.html?source=${encodeURIComponent(sourceUrl)}`;
      } else if (tag === "licitação" || tag === "contrato") {
        internal = `./contratacoes.html?source=${encodeURIComponent(sourceUrl)}`;
      }
      if (!internal) return;

      titleLink.href = internal;
      titleLink.removeAttribute("target");
      titleLink.removeAttribute("rel");

      const actions = $(".result-actions", result);
      if (actions && !actions.querySelector("[data-detail-link]")) {
        const link = document.createElement("a");
        link.dataset.detailLink = "true";
        link.href = internal;
        link.textContent = tag === "lei" || tag === "decreto"
          ? "Ler texto oficial e relações"
          : "Ver detalhes e relações";
        actions.prepend(link);
      }
    });
  }

  function watchResults() {
    const roots = $$("[data-results]");
    for (const root of roots) {
      enhanceRenderedResults(root);
      const observer = new MutationObserver(() => enhanceRenderedResults(root));
      observer.observe(root, { childList: true, subtree: true });
    }
  }

  function formatAttributeLabel(key) {
    return String(key || "")
      .replace(/_/g, " ")
      .replace(/\b\w/g, char => char.toUpperCase());
  }

  function renderMetadata(target, detail, allowedKeys = null) {
    if (!target || !detail) return;
    const attrs = detail.attributes || {};
    const preferred = allowedKeys || [
      "numero", "norma_tipo", "classe", "identifier", "modalidade", "situacao",
      "processo", "compras_gov", "objeto", "amparo_legal", "contractor",
      "contratada", "valor", "vigencia", "author"
    ];
    const rows = [];
    for (const key of preferred) {
      const value = attrs[key];
      if (value === null || value === undefined || value === "" || Array.isArray(value) || typeof value === "object") continue;
      rows.push(`<div><dt>${escapeHtml(formatAttributeLabel(key))}</dt><dd>${escapeHtml(value)}</dd></div>`);
    }
    rows.unshift(
      `<div><dt>Data</dt><dd>${escapeHtml(displayDate(detail.date || detail.year))}</dd></div>`,
      `<div><dt>Fonte</dt><dd>${escapeHtml(detail.source?.name || "Fonte pública")}</dd></div>`
    );
    target.innerHTML = rows.join("");
  }

  async function findLegislation(params) {
    const id = params.get("id");
    if (id) {
      const detail = await loadDetail(id).catch(() => null);
      if (detail) return detail;
    }

    const source = canonicalUrl(params.get("source"));
    const collection = await fetchJsonGzip("./api/v1/legislacao.json.gz");
    const item = (collection.items || []).find(candidate => {
      if (id && candidate.id === id) return true;
      if (!source) return false;
      return [candidate.source?.url, candidate.document_url].some(url => canonicalUrl(url) === source);
    });
    if (!item) return null;
    return (await loadDetail(item.id).catch(() => null)) || item;
  }

  async function initNormPage() {
    const shell = $("[data-norma-detail]");
    if (!shell) return;
    const params = new URLSearchParams(location.search);
    const title = $("[data-norma-title]");
    const summary = $("[data-norma-summary]");
    const metadata = $("[data-norma-meta]");
    const official = $("[data-norma-official]");
    const frame = $("[data-norma-frame]");
    const exactText = $("[data-norma-exact-text]");
    const relationsNode = $("[data-norma-relations]");

    try {
      const detail = await findLegislation(params);
      if (!detail) throw new Error("Norma não encontrada no índice publicado.");
      document.title = `${detail.title} — Suzano Aberta`;
      if (title) title.textContent = detail.title || "Norma municipal";
      if (summary) summary.textContent = detail.summary || "Ementa ou resumo não informado pela fonte.";
      renderMetadata(metadata, detail);

      const sourceUrl = detail.source?.url || detail.document_url || "";
      if (official) official.href = sourceUrl;
      const text = detail.attributes?.texto_integral || detail.attributes?.texto || "";
      if (text && exactText) {
        exactText.hidden = false;
        exactText.innerHTML = `<h2>Texto integral preservado</h2><div class="legal-text">${escapeHtml(text).replace(/\n/g, "<br>")}</div>`;
      } else if (frame && sourceUrl) {
        frame.src = sourceUrl;
        frame.title = `Texto oficial de ${detail.title || "norma municipal"}`;
      }

      const relations = await loadRelations(detail.id).catch(() => []);
      renderRelations(relationsNode, relations);
    } catch (error) {
      shell.innerHTML = `<div class="empty"><strong>Não foi possível abrir esta norma.</strong><p>${escapeHtml(error.message)}</p><p><a href="./legislacao.html">Voltar para legislação</a></p></div>`;
    }
  }

  function procurementSearchText(item) {
    return JSON.stringify(item || {}).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
  }

  function renderProcurementList(target, items) {
    if (!target) return;
    if (!items.length) {
      target.innerHTML = `<div class="empty"><strong>Nenhuma contratação encontrada.</strong><p>Experimente outro termo ou consulte o acervo completo.</p></div>`;
      return;
    }
    target.innerHTML = `<ul class="result-list">${items.slice(0, 120).map(item => {
      const attrs = item.attributes || {};
      const meta = [attrs.modalidade, attrs.situacao, attrs.processo].filter(Boolean).join(" · ");
      return `<li class="result">
        <div class="result-meta"><span class="tag">${escapeHtml(KIND_LABELS[item.kind] || item.kind)}</span><time>${escapeHtml(displayDate(item.date || item.year))}</time></div>
        <h2 class="result-title"><a href="./contratacoes.html?id=${encodeURIComponent(item.id)}">${escapeHtml(item.title)}</a></h2>
        ${item.summary ? `<p>${escapeHtml(item.summary).slice(0, 520)}</p>` : ""}
        ${meta ? `<div class="result-meta"><span>${escapeHtml(meta)}</span></div>` : ""}
      </li>`;
    }).join("")}</ul>`;
  }

  async function initProcurementPage() {
    const list = $("[data-procurement-list]");
    if (!list) return;
    try {
      const data = await fetchJsonGzip("./api/v1/contratacoes.json.gz");
      const items = Array.isArray(data.items) ? data.items : [];
      const count = $("[data-procurement-count]");
      if (count) count.textContent = new Intl.NumberFormat("pt-BR").format(items.length);

      const params = new URLSearchParams(location.search);
      const id = params.get("id");
      const source = canonicalUrl(params.get("source"));
      let focus = items.find(item => item.id === id);
      if (!focus && source) {
        focus = items.find(item => canonicalUrl(item.source?.url) === source);
      }

      const detailShell = $("[data-procurement-detail]");
      if (focus && detailShell) {
        const enriched = (await loadDetail(focus.id).catch(() => null)) || focus;
        detailShell.hidden = false;
        $("[data-procurement-detail-title]").textContent = enriched.title || "Contratação pública";
        const summary = $("[data-procurement-detail-summary]");
        if (summary) summary.textContent = enriched.summary || enriched.attributes?.objeto || "Objeto não informado.";
        renderMetadata($("[data-procurement-meta]"), enriched);

        const official = $("[data-procurement-official]");
        if (official) official.href = enriched.source?.url || "#";

        const docs = Array.isArray(enriched.attributes?.documentos) ? enriched.attributes.documentos : [];
        const docsNode = $("[data-procurement-documents]");
        if (docsNode) {
          docsNode.innerHTML = docs.length
            ? `<ul class="document-list">${docs.map(doc => `<li><a href="${escapeHtml(doc.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(doc.title || "Documento")}</a></li>`).join("")}</ul>`
            : `<p class="search-help">Nenhum anexo estruturado foi identificado nesta publicação; confira a fonte oficial.</p>`;
        }

        const publication = enriched.attributes?.texto_publicacao;
        const publicationNode = $("[data-procurement-publication]");
        if (publicationNode && publication) {
          publicationNode.innerHTML = `<div class="legal-text">${escapeHtml(publication)}</div>`;
        }

        renderRelations($("[data-procurement-relations]"), await loadRelations(enriched.id).catch(() => []));
      }

      const input = $("[data-procurement-search]");
      const update = () => {
        const q = (input?.value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR").trim();
        const filtered = q ? items.filter(item => procurementSearchText(item).includes(q)) : items;
        renderProcurementList(list, filtered);
        const filteredCount = $("[data-procurement-filtered-count]");
        if (filteredCount) filteredCount.textContent = new Intl.NumberFormat("pt-BR").format(filtered.length);
      };
      input?.addEventListener("input", update);
      update();
    } catch (error) {
      list.innerHTML = `<div class="empty"><strong>Não foi possível abrir a coleção de contratações.</strong><p>${escapeHtml(error.message)}</p></div>`;
    }
  }

  function init() {
    watchResults();
    loadNews();
    if ($("[data-news-list]")) window.setInterval(loadNews, NEWS_REFRESH_MS);
    initNormPage();
    initProcurementPage();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
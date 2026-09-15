(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const NEWS_REFRESH_MS = 30 * 60 * 1000;
  const numberFmt = new Intl.NumberFormat("pt-BR");
  const moneyFmt = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
  const dateFmt = new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium" });
  const dateTimeFmt = new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short" });
  const KIND_LABELS = { licitacao: "Licitação", contrato: "Contrato", ata: "Ata de preços" };

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, char => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
    }[char]));
  }

  function normalized(value) {
    return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR").trim();
  }

  function displayDate(value) {
    if (!value) return "Data não informada";
    const raw = String(value);
    const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (match) {
      try { return dateFmt.format(new Date(`${match[1]}-${match[2]}-${match[3]}T12:00:00Z`)); } catch (_) {}
    }
    try {
      const parsed = new Date(raw);
      if (!Number.isNaN(parsed.getTime())) return dateFmt.format(parsed);
    } catch (_) {}
    return raw;
  }

  function formatMoney(value) {
    const number = Number(value);
    return Number.isFinite(number) && number > 0 ? moneyFmt.format(number) : "";
  }

  async function fetchJsonGzip(url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    if (!("DecompressionStream" in window)) throw new Error("Navegador sem suporte à descompressão do conjunto de dados.");
    return new Response(response.body.pipeThrough(new DecompressionStream("gzip"))).json();
  }

  function shardFor(recordId) {
    let total = 0;
    for (const char of String(recordId || "")) total = (((total * 33) >>> 0) + char.codePointAt(0)) >>> 0;
    return (total & 15).toString(16);
  }

  async function loadDetail(recordId) {
    if (!recordId) return null;
    const data = await fetchJsonGzip(`./data/details/${shardFor(recordId)}.json.gz`);
    return data[recordId] || null;
  }

  async function loadRelations(recordId) {
    if (!recordId) return [];
    const data = await fetchJsonGzip(`./data/relations/${shardFor(recordId)}.json.gz`);
    return data[recordId] || [];
  }

  function newsCard(item, featured = false) {
    const official = item.origin === "prefeitura";
    const summary = String(item.summary || "").replace(/\s+/g, " ").trim();
    const label = official ? "Fonte institucional" : "Imprensa e web";
    if (featured) {
      return `<article class="news-featured">
        <div class="news-featured-top"><span class="news-source-badge${official ? " is-official" : ""}">${escapeHtml(label)}</span><time>${escapeHtml(displayDate(item.published_at))}</time></div>
        <div class="news-publisher">${escapeHtml(item.publisher || "Fonte pública")}</div>
        <h3><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)}</a></h3>
        ${summary ? `<p>${escapeHtml(summary.slice(0, 420))}${summary.length > 420 ? "…" : ""}</p>` : ""}
        <a class="news-open" href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">Abrir matéria na fonte</a>
      </article>`;
    }
    return `<article class="news-secondary">
      <div class="news-secondary-meta"><span>${escapeHtml(item.publisher || "Fonte pública")}</span><time>${escapeHtml(displayDate(item.published_at))}</time></div>
      <h3><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)}</a></h3>
      ${summary ? `<p>${escapeHtml(summary.slice(0, 180))}${summary.length > 180 ? "…" : ""}</p>` : ""}
      <a class="news-text-link" href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">Ler na fonte</a>
    </article>`;
  }

  async function loadNews() {
    const list = $("[data-news-list]");
    if (!list) return;
    const status = $("[data-news-generated]");
    try {
      const response = await fetch(`./data/news.json?t=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!Array.isArray(data.items) || data.items.length < 5) throw new Error("feed incompleto");
      const items = data.items.slice(0, 5);
      const publishers = new Set(items.map(item => normalized(item.publisher)).filter(Boolean));
      const officialCount = items.filter(item => item.origin === "prefeitura").length;
      list.innerHTML = `<div class="news-editorial-grid">
        ${newsCard(items[0], true)}
        <div class="news-secondary-grid">${items.slice(1).map(item => newsCard(item)).join("")}</div>
      </div>`;
      const sources = $("[data-news-source-summary]");
      if (sources) sources.textContent = `${publishers.size} fontes · ${officialCount} ${officialCount === 1 ? "publicação institucional" : "publicações institucionais"}`;
      if (status) {
        status.textContent = data.generated_at
          ? `Atualizado ${dateTimeFmt.format(new Date(data.generated_at))} · nova varredura a cada 30 minutos`
          : "Nova varredura a cada 30 minutos";
      }
    } catch (error) {
      list.innerHTML = `<div class="empty"><strong>As notícias não puderam ser atualizadas agora.</strong><p>O acervo principal continua disponível normalmente.</p></div>`;
      if (status) status.textContent = "Última tentativa de atualização falhou.";
    }
  }

  function sourceFamily(item) {
    const texts = [item.source?.name, item.attributes?.fonte_api, ...(item.attributes?.fontes_cruzadas || []).map(source => source.name)].join(" ").toLocaleLowerCase("pt-BR");
    if (texts.includes("pncp")) return "pncp";
    if (texts.includes("compras.gov")) return "comprasgov";
    if (texts.includes("prefeitura")) return "prefeitura";
    if (texts.includes("câmara") || texts.includes("camara")) return "camara";
    return "outra";
  }

  function allSources(item) {
    const sources = [];
    const primary = item.source || {};
    if (primary.name || primary.url) sources.push({ name: primary.name || "Fonte pública", url: primary.url || "" });
    for (const source of item.attributes?.fontes_cruzadas || []) {
      if (!sources.some(current => current.url && current.url === source.url)) sources.push(source);
    }
    return sources;
  }

  function procurementSearchText(item) {
    return normalized(JSON.stringify(item || {}));
  }

  function renderProcurementList(target, items) {
    if (!target) return;
    if (!items.length) {
      target.innerHTML = `<div class="empty"><strong>Nenhuma contratação encontrada neste filtro.</strong><p>Limpe os filtros ou tente número de processo, fornecedor, CNPJ ou objeto.</p></div>`;
      return;
    }
    target.innerHTML = `<div class="procurement-cards">${items.slice(0, 180).map(item => {
      const attrs = item.attributes || {};
      const sources = allSources(item);
      const value = formatMoney(attrs.valor_homologado || attrs.valor_estimado || attrs.valor_global || attrs.valor || attrs.valor_inicial);
      const meta = [attrs.modalidade, attrs.situacao, attrs.processo ? `Processo ${attrs.processo}` : ""].filter(Boolean);
      return `<article class="procurement-card">
        <div class="procurement-card-head"><span class="tag">${escapeHtml(KIND_LABELS[item.kind] || item.kind || "Contratação")}</span><time>${escapeHtml(displayDate(item.date || item.year))}</time></div>
        <h3><a href="./contratacoes.html?id=${encodeURIComponent(item.id)}">${escapeHtml(item.title || "Contratação pública")}</a></h3>
        ${item.summary ? `<p>${escapeHtml(String(item.summary).slice(0, 360))}${String(item.summary).length > 360 ? "…" : ""}</p>` : ""}
        ${value ? `<strong class="procurement-value">${escapeHtml(value)}</strong>` : ""}
        ${meta.length ? `<div class="procurement-meta">${meta.map(value => `<span>${escapeHtml(value)}</span>`).join("")}</div>` : ""}
        <div class="procurement-source-row"><span>${sources.length} ${sources.length === 1 ? "fonte" : "fontes"}</span><span>${escapeHtml(item.source?.name || "Fonte pública")}</span></div>
      </article>`;
    }).join("")}</div>${items.length > 180 ? `<p class="search-help">Mostrando os 180 registros mais recentes deste filtro. Refine a pesquisa para localizar os demais.</p>` : ""}`;
  }

  function renderMetadata(target, detail) {
    if (!target) return;
    const attrs = detail.attributes || {};
    const preferred = ["numero", "identifier", "numero_controle_pncp", "modalidade", "situacao", "processo", "objeto", "contractor", "contratada", "cnpj_fornecedor", "valor", "valor_estimado", "valor_homologado", "valor_global", "vigencia_inicio", "vigencia_fim"];
    const labels = {
      identifier: "Identificador", numero_controle_pncp: "Controle PNCP", modalidade: "Modalidade", situacao: "Situação",
      processo: "Processo", objeto: "Objeto", contractor: "Fornecedor", contratada: "Contratada", cnpj_fornecedor: "CNPJ do fornecedor",
      valor: "Valor", valor_estimado: "Valor estimado", valor_homologado: "Valor homologado", valor_global: "Valor global",
      vigencia_inicio: "Início da vigência", vigencia_fim: "Fim da vigência", numero: "Número"
    };
    const rows = [`<div><dt>Data</dt><dd>${escapeHtml(displayDate(detail.date || detail.year))}</dd></div>`, `<div><dt>Fonte principal</dt><dd>${escapeHtml(detail.source?.name || "Fonte pública")}</dd></div>`];
    for (const key of preferred) {
      let value = attrs[key];
      if (value === null || value === undefined || value === "" || Array.isArray(value) || typeof value === "object") continue;
      if (key.startsWith("valor")) value = formatMoney(value) || value;
      rows.push(`<div><dt>${escapeHtml(labels[key] || key)}</dt><dd>${escapeHtml(value)}</dd></div>`);
    }
    target.innerHTML = rows.join("");
  }

  function renderRelations(target, relations) {
    if (!target) return;
    if (!relations.length) {
      target.innerHTML = `<p class="search-help">Nenhuma relação determinística adicional foi encontrada.</p>`;
      return;
    }
    target.innerHTML = `<ul class="relation-list">${relations.slice(0, 40).map(item => `<li><span class="tag">${escapeHtml(item.kind || "Registro")}</span><div><strong>${escapeHtml(item.title || "Registro relacionado")}</strong><span>${escapeHtml(item.reason || "Relação documental")}</span></div></li>`).join("")}</ul>`;
  }

  async function renderProcurementDetail(focus) {
    const shell = $("[data-procurement-detail]");
    if (!focus || !shell) return;
    const detail = (await loadDetail(focus.id).catch(() => null)) || focus;
    shell.hidden = false;
    $("[data-procurement-detail-title]").textContent = detail.title || "Contratação pública";
    const summary = $("[data-procurement-detail-summary]");
    if (summary) summary.textContent = detail.summary || detail.attributes?.objeto || "Objeto não informado.";
    renderMetadata($("[data-procurement-meta]"), detail);
    const official = $("[data-procurement-official]");
    if (official) official.href = detail.attributes?.portal_url || detail.source?.url || "#";

    const docs = Array.isArray(detail.attributes?.documentos) ? detail.attributes.documentos : [];
    const docsNode = $("[data-procurement-documents]");
    if (docsNode) docsNode.innerHTML = docs.length
      ? `<ul class="document-list">${docs.map(doc => `<li><a href="${escapeHtml(doc.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(doc.title || "Documento")}</a></li>`).join("")}</ul>`
      : `<p class="search-help">Nenhum anexo foi estruturado nesta fonte. Use o botão de fonte oficial para conferir o registro original.</p>`;

    const publication = detail.attributes?.texto_publicacao;
    const publicationNode = $("[data-procurement-publication]");
    if (publicationNode) publicationNode.innerHTML = publication
      ? `<div class="legal-text">${escapeHtml(publication)}</div>`
      : `<p class="search-help">Esta fonte fornece dados estruturados, sem texto integral nesta coleção.</p>`;

    const sourceNode = $("[data-procurement-sources]");
    if (sourceNode) {
      const sources = allSources(detail);
      sourceNode.innerHTML = `<ul class="document-list">${sources.map(source => `<li>${source.url ? `<a href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.name || "Fonte")}</a>` : escapeHtml(source.name || "Fonte")}</li>`).join("")}</ul>`;
    }
    renderRelations($("[data-procurement-relations]"), await loadRelations(detail.id).catch(() => []));
  }

  async function initProcurementPage() {
    const list = $("[data-procurement-list]");
    if (!list) return;
    try {
      const data = await fetchJsonGzip("./api/v1/contratacoes.json.gz");
      const items = Array.isArray(data.items) ? data.items : [];
      const count = $("[data-procurement-count]");
      if (count) count.textContent = numberFmt.format(items.length);

      const sourceNames = new Set();
      let crossChecked = 0;
      for (const item of items) {
        const sources = allSources(item);
        sources.forEach(source => sourceNames.add(normalized(source.name || source.url)));
        if (sources.length > 1) crossChecked += 1;
      }
      const sourceCount = $("[data-procurement-source-count]");
      if (sourceCount) sourceCount.textContent = numberFmt.format([...sourceNames].filter(Boolean).length);
      const crossCount = $("[data-procurement-cross-count]");
      if (crossCount) crossCount.textContent = numberFmt.format(crossChecked);

      const params = new URLSearchParams(location.search);
      const focus = items.find(item => item.id === params.get("id"));
      if (focus) await renderProcurementDetail(focus);

      const qInput = $("[data-procurement-search]");
      const kindInput = $("[data-procurement-kind]");
      const sourceInput = $("[data-procurement-source]");
      const statusInput = $("[data-procurement-status]");

      const sourceOptions = [
        ["", "Todas as fontes"], ["pncp", "PNCP"], ["comprasgov", "Compras.gov.br"],
        ["prefeitura", "Prefeitura"], ["camara", "Câmara"]
      ];
      if (sourceInput) sourceInput.innerHTML = sourceOptions.map(([value, label]) => `<option value="${value}">${label}</option>`).join("");
      const statuses = [...new Set(items.map(item => String(item.attributes?.situacao || "").trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, "pt-BR"));
      if (statusInput) statusInput.innerHTML = `<option value="">Todas as situações</option>${statuses.map(value => `<option value="${escapeHtml(normalized(value))}">${escapeHtml(value)}</option>`).join("")}`;

      const update = () => {
        const q = normalized(qInput?.value);
        const kind = kindInput?.value || "";
        const source = sourceInput?.value || "";
        const status = statusInput?.value || "";
        const filtered = items.filter(item => {
          if (q && !procurementSearchText(item).includes(q)) return false;
          if (kind && item.kind !== kind) return false;
          if (source && sourceFamily(item) !== source && !(item.attributes?.fontes_cruzadas || []).some(entry => sourceFamily({ source: entry, attributes: {} }) === source)) return false;
          if (status && normalized(item.attributes?.situacao) !== status) return false;
          return true;
        });
        renderProcurementList(list, filtered);
        const filteredCount = $("[data-procurement-filtered-count]");
        if (filteredCount) filteredCount.textContent = numberFmt.format(filtered.length);
      };
      [qInput, kindInput, sourceInput, statusInput].forEach(node => node?.addEventListener(node?.tagName === "INPUT" ? "input" : "change", update));
      update();
    } catch (error) {
      list.innerHTML = `<div class="empty"><strong>Não foi possível abrir a coleção de contratações.</strong><p>${escapeHtml(error.message)}</p></div>`;
    }
  }

  function init() {
    loadNews();
    if ($("[data-news-list]")) window.setInterval(loadNews, NEWS_REFRESH_MS);
    initProcurementPage();
  }

  document.addEventListener("DOMContentLoaded", init);
})();

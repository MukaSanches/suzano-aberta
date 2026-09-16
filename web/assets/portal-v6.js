(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const nf = new Intl.NumberFormat("pt-BR");
  const dateFmt = new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium" });
  const dateTimeFmt = new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short" });
  const KIND_LABELS = {
    ata: "Ata de preços",
    contrato: "Contrato",
    decreto: "Decreto",
    lei: "Lei",
    licitacao: "Licitação",
    proposicao: "Proposição",
  };

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, char => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
    }[char]));
  }

  function safeHref(value, fallback = "#") {
    const raw = String(value || "").trim();
    if (raw.startsWith("./") || raw.startsWith("/")) return raw;
    try {
      const url = new URL(raw);
      return ["http:", "https:"].includes(url.protocol) ? url.href : fallback;
    } catch (_) {
      return fallback;
    }
  }

  function displayDate(value) {
    if (!value) return "Data não informada";
    const raw = String(value);
    const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (match) {
      try { return dateFmt.format(new Date(`${match[1]}-${match[2]}-${match[3]}T12:00:00Z`)); } catch (_) {}
    }
    const parsed = new Date(raw);
    return Number.isNaN(parsed.getTime()) ? raw : dateFmt.format(parsed);
  }

  async function fetchJson(url) {
    const response = await fetch(`${url}${url.includes("?") ? "&" : "?"}t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  function radarItems(items) {
    if (!Array.isArray(items) || !items.length) {
      return '<li><span class="radar-source">Nenhum item datado disponível neste recorte.</span></li>';
    }
    return items.map(item => {
      const href = safeHref(item.href);
      const external = href.startsWith("http") ? ' target="_blank" rel="noopener noreferrer"' : "";
      return `<li>
        <div class="radar-meta"><span class="radar-topic">${escapeHtml(item.topic || "Cidade")}</span><time>${escapeHtml(displayDate(item.date))}</time></div>
        <a href="${escapeHtml(href)}"${external}>${escapeHtml(item.title || "Registro público")}</a>
        <span class="radar-source">${escapeHtml(item.source || "Fonte pública")}</span>
      </li>`;
    }).join("");
  }

  function renderAutopilot(data) {
    const briefing = $("[data-autopilot-briefing]");
    if (briefing) {
      briefing.innerHTML = (data.briefing || []).map(item => `<article class="autopilot-metric">
        <small>${escapeHtml(item.label)}</small>
        <strong>${nf.format(Number(item.value) || 0)}</strong>
        <span>${escapeHtml(item.text)}</span>
      </article>`).join("");
    }

    const legislation = $("[data-autopilot-legislation]");
    if (legislation) legislation.innerHTML = radarItems(data.legislation);
    const procurements = $("[data-autopilot-procurements]");
    if (procurements) procurements.innerHTML = radarItems(data.procurements);

    const status = $("[data-autopilot-status]");
    if (status) {
      const generated = data.generated_at ? dateTimeFmt.format(new Date(data.generated_at)) : "agora";
      status.innerHTML = `<span class="autopilot-status-dot" aria-hidden="true"></span><strong>Operação automática ativa</strong><span>briefing recalculado ${escapeHtml(generated)}</span>`;
    }

    const generated = $("[data-autopilot-generated]");
    if (generated) {
      const refresh = data.refresh || {};
      generated.textContent = `Notícias: ${refresh.news_minutes || 30} min · dados incrementais: ${refresh.incremental_hours || 4} h · reconstrução completa: ${refresh.full_index_hours || 24} h`;
    }

    const sourceNode = $("[data-autopilot-sources]");
    if (sourceNode) {
      const names = (data.top_sources || []).slice(0, 5).map(item => item.name).filter(Boolean);
      sourceNode.textContent = names.length ? `Cobertura principal: ${names.join(" · ")}` : "Cobertura de fontes em atualização.";
    }
  }

  function newsCard(item, mode) {
    const href = safeHref(item.url);
    const summary = String(item.summary || "").replace(/\s+/g, " ").trim();
    const topic = item.topic || "Cidade";
    const publisher = item.publisher || "Fonte pública";
    const meta = `<div class="newsroom-meta"><span class="tag">${escapeHtml(topic)}</span><span>${escapeHtml(publisher)}</span><time>${escapeHtml(displayDate(item.published_at))}</time></div>`;
    if (mode === "lead") {
      return `<article class="newsroom-lead">${meta}<h3><a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)}</a></h3>${summary ? `<p>${escapeHtml(summary.slice(0, 520))}${summary.length > 520 ? "…" : ""}</p>` : ""}<a class="news-open" href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">Ler na fonte</a></article>`;
    }
    return `<article class="newsroom-item">${meta}<h3><a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)}</a></h3>${summary ? `<p>${escapeHtml(summary.slice(0, mode === "more" ? 150 : 210))}${summary.length > (mode === "more" ? 150 : 210) ? "…" : ""}</p>` : ""}</article>`;
  }

  function renderNews(data) {
    const list = $("[data-news-list]");
    if (!list || !Array.isArray(data.items) || data.items.length < 5) return;
    const items = data.items.slice(0, 9);
    const side = items.slice(1, 5);
    const more = items.slice(5, 9);
    const topics = Array.isArray(data.topics) ? data.topics : [...new Set(items.map(item => item.topic).filter(Boolean))];
    list.innerHTML = `
      <div class="news-topic-strip" aria-label="Temas presentes no digest">${topics.map(topic => `<span class="news-topic-chip">${escapeHtml(topic)}</span>`).join("")}</div>
      <div class="newsroom-grid">
        ${newsCard(items[0], "lead")}
        <div class="newsroom-side">${side.map(item => newsCard(item, "side")).join("")}</div>
      </div>
      ${more.length ? `<div class="newsroom-more">${more.map(item => newsCard(item, "more")).join("")}</div>` : ""}`;

    const sources = $("[data-news-source-summary]");
    if (sources) {
      const official = Number(data.official_count || 0);
      sources.textContent = `${nf.format(Number(data.publisher_count || 0))} fontes · ${nf.format(topics.length)} temas · ${nf.format(official)} ${official === 1 ? "item institucional" : "itens institucionais"}`;
    }
    const generated = $("[data-news-generated]");
    if (generated) {
      const stamp = data.generated_at ? dateTimeFmt.format(new Date(data.generated_at)) : "agora";
      generated.textContent = `Mesa automática atualizada ${stamp} · nova varredura a cada ${data.refresh_minutes || 30} minutos`;
    }
  }

  async function boot() {
    const tasks = [];
    if ($("[data-autopilot-briefing]")) {
      tasks.push(fetchJson("./data/autopilot.json").then(renderAutopilot).catch(() => {
        const status = $("[data-autopilot-status]");
        if (status) status.textContent = "Briefing automático temporariamente indisponível; o acervo continua pesquisável.";
      }));
    }
    if ($("[data-news-list]")) {
      tasks.push(fetchJson("./data/news.json").then(renderNews).catch(() => {}));
    }
    await Promise.allSettled(tasks);
  }

  document.addEventListener("DOMContentLoaded", boot);
})();

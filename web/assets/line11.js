(() => {
  "use strict";

  const widgets = [...document.querySelectorAll("[data-line11-widget]")];
  if (!widgets.length) return;

  const DATA_URL = "./data/line11-news-status.json";
  const STORAGE_KEY = "suzano-aberta:line11:news-status:v2";
  const REFRESH_MS = 5 * 60 * 1000;
  const REQUEST_TIMEOUT_MS = 6000;
  const stationOrder = ["Calmon Viana", "Suzano", "Jundiapeba", "Estudantes"];
  const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, char => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "'": "&#39;",
      '"': "&quot;",
    })[char]);
  }

  function formatTime(value) {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : dateTime.format(date);
  }

  function getStored() {
    try {
      const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      return value && typeof value === "object" ? value : null;
    } catch (_) {
      return null;
    }
  }

  function store(payload) {
    if (!payload || payload.availability === "unavailable") return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ saved_at: new Date().toISOString(), payload }));
    } catch (_) {
      // O painel continua funcional mesmo se o armazenamento local estiver bloqueado.
    }
  }

  async function fetchStatus() {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      const response = await fetch(`${DATA_URL}?v=2&t=${Date.now()}`, {
        cache: "no-store",
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`Notícias HTTP ${response.status}`);
      const payload = await response.json();
      if (!payload || payload.method !== "news-headline-estimate") {
        throw new Error("Arquivo de estimativa jornalística inválido.");
      }
      return payload;
    } finally {
      clearTimeout(timer);
    }
  }

  function isStale(payload) {
    if (!payload?.generated_at) return true;
    const generated = new Date(payload.generated_at).getTime();
    if (!Number.isFinite(generated)) return true;
    const limitMinutes = Math.max(30, Number(payload.stale_after_minutes || 90));
    return Date.now() - generated > limitMinutes * 60 * 1000;
  }

  function stateClass(payload, stale) {
    if (payload.availability === "unavailable") return "is-unavailable";
    if (stale) return "is-stale";
    if (payload.color === "red") return "is-danger";
    if (payload.color === "yellow") return "is-attention";
    if (payload.color === "green") return "is-normal";
    return "is-unavailable";
  }

  function stateLabel(payload, stale) {
    if (payload.availability === "unavailable") return "Notícias indisponíveis";
    if (stale) return "Estimativa desatualizada";
    return payload.status || "Sem leitura disponível";
  }

  function stationStrip(payload) {
    const affected = String(payload.affected_segment || "").toLocaleLowerCase("pt-BR");
    return `<ol class="line11-stations" aria-label="Trecho acompanhado">${stationOrder.map(name => {
      const classes = [
        name === "Suzano" ? "is-focus" : "",
        affected.includes(name.toLocaleLowerCase("pt-BR")) ? "is-affected" : "",
      ].filter(Boolean).join(" ");
      return `<li class="${classes}"><i aria-hidden="true"></i><span>${escapeHtml(name)}</span></li>`;
    }).join("")}</ol>`;
  }

  function signalLabel(signal) {
    if (signal === "normal") return "normalização";
    if (signal === "disruption") return "problema";
    if (signal === "attention") return "atenção";
    return "contexto";
  }

  function evidenceHtml(payload) {
    const evidence = Array.isArray(payload.evidence) ? payload.evidence.slice(0, 5) : [];
    if (!evidence.length) {
      return `<div class="line11-news-empty">Nenhuma manchete recente relevante foi encontrada para exibir.</div>`;
    }
    return `<div class="line11-news"><h4>Notícias usadas na estimativa</h4><ol>${evidence.map(item => {
      const title = escapeHtml(item.title || "Notícia sem título");
      const publisher = escapeHtml(item.publisher || "Fonte jornalística");
      const when = escapeHtml(formatTime(item.published_at) || "horário não informado");
      const signal = escapeHtml(signalLabel(item.signal));
      const url = escapeHtml(item.url || "");
      const headline = url
        ? `<a href="${url}" target="_blank" rel="noopener noreferrer">${title}</a>`
        : `<span>${title}</span>`;
      return `<li data-signal="${escapeHtml(item.signal || "context")}">${headline}<small>${publisher} · ${when} · sinal: ${signal}</small></li>`;
    }).join("")}</ol></div>`;
  }

  function render(widget, payload, { browserFallback = false } = {}) {
    const stale = browserFallback || isStale(payload);
    const className = stateClass(payload, stale);
    const generated = formatTime(payload.generated_at);
    const latest = formatTime(payload.latest_news_at);
    const summary = payload.summary || "Nenhum resumo disponível.";
    const segment = payload.affected_segment || "Nenhum trecho específico citado nas manchetes recentes";
    const reason = payload.reason || "Nenhum motivo de alteração recente identificado";
    const confidence = payload.confidence || "não informada";
    const publishers = Array.isArray(payload.publishers) ? payload.publishers.length : 0;
    const relevant = Number(payload.relevant_items || 0);

    widget.innerHTML = `<article class="line11-card ${className}">
      <header class="line11-head">
        <div><span class="line11-kicker">Linha 11–Coral · estimativa por notícias</span><h3>Estação Suzano e trecho leste</h3></div>
        <span class="line11-state">${escapeHtml(stateLabel(payload, stale))}</span>
      </header>
      ${stationStrip(payload)}
      <div class="line11-facts">
        <div><span>Leitura atual</span><strong>${escapeHtml(payload.status || "Não disponível")}</strong></div>
        <div><span>Trecho citado</span><strong>${escapeHtml(segment)}</strong></div>
        <div><span>Última evidência</span><strong>${escapeHtml(summary)}</strong></div>
        <div><span>Motivo / confiança</span><strong>${escapeHtml(reason)} · confiança ${escapeHtml(confidence)}</strong></div>
      </div>
      ${evidenceHtml(payload)}
      <footer class="line11-foot">
        <div>
          <strong>Estimativa jornalística, não telemetria oficial.</strong><br>
          <span>Gerada ${generated ? `em ${escapeHtml(generated)}` : "sem horário válido"}${latest ? ` · notícia mais recente: ${escapeHtml(latest)}` : ""} · ${relevant} itens relevantes / ${publishers} fontes.${stale ? " · estimativa marcada como desatualizada" : ""}</span>
        </div>
        <button type="button" class="line11-refresh" data-line11-refresh>Atualizar</button>
      </footer>
    </article>`;

    widget.querySelector("[data-line11-refresh]")?.addEventListener("click", () => refreshWidget(widget, true));
  }

  function renderUnavailable(widget, message) {
    const cached = getStored();
    if (cached?.payload) {
      render(widget, cached.payload, { browserFallback: true });
      return;
    }
    render(widget, {
      method: "news-headline-estimate",
      line: "Linha 11–Coral",
      availability: "unavailable",
      color: "gray",
      status: "Notícias indisponíveis no momento",
      summary: "Não foi possível carregar a estimativa baseada em notícias.",
      confidence: "indisponível",
      evidence: [],
      publishers: [],
      relevant_items: 0,
      generated_at: new Date().toISOString(),
      stale_after_minutes: 1,
      client_error: message,
    });
  }

  async function refreshWidget(widget, forced = false) {
    if (widget.dataset.loading === "true") return;
    widget.dataset.loading = "true";
    if (forced) widget.setAttribute("aria-busy", "true");
    try {
      const payload = await fetchStatus();
      store(payload);
      render(widget, payload);
    } catch (error) {
      renderUnavailable(widget, error instanceof Error ? error.message : String(error));
    } finally {
      widget.dataset.loading = "false";
      widget.removeAttribute("aria-busy");
    }
  }

  widgets.forEach(widget => refreshWidget(widget));
  const timer = setInterval(() => widgets.forEach(widget => refreshWidget(widget)), REFRESH_MS);
  addEventListener("pagehide", () => clearInterval(timer), { once: true });
})();

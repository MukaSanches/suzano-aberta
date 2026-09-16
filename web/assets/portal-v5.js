(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  function shardFor(recordId) {
    let total = 0;
    for (const char of String(recordId || "")) total = (((total * 33) >>> 0) + char.codePointAt(0)) >>> 0;
    return (total & 15).toString(16);
  }

  async function fetchJsonGzip(url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    if (!("DecompressionStream" in window)) throw new Error("Navegador sem suporte à descompressão gzip.");
    return new Response(response.body.pipeThrough(new DecompressionStream("gzip"))).json();
  }

  async function loadDetail(recordId) {
    if (!recordId) return null;
    const data = await fetchJsonGzip(`./data/details/${shardFor(recordId)}.json.gz`);
    return data[recordId] || null;
  }

  function parsePncpControl(value) {
    const match = String(value || "").trim().match(/^(\d{14})-(\d+)-(\d+)\/(\d{4})(?:-(\d+))?$/);
    if (!match) return null;
    return {
      cnpj: match[1],
      type: Number(match[2]),
      sequence: Number(match[3]),
      year: Number(match[4]),
      childSequence: match[5] ? Number(match[5]) : null,
    };
  }

  function isExactPncpDetail(url) {
    try {
      const parsed = new URL(String(url || ""));
      if (parsed.hostname !== "pncp.gov.br") return false;
      return /^\/app\/(editais|contratos)\/\d{14}\/\d{4}\/\d+\/?$/.test(parsed.pathname)
        || /^\/app\/atas\/\d{14}\/\d{4}\/\d+\/\d+\/?$/.test(parsed.pathname);
    } catch (_) {
      return false;
    }
  }

  function looksLikePncp(detail) {
    const text = [
      detail?.source?.name,
      detail?.source?.url,
      detail?.attributes?.fonte_api,
      ...(detail?.attributes?.fontes_cruzadas || []).map(item => `${item?.name || ""} ${item?.url || ""}`),
    ].join(" ").toLocaleLowerCase("pt-BR");
    return text.includes("pncp") || text.includes("pncp.gov.br");
  }

  function resolvePncpUrl(detail) {
    const attrs = detail?.attributes || {};
    const explicit = attrs.official_url || attrs.portal_url;
    if (isExactPncpDetail(explicit)) return { url: explicit, quality: "exact" };

    const control = parsePncpControl(attrs.numero_controle_pncp || attrs.numeroControlePNCP || attrs.identifier);
    const kind = String(detail?.kind || "");
    if (control) {
      if (kind === "licitacao" && control.type === 1) {
        return { url: `https://pncp.gov.br/app/editais/${control.cnpj}/${control.year}/${control.sequence}`, quality: "exact" };
      }
      if (kind === "contrato" && control.type === 2) {
        return { url: `https://pncp.gov.br/app/contratos/${control.cnpj}/${control.year}/${control.sequence}`, quality: "exact" };
      }
      if (kind === "ata" && control.type === 1 && control.childSequence) {
        return { url: `https://pncp.gov.br/app/atas/${control.cnpj}/${control.year}/${control.sequence}/${control.childSequence}`, quality: "exact" };
      }
    }

    if (kind === "ata") {
      const purchase = parsePncpControl(attrs.numero_controle_pncp_compra || attrs.numeroControlePNCPCompra);
      const ataSequence = Number(
        attrs.sequencial_ata || attrs.sequencialAta ||
        (control?.type === 3 ? control.sequence : control?.childSequence)
      );
      if (purchase?.type === 1 && Number.isFinite(ataSequence) && ataSequence > 0) {
        return { url: `https://pncp.gov.br/app/atas/${purchase.cnpj}/${purchase.year}/${purchase.sequence}/${ataSequence}`, quality: "exact" };
      }
    }

    if (!looksLikePncp(detail)) return null;
    const section = kind === "ata" ? "atas" : kind === "contrato" ? "contratos" : "editais";
    const query = attrs.numero_controle_pncp || attrs.identifier || attrs.numero || detail?.title || "";
    return { url: `https://pncp.gov.br/app/${section}?q=${encodeURIComponent(String(query))}`, quality: "search" };
  }

  function resolveOfficialUrl(detail) {
    const attrs = detail?.attributes || {};
    const stored = attrs.official_url;
    if (stored) return { url: stored, quality: attrs.official_url_quality || (isExactPncpDetail(stored) ? "exact" : "original") };
    const pncp = resolvePncpUrl(detail);
    if (pncp) return pncp;
    const source = detail?.source?.url || attrs.portal_url || "";
    return source ? { url: source, quality: "original" } : null;
  }

  function repairExplorerLayout() {
    const form = $("[data-explore-form]");
    if (!form) return;
    const shell = form.closest(".results-shell");
    const resultsColumn = shell?.querySelector("[data-results-column]");
    const active = shell?.querySelector(":scope > .active-filter-bar") || $(".active-filter-bar", shell || document);
    if (active && resultsColumn && active.parentElement !== resultsColumn) {
      resultsColumn.prepend(active);
    }
  }

  function updatePncpSourceAnchors(url) {
    $$("[data-procurement-sources] a").forEach(link => {
      if (/PNCP|Portal Nacional de Contratações Públicas/i.test(link.textContent || "")) {
        link.href = url;
        link.title = "Abrir este registro diretamente no PNCP";
      }
    });
  }

  function configureCopyButton() {
    const button = $("[data-copy-record-link]");
    if (!button) return;
    button.addEventListener("click", async () => {
      const original = button.textContent;
      try {
        await navigator.clipboard.writeText(location.href);
        button.textContent = "Link copiado";
      } catch (_) {
        const temporary = document.createElement("textarea");
        temporary.value = location.href;
        temporary.setAttribute("readonly", "");
        temporary.style.position = "fixed";
        temporary.style.opacity = "0";
        document.body.append(temporary);
        temporary.select();
        document.execCommand("copy");
        temporary.remove();
        button.textContent = "Link copiado";
      }
      window.setTimeout(() => { button.textContent = original; }, 1600);
    });
  }

  function scrollDetailIntoView(shell) {
    const rootStyles = getComputedStyle(document.documentElement);
    const raw = rootStyles.getPropertyValue("--header-offset").trim();
    const offset = Number.parseFloat(raw) || 88;
    const top = shell.getBoundingClientRect().top + window.scrollY - offset - 18;
    window.scrollTo({ top: Math.max(0, top), behavior: "auto" });
  }

  async function enhanceProcurementDetail() {
    const shell = $("[data-procurement-detail]");
    const params = new URLSearchParams(location.search);
    const recordId = params.get("id");
    if (!shell || !recordId) return;

    if ("scrollRestoration" in history) history.scrollRestoration = "manual";

    let detail = null;
    try {
      detail = await loadDetail(recordId);
    } catch (_) {
      return;
    }
    if (!detail) return;

    const resolved = resolveOfficialUrl(detail);
    const official = $("[data-procurement-official]");
    const note = $("[data-procurement-official-note]");
    if (resolved && official) {
      official.href = resolved.url;
      official.removeAttribute("aria-disabled");
      if (resolved.quality === "exact") {
        official.textContent = looksLikePncp(detail) ? "Abrir este registro no PNCP" : "Abrir registro na fonte oficial";
        if (note) {
          note.textContent = "Link direto para o registro correspondente na fonte oficial.";
          note.classList.add("is-exact");
        }
      } else if (resolved.quality === "search") {
        official.textContent = "Localizar este registro no PNCP";
        if (note) note.textContent = "O identificador é enviado para a pesquisa oficial do PNCP.";
      }
      updatePncpSourceAnchors(resolved.url);
    }

    const sources = $("[data-procurement-sources]");
    if (sources && resolved?.url) {
      const observer = new MutationObserver(() => {
        updatePncpSourceAnchors(resolved.url);
        if (sources.querySelector("a")) observer.disconnect();
      });
      observer.observe(sources, { childList: true, subtree: true });
      window.setTimeout(() => observer.disconnect(), 4000);
    }

    const waitUntilVisible = (attempt = 0) => {
      if (!shell.hidden) {
        requestAnimationFrame(() => requestAnimationFrame(() => scrollDetailIntoView(shell)));
        return;
      }
      if (attempt < 80) window.setTimeout(() => waitUntilVisible(attempt + 1), 25);
    };
    waitUntilVisible();
  }

  document.addEventListener("DOMContentLoaded", () => {
    repairExplorerLayout();
    configureCopyButton();
    enhanceProcurementDetail();
  });
})();

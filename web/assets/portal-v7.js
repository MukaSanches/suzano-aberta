(() => {
  "use strict";

  const $ = (selector, root = document) => root?.querySelector?.(selector) || null;
  const $$ = (selector, root = document) => root?.querySelectorAll ? [...root.querySelectorAll(selector)] : [];
  const mobileQuery = window.matchMedia("(max-width: 900px)");

  function pageName() {
    return location.pathname.split("/").pop() || "index.html";
  }

  function isLegislationPage() {
    return pageName() === "legislacao.html";
  }

  function rawQuery(form) {
    const input = $("[name='q']", form);
    if (input && typeof input.value === "string" && input.value.trim()) return input.value.trim();
    return (new URLSearchParams(location.search).get("q") || "").trim();
  }

  function prepareLegislationDefaults() {
    if (!isLegislationPage()) return;
    const form = $("[data-legislation-form]");
    if (!form) return;
    const params = new URLSearchParams(location.search);
    const q = (params.get("q") || "").trim();
    const kind = $("[name='kind']", form);
    const sort = $("[name='sort']", form);

    if (kind && !params.has("kind")) kind.value = form.dataset.defaultKind || "lei";
    if (sort && !params.has("sort")) sort.value = q ? (form.dataset.querySort || "relevance") : (form.dataset.defaultSort || "date_desc");
  }

  function installLegislationSearchPolicy() {
    if (!isLegislationPage()) return;
    const originalApiSearch = window.apiSearch;
    const localSearch = window.staticSearch;
    if (typeof originalApiSearch !== "function" || typeof localSearch !== "function") return;

    window.apiSearch = async payload => {
      if (payload?.scope !== "legislation") return originalApiSearch(payload);
      try {
        // O snapshot publicado junto do portal é a referência primária da interface.
        // Isso evita que uma API remota temporariamente atrasada zere ou reordene a coleção.
        return await localSearch(payload);
      } catch (_) {
        // Navegadores sem a capacidade local necessária ainda podem usar a API consultiva.
        return originalApiSearch(payload);
      }
    };
  }

  function normalizeLegislationSort(form, { submitting = false } = {}) {
    if (!form?.matches?.("[data-legislation-form]")) return;
    const q = rawQuery(form);
    const sort = $("[name='sort']", form);
    if (!sort) return;

    if (!q) {
      sort.value = form.dataset.defaultSort || "date_desc";
      delete sort.dataset.userSelected;
      return;
    }
    if (submitting && sort.dataset.userSelected !== "true") {
      sort.value = form.dataset.querySort || "relevance";
    }
  }

  function resultsColumnFor(form) {
    const shell = form.closest(".results-shell");
    if (!shell) return null;
    let column = $("[data-results-column]", shell);
    if (column) return column;
    column = [...shell.children].find(node => node !== form && node instanceof HTMLElement && !node.classList.contains("active-filter-bar") && !node.classList.contains("search-filter-toggle")) || null;
    if (column) column.setAttribute("data-results-column", "");
    return column;
  }

  function repairLayout(form) {
    const shell = form.closest(".results-shell");
    const column = resultsColumnFor(form);
    if (!shell || !column) return;
    shell.classList.add("search-layout-v7");

    const misplaced = [...shell.children].find(node => node.classList?.contains("active-filter-bar"));
    if (misplaced && misplaced.parentElement !== column) column.prepend(misplaced);
  }

  function clearTermHref() {
    const url = new URL(location.href);
    url.searchParams.delete("q");
    url.searchParams.delete("page");
    url.searchParams.set("sort", "date_desc");
    const query = url.searchParams.toString();
    return `${pageName()}${query ? `?${query}` : ""}`;
  }

  function ensureSummary(form) {
    const column = resultsColumnFor(form);
    if (!column) return null;
    let panel = $("[data-query-summary]", column);
    if (panel) return panel;

    panel = document.createElement("section");
    panel.className = "search-query-summary";
    panel.dataset.querySummary = "";
    panel.hidden = true;
    panel.setAttribute("aria-live", "polite");
    panel.innerHTML = `
      <div>
        <span class="search-query-summary-kicker">Consulta preservada</span>
        <strong data-query-echo></strong>
        <p data-query-explanation></p>
      </div>
      <a data-query-clear href="#">Remover termo</a>`;
    column.prepend(panel);
    return panel;
  }

  function collectionHeading(form) {
    if (!isLegislationPage()) return null;
    const kind = $("[name='kind']", form)?.value || "";
    if (kind === "lei") return "Leis mais recentes";
    if (kind === "decreto") return "Decretos mais recentes";
    if (kind === "proposicao") return "Proposições mais recentes";
    return "Legislação mais recente";
  }

  function updateResultHeading(form, query) {
    const column = resultsColumnFor(form);
    const heading = $(".section-head h2", column);
    if (!heading) return;
    if (!heading.dataset.v7Original) heading.dataset.v7Original = heading.textContent?.trim() || "Resultados";
    heading.classList.add("search-result-heading");
    heading.textContent = query ? `Resultados para “${query}”` : (collectionHeading(form) || heading.dataset.v7Original);
  }

  function updateDocumentTitle(query) {
    if (query) {
      if (isLegislationPage()) document.title = `${query} — Leis e proposições — Suzano Aberta`;
      else if (pageName() === "explorar.html") document.title = `${query} — Explorar o acervo — Suzano Aberta`;
      return;
    }
    if (isLegislationPage()) document.title = "Leis e proposições — Suzano Aberta";
  }

  function updateSummary(form) {
    repairLayout(form);
    const panel = ensureSummary(form);
    if (!panel) return;
    const query = rawQuery(form);
    updateResultHeading(form, query);
    updateDocumentTitle(query);

    if (!query) {
      panel.hidden = true;
      return;
    }

    panel.hidden = false;
    const echo = $("[data-query-echo]", panel);
    const explanation = $("[data-query-explanation]", panel);
    const clear = $("[data-query-clear]", panel);
    const count = $("[data-result-count]")?.textContent?.trim() || "";
    if (echo) echo.textContent = `“${query}”`;
    if (explanation) {
      explanation.textContent = `${count ? `${count}. ` : ""}O texto digitado é mantido exatamente na interface. A comparação ignora apenas diferenças de maiúsculas/minúsculas e acentos; o portal não troca o tema por sinônimos.`;
    }
    if (clear) clear.href = clearTermHref();
  }

  function syncLegislationSwitcher(form) {
    if (!isLegislationPage()) return;
    const currentKind = $("[name='kind']", form)?.value || "";
    $$('[data-kind-shortcut]').forEach(link => {
      if ((link.dataset.kindShortcut || "") === currentKind) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
  }

  function ensureFilterToggle(form) {
    const shell = form.closest(".results-shell");
    if (!shell) return null;
    let button = $(".search-filter-toggle", shell);
    if (button) return button;

    if (!form.id) form.id = `search-filters-${Math.random().toString(36).slice(2, 9)}`;
    button = document.createElement("button");
    button.type = "button";
    button.className = "search-filter-toggle";
    button.setAttribute("aria-controls", form.id);
    button.setAttribute("aria-expanded", "false");
    button.textContent = "Mostrar filtros";
    shell.insertBefore(button, form);

    button.addEventListener("click", () => {
      const expanded = button.getAttribute("aria-expanded") === "true";
      button.setAttribute("aria-expanded", String(!expanded));
      button.textContent = expanded ? "Mostrar filtros" : "Ocultar filtros";
      form.classList.toggle("is-v7-collapsed", expanded);
      if (!expanded) requestAnimationFrame(() => $("[name='q']", form)?.focus());
    });
    return button;
  }

  function syncFilterDisclosure(form) {
    const button = ensureFilterToggle(form);
    if (!button) return;
    if (mobileQuery.matches) {
      if (!form.dataset.v7DisclosureInitialized) {
        form.classList.add("is-v7-collapsed");
        button.setAttribute("aria-expanded", "false");
        button.textContent = "Mostrar filtros";
        form.dataset.v7DisclosureInitialized = "true";
      }
    } else {
      form.classList.remove("is-v7-collapsed");
      button.setAttribute("aria-expanded", "true");
      button.textContent = "Filtros";
    }
  }

  function assistedReadingUrl(result) {
    const tag = $(".tag", result)?.textContent?.trim().toLocaleLowerCase("pt-BR") || "";
    if (tag !== "lei" && tag !== "decreto") return "";
    const official = [...result.querySelectorAll("a[href]")].find(link => link.target === "_blank" && /^https?:/i.test(link.href));
    if (!official) return "";
    return `./norma.html?source=${encodeURIComponent(official.href)}`;
  }

  function enhanceLegislationCards(root) {
    if (!isLegislationPage()) return;
    $$(".result", root).forEach(result => {
      const internal = assistedReadingUrl(result);
      if (!internal) return;
      const title = $(".result-title a", result);
      if (title && !title.href.includes("norma.html")) {
        title.href = internal;
        title.removeAttribute("target");
        title.removeAttribute("rel");
      }
      const actions = $(".result-actions", result);
      if (!actions) return;
      let detail = $("[data-detail-link]", actions);
      if (!detail) {
        detail = document.createElement("a");
        detail.dataset.detailLink = "true";
        actions.prepend(detail);
      }
      detail.href = internal;
      detail.textContent = "Visualizar lei";
      const tag = $(".tag", result)?.textContent?.trim().toLocaleLowerCase("pt-BR") || "";
      if (tag === "decreto") detail.textContent = "Visualizar decreto";
    });
  }

  function watchSearch(form) {
    repairLayout(form);
    syncFilterDisclosure(form);
    normalizeLegislationSort(form);
    updateSummary(form);
    syncLegislationSwitcher(form);

    if (isLegislationPage()) {
      const reset = $(".filter-reset", form);
      if (reset) reset.textContent = "Restaurar padrão";
    }

    const shell = form.closest(".results-shell");
    const count = $("[data-result-count]");
    const results = $("[data-results]");

    const refresh = () => window.requestAnimationFrame(() => {
      updateSummary(form);
      syncLegislationSwitcher(form);
      if (results) enhanceLegislationCards(results);
    });
    form.addEventListener("submit", refresh);
    form.addEventListener("change", refresh);
    $("[name='q']", form)?.addEventListener("input", () => {
      if (!$("[name='q']", form)?.value?.trim()) refresh();
    });

    if (count) new MutationObserver(refresh).observe(count, { childList: true, subtree: true, characterData: true });
    if (results) new MutationObserver(refresh).observe(results, { childList: true, subtree: true });
    if (shell) new MutationObserver(() => repairLayout(form)).observe(shell, { childList: true });
  }

  function improveResultSemantics() {
    $$('[data-results]').forEach(root => {
      const apply = () => {
        $$(".result", root).forEach((result, index) => {
          if (result.dataset.v7Semantic !== "true") {
            result.dataset.v7Semantic = "true";
            const title = $(".result-title", result);
            if (title && !title.id) title.id = `result-title-${index}-${Math.random().toString(36).slice(2, 6)}`;
            if (title) result.setAttribute("aria-labelledby", title.id);
          }
        });
        enhanceLegislationCards(root);
      };
      apply();
      new MutationObserver(apply).observe(root, { childList: true, subtree: true });
    });
  }

  function init() {
    $$('[data-explore-form]').forEach(watchSearch);
    improveResultSemantics();
    const onViewport = () => $$('[data-explore-form]').forEach(syncFilterDisclosure);
    if (typeof mobileQuery.addEventListener === "function") mobileQuery.addEventListener("change", onViewport);
    else if (typeof mobileQuery.addListener === "function") mobileQuery.addListener(onViewport);
  }

  // Defer scripts execute after parsing. Prepare defaults before app.js runs its DOMContentLoaded search.
  prepareLegislationDefaults();
  installLegislationSearchPolicy();

  // Capture events before the app's bubble listeners so the payload uses the intended ordering.
  document.addEventListener("change", event => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    const form = target.closest("[data-legislation-form]");
    if (!form) return;
    if (target.matches("[name='sort']")) target.dataset.userSelected = "true";
    if (target.matches("[name='kind']") && !rawQuery(form)) normalizeLegislationSort(form);
  }, true);

  document.addEventListener("submit", event => {
    const target = event.target;
    if (!(target instanceof HTMLFormElement) || !target.matches("[data-legislation-form]")) return;
    normalizeLegislationSort(target, { submitting: true });
  }, true);

  document.documentElement.classList.add("portal-v7");
  document.addEventListener("DOMContentLoaded", init);
})();

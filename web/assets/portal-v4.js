(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const NAV_ITEMS = [
    ["explorar.html", "Explorar"],
    ["legislacao.html", "Legislação"],
    ["contratacoes.html", "Contratações"],
    ["sobre.html", "Sobre"],
    ["desenvolvedores.html", "Desenvolvedores"],
    ["status.html", "Status"],
  ];

  const FILTER_LABELS = {
    q: "Busca",
    scope: "Coleção",
    kind: "Tipo",
    year: "Ano",
    date_from: "Desde",
    date_to: "Até",
    sort: "Ordem",
  };

  function pageName() {
    const file = location.pathname.split("/").pop();
    return file || "index.html";
  }

  function buildNavigation() {
    const header = $(".site-header .header-inner");
    const nav = $(".site-header .nav");
    if (!header || !nav || nav.dataset.v4Ready === "true") return;
    nav.dataset.v4Ready = "true";
    nav.id = nav.id || "site-navigation";

    const current = pageName();
    nav.replaceChildren();
    for (const [href, label] of NAV_ITEMS) {
      const link = document.createElement("a");
      link.href = `./${href}`;
      link.textContent = label;
      if (current === href || (current === "norma.html" && href === "legislacao.html")) {
        link.setAttribute("aria-current", "page");
      }
      nav.append(link);
    }

    const search = document.createElement("a");
    search.href = "./explorar.html";
    search.className = "nav-primary quick-search-open";
    search.dataset.quickSearchOpen = "true";
    search.innerHTML = '<span>Pesquisar</span><kbd aria-hidden="true">/</kbd>';
    nav.append(search);

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "nav-toggle";
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-controls", nav.id);
    toggle.setAttribute("aria-label", "Abrir navegação");
    toggle.innerHTML = '<span class="nav-toggle-bars" aria-hidden="true"></span><span>Menu</span>';
    header.insertBefore(toggle, nav);

    const closeMenu = () => {
      nav.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
      toggle.setAttribute("aria-label", "Abrir navegação");
      document.body.classList.remove("nav-open");
    };

    toggle.addEventListener("click", () => {
      const open = toggle.getAttribute("aria-expanded") !== "true";
      toggle.setAttribute("aria-expanded", String(open));
      toggle.setAttribute("aria-label", open ? "Fechar navegação" : "Abrir navegação");
      nav.classList.toggle("is-open", open);
      document.body.classList.toggle("nav-open", open);
    });

    nav.addEventListener("click", event => {
      const target = event.target;
      if (target instanceof Element && target.closest("a")) closeMenu();
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape") closeMenu();
    });
    document.addEventListener("click", event => {
      if (!nav.classList.contains("is-open")) return;
      const target = event.target;
      if (target instanceof Node && !header.contains(target)) closeMenu();
    });
  }

  function setupQuickSearch() {
    if ($("#quick-search-dialog")) return;
    const dialog = document.createElement("dialog");
    dialog.id = "quick-search-dialog";
    dialog.className = "quick-search-dialog";
    dialog.setAttribute("aria-labelledby", "quick-search-title");
    dialog.innerHTML = `
      <div class="quick-search-shell">
        <div class="quick-search-head">
          <strong id="quick-search-title">Pesquisa rápida no acervo</strong>
          <button class="quick-search-close" type="button" aria-label="Fechar pesquisa">×</button>
        </div>
        <form class="quick-search-form" action="./explorar.html" method="get" role="search">
          <div>
            <label class="search-label" for="quick-q">O que você quer encontrar?</label>
            <input id="quick-q" name="q" type="search" maxlength="200" autocomplete="off" placeholder="Contrato, bairro, escola, número de lei…">
          </div>
          <button class="button" type="submit">Pesquisar</button>
        </form>
        <div class="quick-search-shortcuts" aria-label="Atalhos de pesquisa">
          <a href="./legislacao.html">Leis e proposições</a>
          <a href="./contratacoes.html">Licitações e contratos</a>
          <a href="./explorar.html?scope=documents">Documentos e arquivos</a>
          <a href="./explorar.html?sort=date_desc">Publicações recentes</a>
        </div>
        <p class="quick-search-foot">Atalho: pressione <kbd>/</kbd> ou <kbd>Ctrl</kbd> + <kbd>K</kbd> em qualquer página.</p>
      </div>`;
    document.body.append(dialog);

    const input = $("#quick-q", dialog);
    const close = $(".quick-search-close", dialog);

    const openDialog = () => {
      if (typeof dialog.showModal === "function") {
        if (!dialog.open) dialog.showModal();
      } else {
        dialog.setAttribute("open", "");
      }
      requestAnimationFrame(() => input?.focus());
    };
    const closeDialog = () => {
      if (typeof dialog.close === "function" && dialog.open) dialog.close();
      else dialog.removeAttribute("open");
    };

    close?.addEventListener("click", closeDialog);
    dialog.addEventListener("click", event => {
      if (event.target === dialog) closeDialog();
    });

    document.addEventListener("click", event => {
      const target = event.target;
      const trigger = target instanceof Element ? target.closest("[data-quick-search-open]") : null;
      if (!trigger) return;
      event.preventDefault();
      openDialog();
    });

    document.addEventListener("keydown", event => {
      const target = event.target;
      const typing = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement || (target instanceof HTMLElement && target.isContentEditable);
      const command = (event.ctrlKey || event.metaKey) && event.key.toLocaleLowerCase("pt-BR") === "k";
      const slash = event.key === "/" && !typing && !event.ctrlKey && !event.metaKey && !event.altKey;
      if (!command && !slash) return;
      event.preventDefault();
      openDialog();
    });
  }

  function enhanceFilters() {
    $$("form.filters").forEach(form => {
      if (form.dataset.v4Ready === "true") return;
      form.dataset.v4Ready = "true";
      const submit = $("button[type='submit']", form);
      if (!submit) return;

      const actions = document.createElement("div");
      actions.className = "filter-actions";
      submit.parentNode.insertBefore(actions, submit);
      actions.append(submit);

      const reset = document.createElement("button");
      reset.type = "button";
      reset.className = "filter-reset";
      reset.textContent = "Limpar";
      reset.setAttribute("aria-label", "Limpar todos os filtros");
      actions.append(reset);

      const bar = document.createElement("div");
      bar.className = "active-filter-bar";
      bar.hidden = true;
      form.parentNode.insertBefore(bar, form.nextSibling);

      const render = () => {
        const entries = [];
        for (const field of form.elements) {
          if (!(field instanceof HTMLInputElement || field instanceof HTMLSelectElement)) continue;
          if (!field.name || field.type === "hidden" || !field.value) continue;
          if (field.name === "sort" && field.value === "date_desc") continue;
          const label = FILTER_LABELS[field.name] || field.name;
          const value = field instanceof HTMLSelectElement
            ? field.options[field.selectedIndex]?.textContent?.trim() || field.value
            : field.value;
          entries.push([label, value]);
        }
        bar.replaceChildren();
        bar.hidden = entries.length === 0;
        if (!entries.length) return;

        const count = document.createElement("span");
        count.className = "filter-chip-count";
        count.textContent = `${entries.length} ${entries.length === 1 ? "filtro ativo" : "filtros ativos"}`;
        bar.append(count);
        for (const [label, value] of entries) {
          const chip = document.createElement("span");
          chip.className = "filter-chip";
          chip.textContent = `${label}: ${value}`;
          bar.append(chip);
        }
      };

      reset.addEventListener("click", () => {
        form.reset();
        form.dataset.offset = "0";
        render();
        form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      });
      form.addEventListener("change", render);
      form.addEventListener("input", render);
      render();
    });
  }

  function setupReadingProgress() {
    if (pageName() === "index.html") return;
    const bar = document.createElement("div");
    bar.className = "reading-progress";
    bar.setAttribute("aria-hidden", "true");
    document.body.prepend(bar);

    let scheduled = false;
    const update = () => {
      scheduled = false;
      const max = Math.max(1, document.documentElement.scrollHeight - innerHeight);
      const ratio = Math.min(1, Math.max(0, scrollY / max));
      bar.style.width = `${ratio * 100}%`;
    };
    addEventListener("scroll", () => {
      if (scheduled) return;
      scheduled = true;
      requestAnimationFrame(update);
    }, { passive: true });
    update();
  }

  function setupBackToTop() {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "back-to-top";
    button.setAttribute("aria-label", "Voltar ao topo");
    button.textContent = "↑";
    document.body.append(button);

    const update = () => button.classList.toggle("is-visible", scrollY > 700);
    addEventListener("scroll", update, { passive: true });
    button.addEventListener("click", () => scrollTo({ top: 0, behavior: reduceMotion.matches ? "auto" : "smooth" }));
    update();
  }

  function setupReveal() {
    if (reduceMotion.matches || !("IntersectionObserver" in window)) return;
    const nodes = $$(".stat, .card, .trust-item, .crosswalk-item, .arch-row, .procurement-source");
    if (!nodes.length) return;
    document.documentElement.classList.add("reveal-ready");
    nodes.forEach(node => node.dataset.reveal = "true");
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add("is-revealed");
        observer.unobserve(entry.target);
      }
    }, { threshold: .08, rootMargin: "0px 0px -5%" });
    nodes.forEach(node => observer.observe(node));
  }

  function hardenExternalLinks() {
    $$('a[target="_blank"]').forEach(link => {
      const rel = new Set((link.getAttribute("rel") || "").split(/\s+/).filter(Boolean));
      rel.add("noopener");
      rel.add("noreferrer");
      link.setAttribute("rel", [...rel].join(" "));
    });
  }

  function improveBrandAccessibility() {
    $$("a.brand").forEach(brand => {
      if (!brand.getAttribute("aria-label")) brand.setAttribute("aria-label", "Suzano Aberta — página inicial");
    });
    $$(".banner-dot").forEach(dot => dot.setAttribute("aria-hidden", "true"));
  }

  function registerServiceWorker() {
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("./sw.js").catch(() => {});
  }

  document.documentElement.classList.add("portal-v4");
  document.addEventListener("DOMContentLoaded", () => {
    buildNavigation();
    setupQuickSearch();
    enhanceFilters();
    setupReadingProgress();
    setupBackToTop();
    setupReveal();
    hardenExternalLinks();
    improveBrandAccessibility();
    registerServiceWorker();
  });
})();

/* Suzano Aberta — Portal v11 progressive enhancements.
 * Local-first preferences, command palette, PWA install affordance and
 * network status. No analytics, cookies or external dependencies.
 */
(() => {
  "use strict";

  const PREFS_KEY = "suzano-aberta:civic-prefs:v1";
  const RECENT_KEY = "suzano-aberta:recent-searches:v1";
  const root = document.documentElement;
  let deferredInstallPrompt = null;

  const qs = (selector, scope = document) => scope.querySelector(selector);
  const qsa = (selector, scope = document) => [...scope.querySelectorAll(selector)];

  function safeRead(key, fallback) {
    try {
      const value = localStorage.getItem(key);
      return value ? JSON.parse(value) : fallback;
    } catch (_) {
      return fallback;
    }
  }

  function safeWrite(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (_) {
      return false;
    }
  }

  function applyPrefs(prefs) {
    const textScale = ["normal", "large", "xlarge"].includes(prefs.textScale) ? prefs.textScale : "normal";
    root.dataset.textScale = textScale;
    root.dataset.highContrast = prefs.highContrast ? "true" : "false";
    root.dataset.reduceMotion = prefs.reduceMotion ? "true" : "false";

    qsa('[data-a11y-action="contrast"]').forEach(button => {
      button.setAttribute("aria-pressed", prefs.highContrast ? "true" : "false");
    });
    qsa('[data-a11y-action="motion"]').forEach(button => {
      button.setAttribute("aria-pressed", prefs.reduceMotion ? "true" : "false");
    });
    qsa('[data-a11y-action="text"]').forEach(button => {
      button.setAttribute("aria-pressed", textScale === "normal" ? "false" : "true");
      const label = textScale === "normal" ? "Aumentar texto" : textScale === "large" ? "Texto ainda maior" : "Texto normal";
      button.textContent = label;
    });
  }

  function getPrefs() {
    const saved = safeRead(PREFS_KEY, {});
    return {
      textScale: saved.textScale || "normal",
      highContrast: Boolean(saved.highContrast),
      reduceMotion: Boolean(saved.reduceMotion),
    };
  }

  function updatePrefs(mutator) {
    const next = mutator(getPrefs());
    safeWrite(PREFS_KEY, next);
    applyPrefs(next);
  }

  function initAccessibilityPanel() {
    const panel = qs("[data-a11y-popover]");
    const toggles = qsa("[data-a11y-toggle]");
    if (!panel || !toggles.length) return;

    applyPrefs(getPrefs());

    const setOpen = open => {
      panel.hidden = !open;
      toggles.forEach(button => button.setAttribute("aria-expanded", open ? "true" : "false"));
      if (open) qs("button", panel)?.focus();
    };

    toggles.forEach(button => button.addEventListener("click", () => setOpen(panel.hidden)));
    qs("[data-a11y-close]", panel)?.addEventListener("click", () => setOpen(false));

    qsa("[data-a11y-action]", panel).forEach(button => {
      button.addEventListener("click", () => {
        const action = button.dataset.a11yAction;
        if (action === "text") {
          updatePrefs(prefs => ({
            ...prefs,
            textScale: prefs.textScale === "normal" ? "large" : prefs.textScale === "large" ? "xlarge" : "normal",
          }));
        } else if (action === "contrast") {
          updatePrefs(prefs => ({ ...prefs, highContrast: !prefs.highContrast }));
        } else if (action === "motion") {
          updatePrefs(prefs => ({ ...prefs, reduceMotion: !prefs.reduceMotion }));
        } else if (action === "reset") {
          safeWrite(PREFS_KEY, { textScale: "normal", highContrast: false, reduceMotion: false });
          applyPrefs(getPrefs());
        }
      });
    });

    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && !panel.hidden) setOpen(false);
    });
  }

  const COMMANDS = [
    { label: "Início", detail: "Visão geral do portal", href: "./index.html" },
    { label: "Pesquisar tudo", detail: "Leis, documentos, compras e publicações", href: "./explorar.html" },
    { label: "Legislação", detail: "Leis, decretos e proposições", href: "./legislacao.html" },
    { label: "Contratações", detail: "Licitações, contratos e fornecedores", href: "./contratacoes.html" },
    { label: "Documentos", detail: "Arquivos e PDFs públicos", href: "./explorar.html?scope=documents" },
    { label: "Mais recentes", detail: "Registros em ordem cronológica", href: "./explorar.html?sort=date_desc" },
    { label: "Status", detail: "Saúde e atualização das fontes", href: "./status.html" },
    { label: "Acessibilidade", detail: "Recursos e compromisso de acesso", href: "./acessibilidade.html" },
    { label: "Desenvolvedores", detail: "API, dados e reutilização", href: "./desenvolvedores.html" },
    { label: "Sobre", detail: "Metodologia e independência", href: "./sobre.html" },
  ];

  function initCommandPalette() {
    const dialog = qs("#civic-command-dialog");
    if (!dialog || typeof dialog.showModal !== "function") return;
    const input = qs("[data-command-input]", dialog);
    const list = qs("[data-command-list]", dialog);
    const openButtons = qsa("[data-command-open]");
    const closeButton = qs("[data-command-close]", dialog);
    if (!input || !list) return;

    function render(term = "") {
      const normalized = term.trim().toLocaleLowerCase("pt-BR");
      const matches = COMMANDS.filter(item => !normalized || `${item.label} ${item.detail}`.toLocaleLowerCase("pt-BR").includes(normalized));
      const rows = matches.map(item => `<li><a href="${item.href}"><span>${item.label}<small>${item.detail}</small></span><span aria-hidden="true">→</span></a></li>`).join("");
      const searchRow = term.trim() ? `<li><button type="button" data-command-search><span>Pesquisar por “${escapeHtml(term.trim())}”<small>Buscar exatamente este termo no acervo</small></span><span aria-hidden="true">↵</span></button></li>` : "";
      list.innerHTML = `${searchRow}${rows || '<li><span class="empty-local">Nenhum atalho corresponde a este termo.</span></li>'}`;
      qs("[data-command-search]", list)?.addEventListener("click", () => searchTerm(term));
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
    }

    function searchTerm(value) {
      const term = value.trim();
      if (!term) return;
      rememberSearch(term);
      const params = new URLSearchParams({ q: term });
      location.href = `./explorar.html?${params}`;
    }

    function open() {
      if (!dialog.open) dialog.showModal();
      input.value = "";
      render();
      requestAnimationFrame(() => input.focus());
    }

    function close() {
      if (dialog.open) dialog.close();
    }

    openButtons.forEach(button => button.addEventListener("click", open));
    closeButton?.addEventListener("click", close);
    input.addEventListener("input", () => render(input.value));
    input.addEventListener("keydown", event => {
      if (event.key === "Enter") {
        event.preventDefault();
        searchTerm(input.value);
      }
    });
    dialog.addEventListener("click", event => {
      if (event.target === dialog) close();
    });

    document.addEventListener("keydown", event => {
      const active = document.activeElement;
      const isTyping = active && ["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName);
      if ((event.metaKey || event.ctrlKey) && event.key.toLocaleLowerCase() === "k") {
        event.preventDefault();
        open();
      } else if (event.key === "/" && !isTyping && !dialog.open) {
        event.preventDefault();
        const primarySearch = qs('[data-search-form] input[type="search"]');
        if (primarySearch) primarySearch.focus();
        else open();
      }
    });

    render();
  }

  function rememberSearch(term) {
    const clean = String(term || "").trim();
    if (!clean) return;
    const existing = safeRead(RECENT_KEY, []).filter(item => typeof item === "string" && item !== clean);
    safeWrite(RECENT_KEY, [clean, ...existing].slice(0, 6));
  }

  function renderRecentSearches() {
    const target = qs("[data-recent-searches]");
    if (!target) return;
    const items = safeRead(RECENT_KEY, []).filter(item => typeof item === "string").slice(0, 6);
    if (!items.length) {
      target.innerHTML = '<p class="empty-local">Suas buscas recentes aparecerão aqui. Elas ficam somente neste navegador.</p>';
      return;
    }
    target.innerHTML = `<div class="local-chips">${items.map(item => {
      const params = new URLSearchParams({ q: item });
      return `<a class="local-chip" href="./explorar.html?${params}">${escapeText(item)}</a>`;
    }).join("")}</div>`;
  }

  function escapeText(value) {
    return String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
  }

  function initRecentSearches() {
    qsa("[data-search-form]").forEach(form => {
      form.addEventListener("submit", () => {
        const input = qs('[name="q"]', form);
        if (input?.value?.trim()) rememberSearch(input.value);
      });
    });
    qs("[data-clear-recent]")?.addEventListener("click", () => {
      try { localStorage.removeItem(RECENT_KEY); } catch (_) { /* no-op */ }
      renderRecentSearches();
    });
    renderRecentSearches();
  }

  function updateNetworkStatus() {
    const online = navigator.onLine;
    qsa("[data-network-status]").forEach(node => {
      node.dataset.offline = online ? "false" : "true";
      node.textContent = online ? "Conectado" : "Modo offline";
      node.setAttribute("title", online ? "Conexão de rede disponível" : "Sem conexão. Conteúdo já armazenado pode continuar disponível.");
    });
  }

  function initNetworkStatus() {
    updateNetworkStatus();
    addEventListener("online", updateNetworkStatus);
    addEventListener("offline", updateNetworkStatus);
  }

  function initInstallPrompt() {
    const buttons = qsa("[data-install-app]");
    if (!buttons.length) return;
    addEventListener("beforeinstallprompt", event => {
      event.preventDefault();
      deferredInstallPrompt = event;
      buttons.forEach(button => { button.hidden = false; });
    });
    buttons.forEach(button => button.addEventListener("click", async () => {
      if (!deferredInstallPrompt) return;
      deferredInstallPrompt.prompt();
      try { await deferredInstallPrompt.userChoice; } catch (_) { /* no-op */ }
      deferredInstallPrompt = null;
      buttons.forEach(item => { item.hidden = true; });
    }));
    addEventListener("appinstalled", () => {
      deferredInstallPrompt = null;
      buttons.forEach(button => { button.hidden = true; });
    });
  }

  function init() {
    applyPrefs(getPrefs());
    initAccessibilityPanel();
    initCommandPalette();
    initRecentSearches();
    initNetworkStatus();
    initInstallPrompt();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();

(() => {
  "use strict";

  const KINDS = ["lei", "decreto", "proposicao"];
  const PAGE_SIZE = 40;
  const shardPromises = new Map();
  let indexPromise = null;
  const prepared = new WeakMap();

  function fold(value) {
    return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR").replace(/[^a-z0-9\s./-]/g, " ").replace(/\s+/g, " ").trim();
  }
  function effectiveDate(item) {
    if (item?.effective_date) return String(item.effective_date);
    if (item?.date) return String(item.date);
    if (item?.year) return `${item.year}-01-01`;
    return "";
  }
  function sourceName(item) { const source = item?.source || {}; return String(source.name || item?.source_name || "Fonte pública"); }
  function prepare(item) {
    let cached = prepared.get(item);
    if (cached) return cached;
    const title = fold(item?.title), summary = fold(item?.summary), source = fold(sourceName(item)), id = fold(item?.id);
    cached = { title, summary, source, text: `${title} ${summary} ${source} ${id}`.trim(), date: effectiveDate(item), year: Number(item?.year || String(effectiveDate(item)).slice(0, 4) || 0) };
    prepared.set(item, cached);
    return cached;
  }
  function queryTokens(query) { return [...new Set(fold(query).split(" ").filter(token => token.length >= 2))].slice(0, 10); }
  function relevanceScore(item, clean, tokens) {
    if (!clean) return 0;
    const fields = prepare(item);
    let score = 0;
    if (fields.title === clean) score += 1000; else if (fields.title.includes(clean)) score += 650;
    if (fields.summary.includes(clean)) score += 320;
    if (fields.source.includes(clean)) score += 80;
    for (const token of tokens) {
      if (fields.title.includes(token)) score += 110; else if (fields.summary.includes(token)) score += 45; else if (fields.source.includes(token)) score += 12;
    }
    return score;
  }
  async function fetchJson(path) {
    const response = await fetch(path, { cache: "default" });
    if (!response.ok) throw new Error(`HTTP ${response.status} ao carregar ${path}`);
    return response.json();
  }
  function loadIndex() {
    if (!indexPromise) indexPromise = fetchJson("../data/legislation-index.json?v=3").then(payload => { if (!payload?.meta) throw new Error("Índice legislativo inválido."); return payload.meta; });
    return indexPromise;
  }
  function loadShard(kind) {
    if (!KINDS.includes(kind)) throw new Error(`Categoria legislativa inválida: ${kind}`);
    if (!shardPromises.has(kind)) shardPromises.set(kind, fetchJson(`../data/legislation-${kind}.json?v=3`).then(payload => { if (!Array.isArray(payload?.items)) throw new Error(`Shard ${kind} inválido.`); return payload.items; }));
    return shardPromises.get(kind);
  }
  async function warm(kind) {
    const selected = KINDS.includes(kind) ? kind : "lei";
    await Promise.all([loadIndex(), loadShard(selected)]);
    for (const item of await loadShard(selected)) prepare(item);
  }
  async function loadCandidates(kind) {
    if (kind && KINDS.includes(kind)) return loadShard(kind);
    const merged = (await Promise.all(KINDS.map(loadShard))).flat();
    merged.sort((a, b) => effectiveDate(b).localeCompare(effectiveDate(a)) || String(a.id || "").localeCompare(String(b.id || "")));
    return merged;
  }
  async function search(payload) {
    const [meta, candidates] = await Promise.all([loadIndex(), loadCandidates(String(payload.kind || ""))]);
    const clean = fold(payload.query || ""), tokens = queryTokens(clean), requestedYear = Number(payload.year || 0), dateFrom = String(payload.date_from || ""), dateTo = String(payload.date_to || "");
    let matches = [];
    for (const item of candidates) {
      const fields = prepare(item);
      if (requestedYear && fields.year !== requestedYear) continue;
      if (dateFrom && (!fields.date || fields.date < dateFrom)) continue;
      if (dateTo && (!fields.date || fields.date > dateTo)) continue;
      if (clean && !fields.text.includes(clean) && !(tokens.length && tokens.every(token => fields.text.includes(token)))) continue;
      matches.push(item);
    }
    const sort = String(payload.sort || (clean ? "relevance" : "date_desc"));
    if (sort === "date_asc") matches = matches.slice().reverse();
    else if (sort === "relevance" && clean) matches = matches.map(item => ({ item, score: relevanceScore(item, clean, tokens) })).sort((a, b) => b.score - a.score || effectiveDate(b.item).localeCompare(effectiveDate(a.item))).map(entry => entry.item);
    const limit = Math.max(1, Math.min(100, Number(payload.limit || PAGE_SIZE))), offset = Math.max(0, Number(payload.offset || 0));
    return { total: matches.length, items: matches.slice(offset, offset + limit), meta, loaded_kind: payload.kind || "all" };
  }
  self.onmessage = async event => {
    const type = event.data?.type || "search";
    if (type === "warm") { try { await warm(String(event.data?.kind || "lei")); } catch (_) {} return; }
    const id = event.data?.id;
    try { self.postMessage({ id, ok: true, result: await search(event.data?.payload || {}) }); }
    catch (error) { self.postMessage({ id, ok: false, error: error instanceof Error ? error.message : String(error) }); }
  };
})();

const DATA_ROOT = "../data/";
const shardCache = new Map();
let recordsPromise;
let lexiconPromise;

const DOCUMENT_KINDS = new Set([
  "arquivo", "arquivo_historico", "diario", "documento_fiscal", "documento_orcamentario", "lei", "decreto"
]);
const LEGISLATION_KINDS = new Set(["lei", "decreto", "proposicao"]);
const LOW_SIGNAL_KINDS = new Set([
  "pagina_web", "noticia", "vereador", "sessao", "comissao", "secretaria", "presenca"
]);
const BOILERPLATE_HINTS = [
  "acessibilidade", "menu principal", "ir para a pesquisa", "rodape", "aumentar fonte",
  "diminuir fonte", "alto contraste", "assine nosso informativo", "selo de acessibilidade"
];

function normalize(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function fold(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function queryTokens(clean) {
  return [...new Set(String(clean || "").split(" ").filter(token => token.length >= 2))].slice(0, 8);
}

function words(value) {
  const clean = normalize(value);
  return clean ? clean.split(" ") : [];
}

function tokenCoverage(value, tokens) {
  if (!tokens.length) return 0;
  const terms = words(value);
  if (!terms.length) return 0;
  let hits = 0;
  for (const token of tokens) {
    if (terms.some(term => term.startsWith(token))) hits += 1;
  }
  return hits / tokens.length;
}

function minTokenSpan(value, tokens) {
  if (!tokens.length) return Number.POSITIVE_INFINITY;
  const terms = words(value);
  if (!terms.length) return Number.POSITIVE_INFINITY;
  const matched = terms.map(term => tokens.findIndex(token => term.startsWith(token)));
  const counts = Array(tokens.length).fill(0);
  let covered = 0;
  let left = 0;
  let best = Number.POSITIVE_INFINITY;

  for (let right = 0; right < matched.length; right += 1) {
    const tokenIndex = matched[right];
    if (tokenIndex >= 0) {
      if (counts[tokenIndex] === 0) covered += 1;
      counts[tokenIndex] += 1;
    }
    while (covered === tokens.length && left <= right) {
      best = Math.min(best, right - left + 1);
      const leftIndex = matched[left];
      if (leftIndex >= 0) {
        counts[leftIndex] -= 1;
        if (counts[leftIndex] === 0) covered -= 1;
      }
      left += 1;
    }
  }
  return best;
}

function boilerplatePenalty(row) {
  if (!LOW_SIGNAL_KINDS.has(String(row?.[1] || ""))) return 0;
  const title = normalize(row?.[2]);
  const summary = normalize(row?.[8]);
  let penalty = BOILERPLATE_HINTS.reduce((total, hint) => total + (summary.includes(hint) ? 18 : 0), 0);
  if (["camara municipal de suzano", "prefeitura de suzano", "prefeitura municipal de suzano"].includes(title)) {
    penalty += 120;
  }
  return penalty;
}

function isMeaningfulCandidate(row, clean) {
  if (!clean) return true;
  const kind = String(row?.[1] || "");
  if (!LOW_SIGNAL_KINDS.has(kind)) return true;

  const tokens = queryTokens(clean);
  if (!tokens.length) return false;
  const title = normalize(row?.[2]);
  const summary = normalize(row?.[8]);
  const combined = `${title} ${summary}`.trim();
  if (title.includes(clean) || summary.includes(clean)) return true;

  const coverage = tokenCoverage(combined, tokens);
  if (coverage < 1) return false;
  if (tokens.length === 1) return true;
  return minTokenSpan(combined, tokens) <= 12;
}

function relevanceScore(row, clean) {
  if (!clean) return 0;
  const tokens = queryTokens(clean);
  const title = normalize(row?.[2]);
  const summary = normalize(row?.[8]);
  const source = normalize(row?.[5]);
  const combined = `${title} ${summary}`.trim();
  const titleCoverage = tokenCoverage(title, tokens);
  const summaryCoverage = tokenCoverage(summary, tokens);
  const combinedCoverage = tokenCoverage(combined, tokens);
  const span = minTokenSpan(combined, tokens);
  let score = 0;

  if (title === clean) score += 900;
  else if (title.includes(clean)) score += 620;
  if (summary.includes(clean)) score += 360;
  score += Math.round(titleCoverage * 320);
  score += Math.round(summaryCoverage * 170);
  if (combinedCoverage === 1) score += 180;
  if (Number.isFinite(span)) score += Math.max(0, 150 - (span - 1) * 10);
  if (tokens.some(token => source.split(" ").some(term => term.startsWith(token)))) score += 8;
  if (!LOW_SIGNAL_KINDS.has(String(row?.[1] || ""))) score += 35;
  score -= boilerplatePenalty(row);
  return score;
}

function contextualSummary(value, clean, radius = 190) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (!text || !clean) return text;
  const haystack = fold(text);
  const phrase = fold(clean);
  const tokens = queryTokens(clean);
  let index = phrase ? haystack.indexOf(phrase) : -1;
  if (index < 0) {
    for (const token of tokens) {
      index = haystack.indexOf(token);
      if (index >= 0) break;
    }
  }
  if (index < 0) return text;
  const start = Math.max(0, index - radius);
  const end = Math.min(text.length, index + Math.max(phrase.length, 24) + radius);
  return `${start > 0 ? "…" : ""}${text.slice(start, end).trim()}${end < text.length ? "…" : ""}`;
}

async function fetchJsonGzip(url) {
  const response = await fetch(url, { cache: "force-cache" });
  if (!response.ok) throw new Error(`Falha ao carregar ${url}: HTTP ${response.status}`);
  if (!("DecompressionStream" in self)) {
    throw new Error("Este navegador não oferece descompressão nativa necessária ao índice local.");
  }
  const stream = response.body.pipeThrough(new DecompressionStream("gzip"));
  return new Response(stream).json();
}

function getRecords() {
  recordsPromise ||= fetchJsonGzip(`${DATA_ROOT}records.json.gz`);
  return recordsPromise;
}

function getLexicon() {
  lexiconPromise ||= fetchJsonGzip(`${DATA_ROOT}lexicon.json.gz`);
  return lexiconPromise;
}

function lowerBound(values, target) {
  let lo = 0;
  let hi = values.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (values[mid] < target) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

function prefixMatches(lexicon, token, limit = 40) {
  const start = lowerBound(lexicon, token);
  const out = [];
  for (let i = start; i < lexicon.length && out.length < limit; i += 1) {
    if (!lexicon[i].startsWith(token)) break;
    out.push(lexicon[i]);
  }
  return out;
}

function shardFor(token) {
  const a = token.charCodeAt(0) || 0;
  const b = token.charCodeAt(1) || 0;
  return ((a * 31 + b) & 31).toString(16).padStart(2, "0");
}

async function getShard(name) {
  if (!shardCache.has(name)) {
    shardCache.set(name, fetchJsonGzip(`${DATA_ROOT}index/${name}.json.gz`));
  }
  return shardCache.get(name);
}

function unionPostingLists(lists) {
  const result = new Set();
  for (const list of lists) for (const id of list) result.add(id);
  return result;
}

function intersectSets(sets) {
  if (!sets.length) return new Set();
  const ordered = [...sets].sort((a, b) => a.size - b.size);
  const result = new Set(ordered[0]);
  for (let i = 1; i < ordered.length; i += 1) {
    for (const value of result) if (!ordered[i].has(value)) result.delete(value);
    if (!result.size) break;
  }
  return result;
}

function recordObject(row, clean = "") {
  return {
    id: row[0], kind: row[1], title: row[2], date: row[3], year: row[4],
    source_name: row[5], source_url: row[6], last_seen: row[7],
    summary: contextualSummary(row[8] || "", clean),
    effective_date: row[9] || "", date_basis: row[10] || "observed"
  };
}

function inScope(row, scope) {
  if (scope === "documents") return DOCUMENT_KINDS.has(row?.[1]);
  if (scope === "legislation") return LEGISLATION_KINDS.has(row?.[1]);
  return true;
}

function filterIds(ids, records, { scope, kind, year, date_from, date_to }) {
  return ids.filter(index => {
    const row = records[index];
    if (!row || !inScope(row, scope)) return false;
    if (kind && row[1] !== kind) return false;
    if (year && Number(row[4]) !== Number(year)) return false;
    const effective = String(row[9] || "");
    if (date_from && (!effective || effective < date_from)) return false;
    if (date_to && (!effective || effective > date_to)) return false;
    return true;
  });
}

function sortIds(ids, records, clean, sort) {
  ids.sort((left, right) => {
    const a = records[left];
    const b = records[right];
    if (sort === "relevance" && clean) {
      const aScore = relevanceScore(a, clean);
      const bScore = relevanceScore(b, clean);
      if (aScore !== bScore) return bScore - aScore;
    }
    const ad = String(a?.[9] || "");
    const bd = String(b?.[9] || "");
    if (ad !== bd) return sort === "date_asc" ? ad.localeCompare(bd) : bd.localeCompare(ad);
    return String(a?.[0] || "").localeCompare(String(b?.[0] || ""));
  });
}

async function matchingIds(query, records) {
  const clean = normalize(query);
  if (!clean) return { clean, ids: records.map((_, index) => index) };
  const tokens = queryTokens(clean);
  if (!tokens.length) return { clean, ids: [] };
  const lexicon = await getLexicon();
  const sets = [];
  for (const queryToken of tokens) {
    const tokenMatches = prefixMatches(lexicon, queryToken);
    if (!tokenMatches.length) return { clean, ids: [] };
    const byShard = new Map();
    for (const token of tokenMatches) {
      const shard = shardFor(token);
      if (!byShard.has(shard)) byShard.set(shard, []);
      byShard.get(shard).push(token);
    }
    const postings = [];
    for (const [shardName, matchedTokens] of byShard) {
      const shard = await getShard(shardName);
      for (const token of matchedTokens) if (shard[token]) postings.push(shard[token]);
    }
    sets.push(unionPostingLists(postings));
  }
  return { clean, ids: [...intersectSets(sets)] };
}

async function searchStatic(payload) {
  const records = await getRecords();
  const { clean, ids: matched } = await matchingIds(payload.query || "", records);
  let ids = filterIds(matched, records, payload);
  if (clean) ids = ids.filter(index => isMeaningfulCandidate(records[index], clean));
  sortIds(ids, records, clean, payload.sort || (clean ? "relevance" : "date_desc"));
  const offset = Number(payload.offset || 0);
  const limit = Number(payload.limit || 30);
  const page = ids.slice(offset, offset + limit).map(index => recordObject(records[index], clean));
  return { total: ids.length, items: page };
}

self.onmessage = async event => {
  const { id, payload } = event.data;
  try {
    const result = await searchStatic(payload);
    self.postMessage({ id, ok: true, result });
  } catch (error) {
    self.postMessage({ id, ok: false, error: error instanceof Error ? error.message : String(error) });
  }
};

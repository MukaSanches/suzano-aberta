const DATA_ROOT = "../data/";
const shardCache = new Map();
let recordsPromise;
let lexiconPromise;

function normalize(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
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

function recordObject(row) {
  return {
    id: row[0], kind: row[1], title: row[2], date: row[3], year: row[4],
    source_name: row[5], source_url: row[6], last_seen: row[7], summary: row[8] || ""
  };
}

async function searchStatic({ query, kind, year, limit = 30, offset = 0 }) {
  const clean = normalize(query);
  if (!clean) return { total: 0, items: [] };
  const queryTokens = clean.split(" ").filter(token => token.length >= 2).slice(0, 8);
  if (!queryTokens.length) return { total: 0, items: [] };

  const [lexicon, records] = await Promise.all([getLexicon(), getRecords()]);
  const sets = [];
  for (const queryToken of queryTokens) {
    const tokenMatches = prefixMatches(lexicon, queryToken);
    if (!tokenMatches.length) return { total: 0, items: [] };
    const byShard = new Map();
    for (const token of tokenMatches) {
      const shard = shardFor(token);
      if (!byShard.has(shard)) byShard.set(shard, []);
      byShard.get(shard).push(token);
    }
    const postings = [];
    for (const [shardName, tokens] of byShard) {
      const shard = await getShard(shardName);
      for (const token of tokens) if (shard[token]) postings.push(shard[token]);
    }
    sets.push(unionPostingLists(postings));
  }

  let ids = [...intersectSets(sets)];
  if (kind) ids = ids.filter(index => records[index]?.[1] === kind);
  if (year) ids = ids.filter(index => Number(records[index]?.[4]) === Number(year));

  ids.sort((left, right) => {
    const a = records[left];
    const b = records[right];
    const at = normalize(a?.[2]);
    const bt = normalize(b?.[2]);
    const aExact = at.includes(clean) ? 1 : 0;
    const bExact = bt.includes(clean) ? 1 : 0;
    if (aExact !== bExact) return bExact - aExact;
    const ay = Number(a?.[4] || 0);
    const by = Number(b?.[4] || 0);
    if (ay !== by) return by - ay;
    return String(b?.[7] || "").localeCompare(String(a?.[7] || ""));
  });

  const page = ids.slice(offset, offset + limit).map(index => recordObject(records[index]));
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

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const assetRoot = path.join(root, "web", "assets");
const workerPath = path.join(assetRoot, "search-worker.js");
const source = fs.readFileSync(workerPath, "utf8");

async function localFetch(url) {
  const candidate = path.resolve(assetRoot, String(url));
  const dataRoot = path.resolve(root, "web", "data");
  if (!candidate.startsWith(`${dataRoot}${path.sep}`)) {
    return new Response("not found", { status: 404 });
  }
  if (!fs.existsSync(candidate)) return new Response("not found", { status: 404 });
  return new Response(fs.readFileSync(candidate), { status: 200 });
}

const context = vm.createContext({
  self: { postMessage() {} },
  console,
  fetch: localFetch,
  Response,
  DecompressionStream,
});
vm.runInContext(source, context, { filename: "search-worker.js" });
const searchStatic = vm.runInContext("searchStatic", context);

const legislationKinds = new Set(["lei", "decreto", "proposicao"]);
const genericTitles = new Set([
  "camara municipal de suzano",
  "prefeitura de suzano",
  "prefeitura municipal de suzano",
]);
const normalized = value => String(value || "")
  .normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "")
  .toLowerCase()
  .trim();

const mobility = await searchStatic({
  query: "MOBILIDADE",
  scope: "legislation",
  kind: "",
  year: "",
  date_from: "",
  date_to: "",
  sort: "relevance",
  limit: 20,
  offset: 0,
});
assert.ok(mobility.total > 0, "o snapshot real precisa responder à consulta MOBILIDADE");
assert.ok(mobility.items.length > 0, "MOBILIDADE precisa retornar uma primeira página");
assert.ok(mobility.items.every(item => legislationKinds.has(item.kind)), "a coleção legislativa não pode vazar outros tipos");
assert.ok(mobility.items.every(item => !genericTitles.has(normalized(item.title))), "páginas institucionais genéricas não podem liderar a legislação");
assert.ok(
  mobility.items.slice(0, 10).some(item => normalized(`${item.title} ${item.summary}`).includes("mobilidade")),
  "os primeiros resultados de MOBILIDADE precisam explicar a correspondência",
);

const schoolTransport = await searchStatic({
  query: "transporte escolar",
  scope: "",
  kind: "",
  year: "",
  date_from: "",
  date_to: "",
  sort: "relevance",
  limit: 20,
  offset: 0,
});
assert.ok(schoolTransport.total > 0, "o snapshot real precisa responder a transporte escolar");
assert.ok(schoolTransport.items.length > 0, "transporte escolar precisa retornar uma primeira página");
assert.ok(
  schoolTransport.items.slice(0, 10).every(item => !genericTitles.has(normalized(item.title))),
  "boilerplate institucional não pode ocupar o topo de transporte escolar",
);
assert.ok(
  schoolTransport.items.slice(0, 10).some(item => {
    const text = normalized(`${item.title} ${item.summary}`);
    return text.includes("transporte") && text.includes("escolar");
  }),
  "os primeiros resultados de transporte escolar precisam mostrar evidência textual",
);

console.log(JSON.stringify({
  mobility_total: mobility.total,
  mobility_top: mobility.items.slice(0, 3).map(item => item.title),
  school_transport_total: schoolTransport.total,
  school_transport_top: schoolTransport.items.slice(0, 3).map(item => item.title),
}, null, 2));

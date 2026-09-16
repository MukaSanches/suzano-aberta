import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync(new URL("../web/assets/search-worker.js", import.meta.url), "utf8");
const context = vm.createContext({ self: { postMessage() {} }, console });
vm.runInContext(source, context, { filename: "search-worker.js" });

const genericNoise = [
  "page:1", "pagina_web", "Câmara Municipal de Suzano", "2026-09-15", 2026,
  "Câmara Municipal de Suzano", "https://example.test", "",
  "Acessibilidade Conteúdo Menu principal Ir para a pesquisa Rodapé Alto Contraste Pesquisar", "2026-09-15", "record", ""
];
const genericRelevant = [
  "page:2", "pagina_web", "Prefeitura amplia transporte escolar gratuito", "2026-09-14", 2026,
  "Prefeitura de Suzano", "https://example.test/2", "",
  "Novo serviço de transporte escolar atende estudantes da rede municipal.", "2026-09-14", "record", ""
];
const structuredHiddenEvidence = [
  "lei:1", "lei", "Lei Municipal nº 100", "2026-09-16", 2026,
  "Legislação Municipal Consolidada", "https://example.test/3", "", "Dispõe sobre políticas públicas municipais.", "2026-09-16", "record",
  "ementa: Institui diretrizes de mobilidade urbana e transporte coletivo no Município."
];

const isMeaningfulCandidate = vm.runInContext("isMeaningfulCandidate", context);
assert.equal(isMeaningfulCandidate(genericNoise, "transporte escolar"), false);
assert.equal(isMeaningfulCandidate(genericRelevant, "transporte escolar"), true);
assert.equal(isMeaningfulCandidate(structuredHiddenEvidence, "mobilidade"), true);

const relevanceScore = vm.runInContext("relevanceScore", context);
assert.ok(relevanceScore(genericRelevant, "transporte escolar") > relevanceScore(genericNoise, "transporte escolar"));
assert.ok(relevanceScore(structuredHiddenEvidence, "mobilidade") > 100);

const contextualSummary = vm.runInContext("contextualSummary", context);
const longText = `${"introdução ".repeat(60)}O programa de transporte escolar atende a zona rural. ${"final ".repeat(30)}`;
const snippet = contextualSummary(longText, "transporte escolar", 60);
assert.match(snippet, /transporte escolar/i);
assert.ok(snippet.startsWith("…"));
assert.ok(snippet.length < longText.length);

const recordObject = vm.runInContext("recordObject", context);
const structuredResult = recordObject(structuredHiddenEvidence, "mobilidade");
assert.match(structuredResult.summary, /mobilidade urbana/i);

const tokenMatchesForQuery = vm.runInContext("tokenMatchesForQuery", context);
const lexicon = ["mobilidade", "mobilidades", "mobilidade-urbana", "mobiliario", "transporte"];
assert.deepEqual([...tokenMatchesForQuery(lexicon, "mobilidade")], ["mobilidade"]);
assert.deepEqual([...tokenMatchesForQuery(lexicon, "mobili")], ["mobiliario"]);

console.log("search-worker relevance contract: ok");

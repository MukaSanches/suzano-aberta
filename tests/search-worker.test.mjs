import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync(new URL("../web/assets/search-worker.js", import.meta.url), "utf8");
const context = vm.createContext({ self: { postMessage() {} }, console });
vm.runInContext(source, context, { filename: "search-worker.js" });

const genericNoise = [
  "page:1", "pagina_web", "Câmara Municipal de Suzano", "2026-09-15", 2026,
  "Câmara Municipal de Suzano", "https://example.test", "",
  "Acessibilidade Conteúdo Menu principal Ir para a pesquisa Rodapé Alto Contraste Pesquisar", "2026-09-15", "record"
];
const genericRelevant = [
  "page:2", "pagina_web", "Prefeitura amplia transporte escolar gratuito", "2026-09-14", 2026,
  "Prefeitura de Suzano", "https://example.test/2", "",
  "Novo serviço de transporte escolar atende estudantes da rede municipal.", "2026-09-14", "record"
];
const structuredHiddenEvidence = [
  "proc:1", "licitacao", "Pregão eletrônico 10/2026", "2026-09-16", 2026,
  "PNCP", "https://example.test/3", "", "Contratação de serviços para a Secretaria de Educação.", "2026-09-16", "record"
];

const isMeaningfulCandidate = vm.runInContext("isMeaningfulCandidate", context);
assert.equal(isMeaningfulCandidate(genericNoise, "transporte escolar"), false);
assert.equal(isMeaningfulCandidate(genericRelevant, "transporte escolar"), true);
assert.equal(isMeaningfulCandidate(structuredHiddenEvidence, "transporte escolar"), true);

const relevanceScore = vm.runInContext("relevanceScore", context);
assert.ok(relevanceScore(genericRelevant, "transporte escolar") > relevanceScore(structuredHiddenEvidence, "transporte escolar"));
assert.ok(relevanceScore(genericRelevant, "transporte escolar") > relevanceScore(genericNoise, "transporte escolar"));

const contextualSummary = vm.runInContext("contextualSummary", context);
const longText = `${"introdução ".repeat(60)}O programa de transporte escolar atende a zona rural. ${"final ".repeat(30)}`;
const snippet = contextualSummary(longText, "transporte escolar", 60);
assert.match(snippet, /transporte escolar/i);
assert.ok(snippet.startsWith("…"));
assert.ok(snippet.length < longText.length);

console.log("search-worker relevance contract: ok");

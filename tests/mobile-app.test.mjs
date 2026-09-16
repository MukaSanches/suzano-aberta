import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const read = path => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

test('mobile shell exposes all five primary destinations', async () => {
  const html = await read('web/app/index.html');
  for (const name of ['home','explore','follow','status','more']) {
    assert.match(html, new RegExp(`data-nav="${name}"`));
    assert.match(html, new RegExp(`data-view="${name}"`));
  }
});

test('mobile shell clearly identifies project independence', async () => {
  const html = await read('web/app/index.html');
  assert.match(html, /Projeto cívico independente/);
  assert.match(html, /fonte responsável continua sendo a referência oficial/);
});

test('app contains resilient data paths and autonomous refresh', async () => {
  const js = await read('web/app/app.js');
  assert.match(js, /data\/manifest\.json/);
  assert.match(js, /data\/autopilot\.json/);
  assert.match(js, /data\/news\.json/);
  assert.match(js, /search-worker\.js/);
  assert.match(js, /5\*60\*1000/);
  assert.match(js, /serviceWorker/);
});

test('android shell is remote-first and has an offline fallback', async () => {
  const java = await read('mobile/android/app/src/main/java/br/com/suzanoaberta/app/MainActivity.java');
  assert.match(java, /https:\/\/mukasanches\.github\.io\/suzano-aberta\/app\//);
  assert.match(java, /file:\/\/\/android_asset\/www\/index\.html/);
  assert.match(java, /MIXED_CONTENT_NEVER_ALLOW/);
  assert.match(java, /setAcceptThirdPartyCookies\(webView, false\)/);
});

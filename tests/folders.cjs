// Run with: node tests/folders.cjs. Executes the page's real folder renderer.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'public/index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {
    innerHTML: '', options: [], dataset: {}, style: { setProperty() {} },
    classList: { toggle() {}, contains() { return false; } },
    addEventListener() {}, setAttribute() {}, removeAttribute() {},
    querySelector() { return null; }, querySelectorAll() { return []; },
  });
  return elements.get(id);
}
let columns = 6;
const context = vm.createContext({
  URL, URLSearchParams, console,
  location: new URL('https://preview.example/?lang=zh&view=library'),
  localStorage: { getItem() { return null; } },
  document: { getElementById: element, documentElement: { style: { setProperty() {} } }, body: element('body'), addEventListener() {} },
  getComputedStyle() { return { getPropertyValue() { return String(columns); } }; },
  matchMedia() { return { matches: false, addEventListener() {} }; },
  addEventListener() {}, setTimeout() {}, clearTimeout() {}, setInterval() {}, history: {},
});
vm.runInContext(script.replace('tick(); setInterval(tick, 15000);\nload();', ''), context);
context.inputData = JSON.parse(fs.readFileSync(path.join(root, 'demo/data.json'), 'utf8'));
const run = code => vm.runInContext(code, context);
const output = () => element('main').innerHTML;
run('state.data=inputData; state.animate=false; render();');
const keys = [...output().matchAll(/data-folder="([^"]+)"/g)].map(m => m[1]);
assert(keys.length > 1);
assert(!output().includes('folder-panel"'), 'folders start closed');
assert(!output().includes('<h1>'), 'no added Start title');
let covered = 0;
for (const key of keys) {
  run(`toggleFolder(${JSON.stringify(key)})`);
  assert.equal([...output().matchAll(/class="folder-panel"/g)].length, 1);
  assert(output().includes(`id="folder-${key}"`));
  assert.equal([...output().matchAll(/aria-expanded="true"/g)].length, 1);
  const panel = output().split('class="folder-panel"')[1].split('</section>')[0];
  covered += [...panel.matchAll(/class="tile /g)].length;
  const indices = [...output().matchAll(/data-i="(\d+)"/g)].map(m => Number(m[1]));
  assert.deepEqual(indices, indices.map((_, i) => i), 'visible navigation stays contiguous');
  run(`toggleFolder(${JSON.stringify(key)})`);
  assert(!output().includes('class="folder-panel"'), 'second click closes the folder');
}
assert.equal(covered, run('contentEntries(services()).length'), 'every entry is reachable in exactly one folder');
run(`toggleFolder(${JSON.stringify(keys[0])})`);
for (const count of [6, 4]) {
  columns = count;
  run('render()');
  const beforePanel = output().split('class="folder-panel"')[0];
  assert.equal([...beforePanel.matchAll(/class="tile folder-tile/g)].length, count / 2, 'panel follows the complete folder row');
}
run(`toggleFolder(${JSON.stringify(keys[1])})`);
assert(!output().includes(`id="folder-${keys[0]}"`), 'opening another folder closes the previous one');
const appCategory = run('contentCategory(state.data.apps[0])');
run(`state.openFolder=${JSON.stringify(appCategory)}; render();`);
assert(output().includes(run('esc(state.data.apps[0].live[0])')), 'live app content remains available');
assert(/class="tile w[^"<>]*\blive\b/.test(output()), 'live app keeps its wide tile');
context.location = new URL('https://preview.example/?view=classic');
run('render()');
assert(!output().includes('folder-grid'), 'classic view remains available');
console.log(`Folders passed: ${covered} demo entries, open/close/switch, navigation, 4/6-column row placement, live app and classic view. DOM stubs; visual interaction still needs browser verification.`);

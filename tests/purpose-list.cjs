// Run with: node tests/purpose-list.cjs. Uses only Node's built-in modules.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'public/index.html'), 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
const elements = new Map(), handlers = {};
function el(id) {
  if (!elements.has(id)) elements.set(id, {
    innerHTML: '', options: [], dataset: {}, style: { setProperty() {} },
    classList: { toggle() {}, contains() { return false; } },
    addEventListener() {}, setAttribute() {}, removeAttribute() {},
    querySelector() { return null; }, querySelectorAll() { return []; },
  });
  return elements.get(id);
}
const ctx = vm.createContext({
  URL, URLSearchParams, console, location: new URL('https://preview.example/?lang=zh'),
  localStorage: { getItem() { return null; } },
  document: { getElementById: el, documentElement: { style: { setProperty() {} } }, body: el('body'),
    querySelector() { return null; }, addEventListener(type, fn) { handlers[type] = fn; } },
  matchMedia() { return { matches: false, addEventListener() {} }; },
  addEventListener() {}, setTimeout() {}, setInterval() {}, history: {},
});
vm.runInContext(source.replace('tick(); setInterval(tick, 15000);\nload();', ''), ctx);
ctx.inputData = JSON.parse(fs.readFileSync(path.join(root, 'demo/data.json'), 'utf8'));
ctx.pins = [...ctx.inputData.services.slice(0, 2).map(s => ({ name: s.name, size: 'm' })),
  { name: ctx.inputData.apps[0].id, size: 'w' }];
const run = code => vm.runInContext(code, ctx);
run('state.data={...inputData,start:pins,start_grouped:true};state.animate=false;render();');
const home = el('main').innerHTML;
assert.equal([...home.matchAll(/data-nav/g)].length, 3, 'home shows only selected app tiles');
assert(!/<h1>|folder-grid|library-categories/.test(home), 'no new home title or classification container');
assert(home.includes('class="capability-name"'), 'capability titles are visible on the home screen');
const nav = [...home.matchAll(/data-i="(\d+)"/g)].map(match => Number(match[1]));
assert.deepEqual(nav, nav.map((_, index) => index), 'grouped home navigation stays contiguous');
run('state.data.start_grouped=false;render();');
assert(!el('main').innerHTML.includes('capability-grid'), 'ungrouped view stays available');
run('state.data.start_grouped=true;render();');
const count = ctx.inputData.services.length + (ctx.inputData.bookmarks || []).length + ctx.inputData.apps.filter(a => a.url).length;
function assertAllEntries() {
  assert.equal([...el('apps-list').innerHTML.matchAll(/data-app=/g)].length, count, 'all apps remain reachable');
}
assertAllEntries();
assert(el('apps-list').innerHTML.includes('<h3>系统</h3>'));
assert.equal(run("purposeOf({name:'Anthropic Courses',group:'AI Tools'})"), 'learn', 'specific purpose beats broad group');
assert.equal(run("purposeOf({name:'Unknown'})"), 'other');
assert.equal(run("purposeOf({name:'Category example',category:'assets'})"), 'assets');
handlers.click({ target: { closest(selector) { return selector === '[data-app-order]' ? { dataset: { appOrder: 'name' } } : null; } } });
assert.equal(run('state.appsOrder'), 'name');
assertAllEntries();
assert(!el('apps-list').innerHTML.includes('<h3>系统</h3>'));
run('render()');
assert.equal(el('main').innerHTML, home, 'list ordering never changes the Start tiles');
handlers.click({ target: { closest(selector) { return selector === '[data-app-order]' ? { dataset: { appOrder: 'purpose' } } : null; } } });
assertAllEntries();
ctx.itemName = ctx.inputData.services[0].name;
run("state.data.navigation={ [itemName]: {category:'learn',primary:false} };renderApps();");
assertAllEntries();
assert(el('apps-list').innerHTML.includes('<details data-purpose="learn"'), 'supporting entry is folded under its capability');
assert.equal(run('purposeOf(state.data.services[0])'), 'learn', 'configured capability overrides a product name');
el('apps-list').querySelectorAll = () => [{dataset:{purpose:'learn'}}];
run('renderApps()');
assert(el('apps-list').innerHTML.includes('<details data-purpose="learn" open>'), 'expanded support list survives refresh');
el('apps-list').querySelectorAll = () => [];
const visible = el('apps-list').innerHTML.replace(/<details[\s\S]*?<\/details>/g, '');
assert.equal([...visible.matchAll(/data-app=/g)].length, count - 1, 'supporting entry leaves the default list');
run("state.appsOrder='name';renderApps();");
assertAllEntries();
assert(!el('apps-list').innerHTML.includes('<details'), 'name view shows every entry directly');
run("state.appsOrder='purpose';state.data.navigation={};renderApps();");
run("applyLang('en');renderApps()");
assert(el('apps-list').innerHTML.includes('<h3>System</h3>'));
assert(el('apps-order').innerHTML.includes('purpose'));
run('state.device=state.data.devices[0].name;render();');
assert(!el('main').innerHTML.includes('capability-grid'), 'device filtering retains its service view');
ctx.plan = {...ctx.inputData.bookmarks[0], lines:['Week 1','Next: explain a sample <account>'], badge:'Plan'};
run('state.device=null;state.data.bookmarks=[plan];state.data.start=[{name:plan.name,size:"m"}];render();');
assert(el('main').innerHTML.includes('Next: explain a sample &lt;account&gt;'), 'summary uses escaped private configuration text');
assert(el('main').innerHTML.includes('class="mark-summary"'), 'planning summary is visible on its tile');
run('state.data.start=[{name:plan.name,size:"s"}];render();');
assert(!el('main').innerHTML.includes('class="mark-summary"'), 'small tiles retain their compact icon');
console.log(`Passed: ${count} complete-list entries, purpose/name switching, fixed home, explicit category, fallback and English. DOM execution; visual verification is separate.`);

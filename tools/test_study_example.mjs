// Verify the study card shows the ALBANIAN sentence of an example, not just
// the English translation.
//
// Why this test is written the way it is: a previous version of this feature
// was merged broken and its test still passed. That test exercised a
// hand-copied viewStudy against a hand-built word object, so it never touched
// the shipped data or the shipped view. This one extracts the REAL
// viewStudy() source out of app/js/app.js and runs it against the REAL
// data/words.json, so a change to either side is caught.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
const APP = join(ROOT, 'app', 'js', 'app.js');

let pass = 0;
let fail = 0;
function ok(cond, name, extra = '') {
  if (cond) { pass += 1; console.log('  ok ' + name); }
  else { fail += 1; console.log('  x  ' + name + (extra ? '  [' + extra + ']' : '')); }
}
function eq(a, b, name) { ok(a === b, name, 'got ' + JSON.stringify(a) + ' want ' + JSON.stringify(b)); }

console.log('study card example tests');

/* ------------------------------------------------------------------ DOM stub */

function makeNode(tag) {
  return {
    tag,
    className: '',
    _text: '',
    children: [],
    listeners: {},
    set textContent(v) { this._text = v; this.children = []; },
    get textContent() {
      if (this.children.length) return this.children.map((c) => c.text).join('');
      return this._text;
    },
    append(...nodes) { for (const n of nodes) this.children.push(n); },
    addEventListener(evt, fn) { (this.listeners[evt] ||= []).push(fn); },
  };
}

const document = {
  createElement: (tag) => makeNode(tag),
  createTextNode: (t) => ({ text: String(t), children: [], textContent: String(t) }),
  querySelector: () => makeNode('div'),
};

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}

/* --------------------------------------------- extract the real viewStudy */

const appSrc = readFileSync(APP, 'utf8');
const lines = appSrc.split('\n');

const start = lines.findIndex((l) => l.startsWith('function viewStudy('));
if (start < 0) {
  console.log('  x  could not find viewStudy() in app/js/app.js');
  process.exit(1);
}
// The function ends at the next line that is exactly "}" at column 0.
let end = start;
while (end < lines.length && lines[end] !== '}') end += 1;
const viewStudySrc = lines.slice(start, end + 1).join('\n');

ok(viewStudySrc.length > 0, 'extracted real viewStudy() source',
   String(viewStudySrc.split('\n').length) + ' lines');

/* ---------------------------------- run that source against real course data */

const GRADES = { AGAIN: 1, HARD: 2, GOOD: 3, EASY: 4 };

/**
 * Build a runnable viewStudy from the extracted source, with the app's
 * surroundings stubbed out. `src` is the real source unless a test passes a
 * deliberately broken copy (negative control).
 */
function buildViewStudy(src) {
  const stubbed = [
    'function viewDone(root){ return null; }',
    'function componentsLine(w){ return null; }',
    'function preview(item, g){ return ""; }',
    'function itemFor(id){ return null; }',
    'function grade(){ }',
    'function render(){ }',
    'const GRADES = { AGAIN:1, HARD:2, GOOD:3, EASY:4 };',
    'const el = globalThis.__el;',
    'const document = globalThis.__document;',
    'var state = globalThis.__state;',
    src,
    'return viewStudy;',
  ].join('\n');

  const factory = new Function('globalThis', stubbed);
  return function call(src) { return factory(globalThis); };
}

// Real data.
const wordsDoc = JSON.parse(readFileSync(join(ROOT, 'data', 'words.json'), 'utf8'));
const allWords = wordsDoc.words;
ok(Array.isArray(allWords), 'words.json exposes an array of words');

// Every example in the shipped data must carry BOTH halves, so the card can
// show the Albanian sentence rather than silently skipping it.
const withEx = allWords.filter((w) => w.ex);
const bothHalves = withEx.filter((w) => w.ex && w.ex.sq && w.ex.en);
eq(bothHalves.length, withEx.length,
   'every example has both sq and en (' + withEx.length + ')');

function renderStudyCard(word, opts = {}) {
  globalThis.__el = el;
  globalThis.__document = document;
  globalThis.__state = {
    queue: [word.id],
    queuePos: 0,
    direction: opts.direction || 'sq2en',
    revealed: opts.revealed !== false,
    words: new Map([[word.id, word]]),
  };
  const viewStudy = buildViewStudy(viewStudySrc)();
  const root = makeNode('div');
  viewStudy(root);
  return root;
}

// Walk the rendered tree collecting text.
function nodeText(node) {
  // A node made by el(tag, cls, text) holds its string in _text. A node made
  // by document.createTextNode(s) holds it in .text. Either can have children.
  if (typeof node._text === 'string' && node._text !== '') return node._text;
  if (typeof node.text === 'string' && node.text !== '') return node.text;
  return '';
}

function allText(node, acc = []) {
  const t = nodeText(node);
  if (t) acc.push(t);
  for (const c of node.children || []) allText(c, acc);
  return acc;
}

// The headline case from the report: the card for "të" glossed
// "to, that (introduces a subjunctive clause...)" showed only the English
// half, "to love someone.", so there was no way to see how të is used.
const te = allWords.find((w) => w.id === 'të');
ok(!!te, 'the card "të" exists in the shipped data');

if (te) {
  ok(!!te.ex && !!te.ex.sq, 'të has an Albanian example sentence',
     te.ex ? JSON.stringify(te.ex.sq) : 'none');
  eq(te.ex.en, 'to love someone.', 'të example English is the translation');

  const root = renderStudyCard(te);
  const text = allText(root).join(' | ');

  ok(text.includes(te.ex.sq),
     'the study card shows the ALBANIAN example sentence',
     'sq=' + JSON.stringify(te.ex.sq));
  ok(text.includes(te.ex.en),
     'the study card still shows the English translation');
  ok(text.includes('to, that'),
     'the study card shows the gloss');
  ok(text.includes(te.sq),
     'the study card shows the Albanian prompt');
}

// The example must be marked up in two parts so the CSS can set the
// Albanian line apart from the italic English one.
{
  const root = renderStudyCard(te);
  let exBox = null;
  const walk = (n) => {
    if (n.className === 'example') exBox = n;
    for (const c of n.children || []) walk(c);
  };
  walk(root);
  ok(!!exBox, 'the example is wrapped in a .example box');
  if (exBox) {
    const classes = (exBox.children || []).map((c) => c.className);
    ok(classes.includes('ex-sq') && classes.includes('ex-en'),
       'the example box holds an .ex-sq and an .ex-en line',
       JSON.stringify(classes));
  }
}

// Cards with no example must not gain an empty box.
{
  const noEx = allWords.find((w) => !w.ex);
  ok(!!noEx, 'found a card with no example to test the empty case');
  if (noEx) {
    const root = renderStudyCard(noEx);
    let found = false;
    const walk = (n) => {
      if (n.className === 'example') found = true;
      for (const c of n.children || []) walk(c);
    };
    walk(root);
    ok(!found, 'a card with no example renders no empty example box',
       noEx.id);
  }
}

// Every card in the deck that has an example must render both halves.
// This is the sweep that would have caught the original bug at scale.
{
  let both = 0;
  let missingSq = 0;
  let missingEn = 0;
  for (const w of withEx) {
    const text = allText(renderStudyCard(w)).join(' | ');
    if (!text.includes(w.ex.sq)) { missingSq += 1; if (missingSq < 4) console.log('      missing sq: ' + w.id); }
    else if (!text.includes(w.ex.en)) { missingEn += 1; if (missingEn < 4) console.log('      missing en: ' + w.id); }
    else both += 1;
  }
  eq(missingSq, 0, 'no example loses its Albanian sentence across all ' + withEx.length + ' cards');
  eq(missingEn, 0, 'no example loses its English translation across all ' + withEx.length + ' cards');
  eq(both, withEx.length, 'every example renders fully');
}

/* ------------------------------------------------------------ negative control */

// A test that cannot fail is worthless. Put the old bug back in a copy of the
// real source and confirm this test's assertion would catch it.
{
  const brokenSrc = viewStudySrc.replace(
    /if \(w\.ex && w\.ex\.sq && w\.ex\.en\) \{[\s\S]*?\n    \}/,
    "if (w.ex) card.append(el('div', 'example', w.ex.en));"
  );
  ok(brokenSrc !== viewStudySrc, 'negative control: the old buggy line can be reintroduced');

  globalThis.__el = el;
  globalThis.__document = document;
  globalThis.__state = {
    queue: [te.id], queuePos: 0, direction: 'sq2en', revealed: true,
    words: new Map([[te.id, te]]),
  };
  const brokenView = buildViewStudy(brokenSrc)();
  const root = makeNode('div');
  brokenView(root);
  const text = allText(root).join(' | ');

  ok(!text.includes(te.ex.sq),
     'negative control: the old code drops the Albanian sentence');
  ok(text.includes(te.ex.en),
     'negative control: the old code still shows the English half');
}

console.log();
if (fail) { console.log('FAILURES (' + fail + ') of ' + (pass + fail)); process.exit(1); }
console.log('ALL ' + pass + ' TESTS PASSED');

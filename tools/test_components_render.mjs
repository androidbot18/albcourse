// Verify the breakdown line renders from real course data.
//
// The build stores components as [{word, role, en?, affix?, meaning?}] plus a
// card-level `breakdown` of "transparent" or "historical". app.js must turn
// that into "built from pa- + fund" (with glosses) or "historically from
// për- + dorë" (without). This runs the REAL componentsLine() extracted from
// app/js/app.js against the shipped level files, because a hand-copied mirror
// of the function is what this test used to check, and a mirror can pass
// while the app is wrong.

import { readFileSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const LEVELS = join(ROOT, 'data', 'levels');

let fail = 0;
let n = 0;
function ok(name, cond, extra) {
  n += 1;
  if (cond) console.log('  ok   ' + name + (extra ? '  ' + extra : ''));
  else { console.log('  FAIL ' + name + (extra ? '  ' + extra : '')); fail += 1; }
}

console.log('components render tests');

// Minimal DOM stand-ins, enough for el() and createTextNode().
function makeNode(tag) {
  return {
    tag, className: '', children: [], textContent: '', title: '',
    append(...xs) { this.children.push(...xs); },
  };
}
const document = {
  createElement: makeNode,
  createTextNode: (s) => ({ text: s }),
};
const el = (tag, cls, text) => {
  const node = makeNode(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
};
function text(node) {
  if (node.text !== undefined) return node.text;
  return (node.textContent || '') + node.children.map(text).join('');
}
function find(node, cls, out = []) {
  if ((node.className || '').split(' ').includes(cls)) out.push(node);
  for (const c of node.children || []) find(c, cls, out);
  return out;
}

// Extract the real functions from app.js.
const appSrc = readFileSync(join(ROOT, 'app', 'js', 'app.js'), 'utf8');
function extract(src, name) {
  const lines = src.split('\n');
  const start = lines.findIndex((l) => l.startsWith('function ' + name + '('));
  if (start < 0) return '';
  const end = lines.findIndex((l, i) => i > start && l === '}');
  return lines.slice(start, end + 1).join('\n');
}
const lexical = appSrc.split('\n').find((l) => l.startsWith('const LEXICAL ='));
const partSrc = extract(appSrc, 'partText');
const lineSrc = extract(appSrc, 'componentsLine');
ok('app.js defines LEXICAL, partText and componentsLine', !!lexical && !!partSrc && !!lineSrc);

function build(src) {
  return new Function('el', 'document',
    [lexical, partSrc, src, 'return componentsLine;'].join('\n'))(el, document);
}
const componentsLine = build(lineSrc);

ok('app.js wires the line into wordRow (level view) with glosses',
   /componentsLine\(w, \{ glosses: true \}\)/.test(appSrc) && /row\.append\(comps\)/.test(appSrc));
ok('app.js wires the line into the study card', /card\.append\(sc\)/.test(appSrc));

const css = readFileSync(join(ROOT, 'app', 'css', 'style.css'), 'utf8');
ok('style.css colour-codes stem and affix',
   css.includes('.components .stem') && css.includes('.components .affix'));
ok('style.css mutes historical breakdowns', css.includes('.components.historical'));

// Real data.
const files = readdirSync(LEVELS).filter((f) => /^level_\d+\.json$/.test(f)).sort();
const byWord = new Map();
let cards = 0;
let empty = 0;
let suffixes = 0;
let stemAsPrefix = 0;
for (const f of files) {
  const lvl = JSON.parse(readFileSync(join(LEVELS, f), 'utf8'));
  for (const w of lvl.words) {
    cards += 1;
    byWord.set(w.sq, w);
    const comps = w.components || [];
    if (!comps.length) continue;
    const line = componentsLine(w, { glosses: true });
    if (!line || !text(line).trim()) empty += 1;
    if (comps.some((c) => c.role === 'suffix')) suffixes += 1;
    // The 514-card bug: a suffix derivation ("mund + -ësi") whose base was
    // filed as a prefix with nothing after it ("from mund-"). A lone prefix
    // on a compound (doemos = do + e + mos) is a different, older case.
    if (comps.length === 1 && comps[0].role === 'prefix'
        && new RegExp(comps[0].word + '\\s*(\\([^)]*\\)\\s*)?\\+\\s*-').test(w.etymology || '')) {
      stemAsPrefix += 1;
    }
  }
}
ok('every card with components renders a non-empty line', empty === 0, '(' + empty + ' empty)');
ok('suffixes are extracted', suffixes > 400, '(' + suffixes + ' cards show a suffix)');
ok('no lone-prefix breakdowns ("from mund-")', stemAsPrefix === 0, '(' + stemAsPrefix + ')');

const idxWords = JSON.parse(readFileSync(join(ROOT, 'data', 'index.json'), 'utf8'))
  .reduce((acc, lv) => acc + (lv.word_count || 0), 0);
ok('sanity: cards counted', cards === idxWords, '(got ' + cards + ', expected ' + idxWords + ')');

function rendered(sq, opts) {
  const w = byWord.get(sq);
  return w ? text(componentsLine(w, opts)).replace(/\s+/g, ' ').trim() : '(missing ' + sq + ')';
}

// Headline cases, read from the shipped data.
let got = rendered('mundësi', { glosses: false });
ok('mundësi renders as mund + -ësi', got === 'built from mund + -ësi', '(got "' + got + '")');
got = rendered('pafund', { glosses: true });
ok('pafund shows each part with its meaning',
   got.includes('pa-') && got.includes('un-, without') && got.includes('fund') && got.includes('end'),
   '(got "' + got + '")');
got = rendered('përdor', { glosses: true });
ok('përdor is historical and unglossed',
   got.startsWith('historically from') && !got.includes('hand'), '(got "' + got + '")');
got = rendered('esëll', { glosses: false });
ok('esëll still renders e- + sillë', got.endsWith('e- + sillë'), '(got "' + got + '")');
// A wrong-homograph stem gloss must never reach the learner: pije is pi
// ("to drink"), but the deck glosses the card pi as "from".
got = rendered('pije', { glosses: true });
ok('pije does not show the wrong-homograph gloss "from"', !/\bfrom\b.*\bfrom\b/.test(got) && !got.includes('(from'),
   '(got "' + got + '")');

// Negative control: a componentsLine that ignores `breakdown` glosses
// historical cards too. The përdor check above must catch it.
const broken = build(lineSrc.replace("w.breakdown === 'transparent'", 'true'));
const w = byWord.get('përdor');
if (w) {
  const bad = text(broken(w, { glosses: true }));
  ok('negative control: an always-transparent renderer is caught',
     !bad.startsWith('historically from'), '(got "' + bad + '")');
}

// Guess from the parts: offered only on a NEW transparent card whose base
// the learner has already started. Runs the real isGuessCard().
const guessSrc = extract(appSrc, 'isGuessCard');
ok('app.js defines isGuessCard', !!guessSrc);
const isNewStub = (it) => !it || it.due === null;
function guessWith(items) {
  const state = { progress: { items } };
  return new Function('state', 'isNew', [lexical, guessSrc, 'return isGuessCard;'].join('\n'))(state, isNewStub);
}
const learned = { id: 'mund', due: 1 };
const ms = byWord.get('mundësi');
ok('guess: mundësi is a guess card once mund is known', guessWith({ mund: learned })(ms, 'mundësi'));
ok('guess: not before mund is known', !guessWith({})(ms, 'mundësi'));
ok('guess: not once mundësi itself has been seen',
   !guessWith({ mund: learned, 'mundësi': { id: 'mundësi', due: 1 } })(ms, 'mundësi'));
ok('guess: not on the reverse card', !guessWith({ mund: learned })(ms, 'mundësi~r'));
const pd = byWord.get('përdor');
ok('guess: never on a historical breakdown', !guessWith({ 'dorë': learned })(pd, 'përdor'));

console.log();
if (fail) { console.log('FAILURES (' + fail + ')'); process.exit(1); }
console.log('ALL ' + n + ' TESTS PASSED');

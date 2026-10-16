/* Pin the flat index's example choice to the lesson view's.
 *
 * These two implementations had already drifted once, and the drift shipped:
 * course.js applied the "same POS or nothing" rule while build_words_index.py
 * kept scanning every sense, so the review card kept showing the bug the
 * lesson view had already fixed. This file exists to stop that recurring.
 *
 * It reads the REAL data/words.json, the REAL level files, and the REAL
 * exampleForSense(), so a change to any of the three is caught here.
 */

import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { exampleForSense } from '../app/js/course.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');

let pass = 0;
let fail = 0;
function ok(cond, name, extra = '') {
  if (cond) { pass += 1; console.log('  ok ' + name); }
  else { fail += 1; console.log('  x  ' + name + (extra ? '  [' + extra + ']' : '')); }
}

console.log('flat index example parity tests');

const words = JSON.parse(readFileSync(join(ROOT, 'data', 'words.json'), 'utf8')).words;
const levelDir = join(ROOT, 'data', 'levels');
const levels = {};
for (const f of readdirSync(levelDir)) {
  if (!f.endsWith('.json')) continue;
  const lvl = JSON.parse(readFileSync(join(levelDir, f), 'utf8'));
  for (const w of lvl.words) levels[w.id] = w;
}
ok(Object.keys(levels).length > 0, 'level files loaded', String(Object.keys(levels).length));

const byId = {};
for (const w of words) byId[w.id] = w;

// "e" is back (RECOMMENDATIONS.md section 3.2). It was removed because its
// card could not say which sense it taught, and its corpus example showed
// the ARTICLE ("jetën e gëzuar") under the gloss "and", whose English "and"
// came from "dhe". It now headlines "and" with a reviewed example in which
// e joins two nouns (tools/gloss_overrides.EXAMPLES), and the corpus
// sentence is dropped. Pin both, in both the lesson view and the index.
const E_DEFECT = 'Për të rikthyer jetën e gëzuar dhe të hareshme.';
const E_REVIEWED = 'Punoj ditë e natë.';
ok(!!levels['e'] && levels['e'].en === 'and', '"e" is a card headlining "and"',
   levels['e'] ? levels['e'].en : 'missing');
{
  const shown = levels['e'] ? exampleForSense(levels['e']) : null;
  ok(shown && shown.sq === E_REVIEWED, 'lesson view: "e" shows the reviewed example',
     shown ? shown.sq : 'none');
  const idx = byId['e'];
  ok(idx && idx.ex && idx.ex.sq === E_REVIEWED, 'flat index: "e" shows the reviewed example',
     idx && idx.ex ? idx.ex.sq : 'none');
  ok(!levels['e'] || !levels['e'].corpus_example
     || levels['e'].corpus_example.sq !== E_DEFECT,
     'the article-sense corpus sentence is gone');
}

// The same defect, on a word that still ships. "lis" headlines the adjective
// "strong and tall", which has no example, while its noun sense "lineage"
// carries one. A same-POS borrow would be defensible -- the sentence would
// still show the glossed meaning -- so this fixture is deliberately the harder
// case: the only example available belongs to a DIFFERENT part of speech.
// Both implementations must return nothing rather than borrow it.
const lis = levels['lis'];
ok(!!lis, 'the card "lis" is in the level data');
if (lis) {
  const home = lis.sense_detail[0];
  const hasExample = (s) => (s.examples || []).some(
    (x) => x && typeof x.en === 'string' && x.en.trim());
  ok(!hasExample(home), '"lis" headline sense ("strong and tall") has no example');
  ok(!(lis.sense_detail || []).some(
 (s) => s.pos === home.pos && hasExample(s)),
     '"lis" has no same-POS example to fall back on');
  const other = (lis.sense_detail || []).find((s) => hasExample(s));
  ok(!!other && other.pos !== home.pos,
     'a later "lis" sense of another POS has an example to leak');
  const shownL = exampleForSense(lis);
  ok(!shownL, 'lesson view: "lis" shows no other-POS example',
     shownL ? JSON.stringify(shownL) : 'none');
  const idx = byId['lis'];
  ok(idx && !idx.ex, 'flat index: "lis" carries no other-POS example',
     idx ? JSON.stringify(idx.ex) : 'missing');
}

// Parity across the whole deck: for every card, the flat index must hold the
// same example the lesson view would pick.
let agree = 0;
const disagree = [];
for (const w of Object.values(levels)) {
  const idx = byId[w.id];
  if (!idx) continue;
  const fromView = exampleForSense(w);
  const norm = (x) => (x && x.en ? { sq: x.sq, en: x.en } : null);
  if (JSON.stringify(norm(fromView)) === JSON.stringify(norm(idx.ex || null))) agree += 1;
  else disagree.push(w.id);
}
ok(disagree.length === 0,
   'flat index agrees with the lesson view for every card',
   disagree.length + ' disagree: ' + disagree.slice(0, 6).join(', '));

// No surviving example may come from a different part of speech than the
// gloss the card headlines. This is the rule itself, asserted on real data.
const leaks = [];
for (const w of Object.values(levels)) {
  const idx = byId[w.id];
  if (!idx || !idx.ex) continue;
  const senses = w.sense_detail || [];
  if (!senses.length) continue;
  const home = senses[0];
  const own = (home.examples || []).some(
    (x) => x && typeof x.en === 'string' && x.en.trim());
  if (own) continue; // from its own sense: correct by construction
  const src = senses.find((s) => (s.examples || []).some(
    (x) => x && x.en === idx.ex.en));
  if (src && src.pos !== home.pos) {
    leaks.push(w.id + ' (' + home.pos + ' <- ' + src.pos + ')');
  }
}
ok(leaks.length === 0,
   'no card pairs a gloss with an example from another part of speech',
   leaks.length + ' leaks: ' + leaks.slice(0, 6).join(', '));
ok(agree > 300, 'a substantial number of cards were compared', String(agree));

// Negative control: the OLD build_words_index rule DOES leak on "lis" --
// it walks every sense and returns the first example it finds, ignoring which
// sense the card actually headlines. If it ever stopped leaking, the control
// above would be meaningless.
{
  const oldRule = (word) => {
    for (const s of word.sense_detail || []) {
      for (const ex of s.examples || []) {
        if (ex && typeof ex.en === 'string' && ex.en.trim()) {
          return { sq: ex.sq, en: ex.en };
        }
      }
    }
    return null;
  };
  const leaked = oldRule(lis);
  ok(!!leaked, 'negative control: the old rule does return an example');
  ok(JSON.stringify(oldRule(lis)) !== JSON.stringify(exampleForSense(lis)),
     'negative control: the old rule differs from the current one');
}

console.log();
if (fail) { console.log('FAILURES (' + fail + ')'); process.exit(1); }
console.log('ALL ' + pass + ' TESTS PASSED');

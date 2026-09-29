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

// The reported case: "e" headlines the conjunction "and", whose senses carry
// no examples. The only example belongs to the preposition sense "of, +
// dative", so both implementations must return nothing.
const e = levels['e'];
ok(!!e, 'the card "e" is in the level data');
if (e) {
  const home = e.sense_detail[0];
  const homeHasExample = (home.examples || []).some(
    (x) => x && typeof x.en === 'string' && x.en.trim());
  ok(!homeHasExample, '"e" headline sense ("and") really has no example');
  // The card may now show a corpus sentence where "e" really is the
  // conjunction ("Dhe e bera." / "And it did."). What must never happen is the
  // preposition example, so the rule under test is "no wrong-POS example",
  // not "no example at all".
  const shownE = exampleForSense(e);
  ok(!shownE || String(shownE.sq).indexOf('Besa') < 0,
     'lesson view: "e" shows no preposition example');
  const idx = byId['e'];
  ok(idx && (!idx.ex || String(idx.ex.sq).indexOf('Besa') < 0),
     'flat index: "e" carries no preposition example',
     idx ? JSON.stringify(idx.ex) : 'missing');
  ok(!idx || !idx.ex || String(idx.ex.sq).indexOf('Besa') < 0,
     'the preposition sentence is gone from "e"');
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

// Negative control: the OLD build_words_index rule does leak on "e". If it
// ever stopped leaking, this control would be meaningless.
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
  const leaked = oldRule(e);
  ok(!!leaked && String(leaked.sq).indexOf('Besa') >= 0,
     'negative control: the old rule does return the preposition sentence');
  ok(JSON.stringify(oldRule(e)) !== JSON.stringify(exampleForSense(e)),
     'negative control: the old rule differs from the current one');
}

console.log();
if (fail) { console.log('FAILURES (' + fail + ')'); process.exit(1); }
console.log('ALL ' + pass + ' TESTS PASSED');

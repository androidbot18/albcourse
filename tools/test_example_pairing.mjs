/* Audit example/gloss pairing across the whole deck.
 *
 * The bug: firstExample() returned the first example across ALL senses, so a
 * card could show its headline gloss next to an example belonging to a
 * different sense -- and often a different part of speech entirely. 'e' showed
 * the conjunction "and" illustrated by a preposition sentence with no "and" in
 * it.
 *
 * This reports how many cards are affected and confirms every example now
 * shown shares the headline sense's part of speech.
 */
import { readdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { firstExample, exampleForSense } from '../app/js/course.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const LEVELS = join(dirname(HERE), 'data', 'levels');

let pass = 0, fail = 0;
function ok(cond, name, extra) {
  if (cond) { console.log('  ok   ' + name); pass += 1; }
  else { console.log('  FAIL ' + name + (extra ? '  ' + extra : '')); fail += 1; }
}

console.log('example pairing tests');

// The reported case, exactly.
const lvl1 = JSON.parse(readFileSync(join(LEVELS, 'level_0001.json'), 'utf8'));
const e = lvl1.words.find((w) => w.id === 'e');
ok(!!e, 'the card e exists');
if (e) {
  ok(e.en === 'and', "e's headline is the conjunction 'and'", 'got ' + e.en);
  const homePos = e.sense_detail[0].pos;
  ok(homePos === 'conj', 'headline sense is a conjunction', 'got ' + homePos);
  ok((e.sense_detail[0].examples || []).length === 0,
     'that sense genuinely has no example, so showing none is correct');
  const ex = firstExample(e);
  ok(ex === null, "'e' shows no example rather than a preposition one",
     'got ' + (ex ? ex.sq : 'null'));
}

// Across the whole deck: no shown example may come from a different POS.
let total = 0, withEx = 0, crossPos = 0;
const samples = [];
for (const f of readdirSync(LEVELS)) {
  const words = JSON.parse(readFileSync(join(LEVELS, f), 'utf8')).words;
  for (const w of words) {
    total += 1;
    const ex = firstExample(w);
    if (!ex) continue;
    withEx += 1;
    const home = (w.sense_detail || [])[0];
    if (!home) continue;
    const src = (w.sense_detail || []).find(
      (s) => (s.examples || []).some((q) => q && q.sq === ex.sq));
    if (src && src.pos !== home.pos) {
      crossPos += 1;
      if (samples.length < 5) samples.push(w.id + ' (' + home.pos + ' gloss, ' + src.pos + ' example)');
    }
  }
}
console.log('  cards: ' + total + ', showing an example: ' + withEx);
ok(crossPos === 0, 'no card shows an example from a different part of speech',
   'bad: ' + crossPos + ' ' + samples.join('; '));

// The same-POS fallback must still work where it legitimately applies.
let found = null;
for (const f of readdirSync(LEVELS)) {
  const words = JSON.parse(readFileSync(join(LEVELS, f), 'utf8')).words;
  for (const w of words) {
    const sd = w.sense_detail || [];
    if (sd.length < 2) continue;
    if ((sd[0].examples || []).length) continue;
    const same = sd.find((s, i) => i > 0 && s.pos === sd[0].pos && (s.examples || []).length);
    if (same) { found = w.id; break; }
  }
  if (found) break;
}
ok(found !== null, 'at least one card falls back within its own POS',
   'no such card found');
if (found) {
  console.log('       e.g. ' + found + ' (headline sense has no example)');
}

// Negative control: the old behaviour really did mispair.
if (e) {
  const old = (() => {
    for (const s of e.sense_detail) {
      for (const ex of (s.examples || [])) {
        if (ex && ex.en && ex.en.trim()) return ex;
      }
    }
    return null;
  })();
  ok(old !== null && old.sq.includes('Besa'),
     'negative control: the old scan returned the preposition example');
  ok(old !== firstExample(e), 'negative control: the old behaviour differs from the fix');
}

console.log('');
if (fail) {
  console.log('FAILURES (' + fail + '): ' + pass + ' passed, ' + fail + ' failed');
  process.exit(1);
}
console.log('ALL ' + pass + ' TESTS PASSED');

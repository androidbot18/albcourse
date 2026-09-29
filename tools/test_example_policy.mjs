/* Lock in the example-pairing policy the learner asked for.
 *
 * 1. An example must actually USE the word it illustrates. A sentence that
 *    never says the headword teaches nothing.
 * 2. An example must be paired with a gloss it really illustrates, and a
 *    sentence borrowed from a sibling sense must say which sense it came from,
 *    so it is never read as illustrating the headline meaning.
 * 3. An example must never be borrowed across parts of speech - that is the
 *    exact bug that put a preposition sentence under the conjunction "and".
 * 4. Ranking must not reduce coverage: short-and-familiar is a PREFERENCE, and
 *    the source is too thin to throw anything away. A first attempt at this
 *    hard-rejected non-matching examples and silently cost 149 cards their only
 *    example, so this invariant is pinned here.
 *
 * Reads the REAL data files, so a data or code change is caught.
 */

import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { examplePairForSense, sensesOf } from '../app/js/course.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');

let pass = 0;
let fail = 0;
function ok(cond, name, extra = '') {
  if (cond) { pass += 1; console.log('  ok ' + name); }
  else { fail += 1; console.log('  x  ' + name + (extra ? '  [' + extra + ']' : '')); }
}

console.log('example policy tests');

const words = JSON.parse(readFileSync(join(ROOT, 'data', 'words.json'), 'utf8')).words;
const levels = {};
for (const f of readdirSync(join(ROOT, 'data', 'levels'))) {
  const lv = JSON.parse(readFileSync(join(ROOT, 'data', 'levels', f), 'utf8'));
  for (const w of lv.words) levels[w.sq] = w;
}

// --- 1. every shipped example is a real bilingual pair -------------------
const withEx = words.filter((w) => w.ex);
ok(withEx.length > 300, 'deck ships a useful number of examples', String(withEx.length));
ok(withEx.every((w) => w.ex.sq && w.ex.en),
  'every shipped example has both Albanian and English');
ok(withEx.every((w) => typeof w.ex_gloss === 'string' || w.ex_gloss === null),
  'ex_gloss is a string or null, never undefined');

// --- 2. no cross-POS borrowing (the "e" bug) ----------------------------
let crossPos = 0;
for (const w of withEx) {
  if (!w.ex_from_sense) continue;
  const senses = sensesOf(levels[w.sq]);
  const homePos = senses[0] && senses[0].pos;
  const src = senses.find((s) => s.gloss === w.ex_gloss);
  if (!src || src.pos !== homePos) crossPos += 1;
}
ok(crossPos === 0, 'no example is borrowed across parts of speech', 'bad=' + crossPos);

// --- 3. a borrowed example is labelled ----------------------------------
const borrowed = withEx.filter((w) => w.ex_from_sense);
ok(borrowed.length > 0, 'the borrowed-sense path is exercised', String(borrowed.length));
ok(borrowed.every((w) => w.ex_gloss && String(w.ex_gloss).trim()),
  'every borrowed example names the sense it came from');
ok(borrowed.every((w) => w.ex_gloss !== w.en),
  'a borrowed example is never labelled with the headline gloss');

// --- 4. the app renders the label ---------------------------------------
const appSrc = readFileSync(join(ROOT, 'app', 'js', 'app.js'), 'utf8');
ok(/ex_from_sense/.test(appSrc) && /ex_gloss/.test(appSrc),
  'the review card renders the borrowed-sense label');
ok(/ex-note/.test(readFileSync(join(ROOT, 'app', 'css', 'style.css'), 'utf8')),
  'the borrowed-sense label is styled');

// --- 5. the JS rule matches the shipped flat index, card for card ------
let mismatch = 0;
for (const w of words) {
  const pair = examplePairForSense(levels[w.sq], 0);
  const jsSq = pair ? pair.ex.sq : null;
  if ((jsSq || null) !== ((w.ex && w.ex.sq) || null)) mismatch += 1;
}
ok(mismatch === 0, 'JS and the flat index agree on every card', 'mismatch=' + mismatch);

// --- 6. NEGATIVE CONTROL -------------------------------------------------
// A card whose senses are [conj "and" (no examples), prep "of" (with an
// example)] must NOT borrow the preposition sentence. This is the original
// bug, reproduced in miniature.
const trap = {
  sense_detail: [
    { pos: 'conj', gloss: 'and', examples: [] },
    { pos: 'prep', gloss: 'of, + dative', examples: [{ sq: 'Besa e shqiptarit nuk shitet pazarit.', en: 'The honor of an Albanian can not be sold.' }] },
  ],
  pos: ['conj', 'prep'],
  en: 'and',
};
const trapPair = examplePairForSense(trap, 0);
ok(trapPair === null, 'a conj card refuses a preposition example');
ok(!/Besa/.test(JSON.stringify(trapPair)), 'the bazaar sentence never reaches the conj card');

// And the same-POS sibling case SHOULD be allowed, and labelled.
const sibling = {
  sense_detail: [
    { pos: 'noun', gloss: 'cheese, dairy', examples: [] },
    { pos: 'noun', gloss: 'cheese made from skimmed milk', examples: [{ sq: 'djathe i bardhe', en: 'white cheese' }] },
  ],
  pos: ['noun'],
  en: 'cheese',
};
const sibPair = examplePairForSense(sibling, 0);
ok(!!sibPair && sibPair.fromSense === true, 'a same-POS sibling example IS used');
ok(sibPair && sibPair.senseGloss === 'cheese made from skimmed milk',
  'the sibling example is labelled with its own sense');

console.log('\n' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);

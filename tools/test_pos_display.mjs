/* test_pos_display.mjs - regression test for the duplicated POS label.
 *
 * The bug: the level files keep pos/pos_labels index-aligned with glosses, so
 * a word like "e" really does have two conjunctive senses. The word row used to
 * render the first two ENTRIES of that array, printing
 * "conjunction, conjunction". The fix shows the first two DISTINCT labels.
 *
 * This test was added after the live E2E caught the defect, so it asserts the
 * exact rendered text for the words that triggered it.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { displayPosLabels } from '../app/js/course.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = dirname(HERE);

let pass = 0;
let fail = 0;
function ok(cond, name, extra) {
  if (cond) { console.log('  ok   ' + name); pass += 1; }
  else { console.log('  FAIL ' + name + (extra ? '  ' + extra : '')); fail += 1; }
}
function eq(a, b, name) {
  ok(a === b, name, 'got ' + JSON.stringify(a) + ' want ' + JSON.stringify(b));
}

console.log('pos display tests');

// ------------------------------------------------------------- unit behaviour
{
  const e = { pos_labels: ['conjunction', 'conjunction', 'preposition', 'preposition', 'pronoun'] };
  eq(displayPosLabels(e, 2).join(', '), 'conjunction, preposition',
     "'e' shows two distinct labels, not conjunction, conjunction");
  eq(displayPosLabels(e).join(', '), 'conjunction, preposition',
     'default n is 2');

  const n = { pos_labels: ['conjunction', 'preposition', 'preposition', 'preposition', 'preposition', 'pronoun', 'pronoun'] };
  eq(displayPosLabels(n, 2).join(', '), 'conjunction, preposition',
     "'ne' shows two distinct labels");

  const t = { pos_labels: ['conjunction', 'pronoun'] };
  eq(displayPosLabels(t, 2).join(', '), 'conjunction, pronoun',
     'a word with no repeats is unchanged');

  const one = { pos_labels: ['noun', 'noun', 'noun'] };
  eq(displayPosLabels(one, 2).join(', '), 'noun',
     'an all-same word collapses to a single label');

  eq(displayPosLabels({}, 2).join(', '), '', 'a word with no POS renders empty, not "undefined"');
  eq(displayPosLabels(null, 2).join(', '), '', 'null word is handled');
  eq(displayPosLabels({ pos: ['verb', 'verb'] }, 2).join(', '), 'verb', 'falls back to raw pos codes');
  eq(displayPosLabels({ pos_labels: ['a', 'b', 'c'] }, 5).join(', '), 'a, b, c', 'n larger than the list is fine');
  eq(displayPosLabels({ pos_labels: ['', 'noun', '', 'verb'] }, 2).join(', '), 'noun, verb',
     'empty labels are skipped, not rendered as blank entries');
}

// ------------------------------------------- against the real shipped data
{
  const idx = JSON.parse(readFileSync(join(ROOT, 'data', 'index.json'), 'utf8'));
  const width = String(idx.reduce((m, l) => Math.max(m, l.level), 0)).length;

  let checked = 0;
  let dupes = 0;
  const worst = [];
  // Sample levels across the whole course, not just the first: the defect was
  // common enough that only a wide sample proves it is gone.
  const step = Math.max(1, Math.floor(idx.length / 120));
  for (let i = 0; i < idx.length; i += step) {
    const n = idx[i].level;
    const lvl = JSON.parse(readFileSync(
      join(ROOT, 'data', 'levels', 'level_' + String(n).padStart(width, '0') + '.json'), 'utf8'));
    for (const w of lvl.words) {
      const shown = displayPosLabels(w, 2);
      checked += 1;
      if (shown.length !== new Set(shown).size) { dupes += 1; if (worst.length < 3) worst.push(w.id); }
    }
  }
  ok(checked > 100, 'sampled a meaningful number of real cards (got ' + checked + ')');
  eq(dupes, 0, 'no real card renders a repeated POS label (dupes: ' + dupes + ' ' + worst.join(', ') + ')');
}

// ----------------------------------------------------- negative control
// If dedup is removed the test MUST fail, otherwise it proves nothing.
{
  const e = { pos_labels: ['conjunction', 'conjunction', 'preposition'] };
  const broken = e.pos_labels.slice(0, 2).join(', '); // the old, buggy behaviour
  ok(broken === 'conjunction, conjunction',
     'negative control: the old slice behaviour really does produce the duplicate');
  ok(broken !== displayPosLabels(e, 2).join(', '),
     'negative control: the old behaviour differs from the fix');
}

console.log('');
if (fail) {
  console.log('FAILURES (' + fail + '): ' + pass + ' passed, ' + fail + ' failed');
  process.exit(1);
}
console.log('ALL ' + pass + ' TESTS PASSED');

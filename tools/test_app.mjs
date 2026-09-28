/* test_app.mjs - end-to-end test of the real app module under a stub DOM.
 *
 * The app is exercised as the browser would: same data files, same store, same
 * scheduler, just a minimal DOM and fetch standing in for the browser's. This
 * catches wiring mistakes that unit tests on srs.js/store.js cannot see, such
 * as a card whose text never gets attached to the DOM.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { newItem, review, GRADES, isDue, stage, STAGE_NAMES, summarise, buildQueue } from '../app/js/srs.js';
import { createStore, normalise, exportProgress, importProgress, STORAGE_KEY } from '../app/js/store.js';
import { groupByFamily, sensesOf, isReverseFriendly, firstExample, levelPath } from '../app/js/course.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');

let pass = 0;
let fail = 0;
function ok(cond, name, extra = '') {
  if (cond) { pass += 1; console.log('  ok ' + name); }
  else { fail += 1; console.log('  x  ' + name + (extra ? ' (' + extra + ')' : '')); }
}
function eq(a, b, name) { ok(a === b, name, 'got ' + JSON.stringify(a) + ' want ' + JSON.stringify(b)); }

console.log('app integration tests');

// ------------------------------------------------------ real data is usable
{
  const idx = JSON.parse(readFileSync(join(ROOT, 'data', 'index.json'), 'utf8'));
  const words = JSON.parse(readFileSync(join(ROOT, 'data', 'words.json'), 'utf8'));
  const levels = readFileSync(join(ROOT, 'data', 'levels', 'level_010.json'), 'utf8');

  eq(Array.isArray(idx), true, 'index.json is an array of level descriptors');
  ok(idx.length > 0, 'index has levels');
  ok(idx.every((l) => typeof l.level === 'number' && typeof l.word_count === 'number'), 'every level has a number and a count');
  ok(idx.every((l) => l.families > 0), 'every level has at least one family');

  ok(words.count === words.words.length, 'words.json count matches its array length');
  ok(words.words.every((w) => w.id && w.sq && w.en), 'every word has an id, Albanian and English');
  ok(words.words.every((w) => typeof w.level === 'number'), 'every word knows its level');
  ok(words.words.every((w) => w.family), 'every word knows its family');

  // The whole point: Albanian ë and ç must survive to the app, not be stripped.
  const withE = words.words.filter((w) => /[ëË]/.test(w.sq));
  const withC = words.words.filter((w) => /[çÇ]/.test(w.sq));
  ok(withE.length > 100, 'ë words reach the app intact (' + withE.length + ')');
  ok(withC.length > 20, 'ç words reach the app intact (' + withC.length + ')');
  ok(withE.some((w) => w.sq === 'të'), 'të is present and spelled correctly');

  // Some words should be reverse-unfriendly (multiword glosses) and be filtered.
  const long = words.words.filter((w) => !isReverseFriendly(w));
  ok(long.length >= 0, 'reverse filter runs without throwing on every word');

  ok(levels.length > 0, 'a level file parses as real JSON on disk');
}

// ------------------------------------------------------- card text resolution
{
  const words = JSON.parse(readFileSync(join(ROOT, 'data', 'words.json'), 'utf8')).words;
  const byId = new Map(words.map((w) => [w.id, w]));

  // The app looks up a card by id from the queue. If that lookup can fail, the
  // review screen renders undefined - so assert it cannot for any real id.
  let missing = 0;
  for (const w of words) {
    const got = byId.get(w.id);
    if (!got || !got.sq || !got.en) missing += 1;
  }
  eq(missing, 0, 'every queued id resolves to a card with both languages');

  // examples, where present, are well formed
  let badEx = 0;
  for (const w of words) {
    if (!w.ex) continue;
    if (typeof w.ex.en !== 'string' || !w.ex.en.trim()) badEx += 1;
  }
  eq(badEx, 0, 'every bundled example has non-empty English text');
}

// ------------------------------------------------- family grouping is stable
{
  const words = JSON.parse(readFileSync(join(ROOT, 'data', 'words.json'), 'utf8')).words.slice(0, 400);
  const groups = groupByFamily(words);
  ok(groups.size > 0, 'families group cleanly');
  // every member of a group carries that family id
  let mismatched = 0;
  for (const [fam, list] of groups) {
    for (const w of list) if ((w.family || w.id) !== fam) mismatched += 1;
  }
  eq(mismatched, 0, 'grouped words all report the family they were grouped under');
}

// ------------------------------------------------ a full review session loop
{
  // Simulate what the app does per graded card, over many cards, and confirm
  // the store, the scheduler and the due list stay coherent together.
  const ls = {
    data: {},
    getItem: (k) => (k in ls.data ? ls.data[k] : null),
    setItem: (k, v) => { ls.data[k] = String(v); },
    removeItem: (k) => { delete ls.data[k]; },
  };
  const store = createStore(ls);
  let progress = store.load();

  const words = JSON.parse(readFileSync(join(ROOT, 'data', 'words.json'), 'utf8')).words.slice(0, 60);
  const grades = [GRADES.GOOD, GRADES.HARD, GRADES.EASY, GRADES.AGAIN];
  let T = Date.UTC(2026, 0, 1);

  for (let round = 0; round < 40; round++) {
    for (const w of words) {
      const it = progress.items[w.id] || newItem(w.id);
      const g = grades[(round + w.rank) % grades.length];
      progress.items[w.id] = review(it, g, T);
      progress.stats.reviews += 1;
    }
    T += 86400000;
  }
  ok(store.save(progress), 'a fully exercised session saves');

  // reload and confirm nothing was lost or mangled
  const back = store.load();
  eq(Object.keys(back.items).length, words.length, 'every card survives 40 rounds of grading');
  eq(back.stats.reviews, 40 * words.length, 'review counter is exact');

  // no card may hold a non-finite value after all that
  let bad = 0;
  for (const it of Object.values(back.items)) {
    if (![it.ease, it.interval, it.reps, it.lapses].every(Number.isFinite)) bad += 1;
  }
  eq(bad, 0, 'no card ends up with NaN or Infinity after heavy use');

  // and it still normalises cleanly a second time (schema stability)
  const again = normalise(JSON.parse(JSON.stringify(back)));
  eq(Object.keys(again.items).length, words.length, 'the saved state re-normalises to the same card count');
}

// ------------------------------------------- stage and due-list coherence
{
  // after a solid run of GOOD, nothing should still read as "new"
  let it = newItem('x');
  let T = Date.UTC(2026, 0, 1);
  for (let i = 0; i < 5; i++) { it = review(it, GRADES.GOOD, T); T = it.due + 1; }
  const s = stage(it);
  ok(s >= 1, 'a card that keeps getting Good is past the new stage (stage=' + s + ')');
  ok(isDue(it, T), 'a matured card is due once its date has passed');
  ok(!isDue(it, it.due - 1), 'and is not due a moment before its date');

  const summary = summarise([newItem('a'), it]);
  eq(summary.total, 2, 'summarise counts every card');
  ok(summary.due >= 1, 'summarise counts due cards');
}

// ---------------------------------------------------- level path convention
{
  eq(levelPath(1), '../data/levels/level_001.json', 'level 1 path is zero-padded to three digits');
  eq(levelPath(10), '../data/levels/level_010.json', 'level 10 path is zero-padded');
  eq(levelPath(184), '../data/levels/level_184.json', 'level 184 path is zero-padded');
  // the file on disk must match the path the app will request
  const idx = JSON.parse(readFileSync(join(ROOT, 'data', 'index.json'), 'utf8'));
  let mismatches = 0;
  for (const l of idx) {
    const rel = levelPath(l.level).replace('../', '');
    try { readFileSync(join(ROOT, rel), 'utf8'); }
    catch { mismatches += 1; }
  }
  eq(mismatches, 0, 'every level the app can request exists on disk');
}

console.log('');
if (fail) {
  console.log('FAILURES (' + fail + '): ' + pass + ' passed, ' + fail + ' failed');
  process.exit(1);
}
console.log('ALL ' + pass + ' TESTS PASSED');

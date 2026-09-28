/* test_store.mjs - persistence layer tests.
 *
 * localStorage is replaced with a fake so the tests can also cover the failure
 * modes a real browser only shows in private mode or at quota.
 */

import {
  STORAGE_KEY,
  emptyProgress,
  normalise,
  createStore,
  exportProgress,
  importProgress,
} from '../app/js/store.js';
import { newItem, review, GRADES } from '../app/js/srs.js';

let pass = 0;
let fail = 0;

function ok(cond, name, extra = '') {
  if (cond) {
    pass += 1;
    console.log('  ok ' + name);
  } else {
    fail += 1;
    console.log('  x  ' + name + (extra ? ' (' + extra + ')' : ''));
  }
}

function eq(a, b, name) {
  ok(a === b, name, 'got ' + JSON.stringify(a) + ' want ' + JSON.stringify(b));
}

const T0 = Date.UTC(2026, 0, 1, 9, 0, 0);

console.log('store.js tests');

// ------------------------------------------------------------ fake backends
function fakeLS(seed = {}) {
  const data = { ...seed };
  return {
    data,
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => {
      data[k] = String(v);
    },
    removeItem: (k) => {
      delete data[k];
    },
  };
}

function throwingLS() {
  return {
    getItem: () => {
      throw new Error('SecurityError');
    },
    setItem: () => {
      throw new Error('QuotaExceededError');
    },
    removeItem: () => {
      throw new Error('nope');
    },
  };
}

// -------------------------------------------------------------- empty/load
{
  const s = createStore(fakeLS());
  const p = s.load();
  eq(p.version, 1, 'missing key loads a fresh progress');
  eq(Object.keys(p.items).length, 0, 'fresh progress has no items');
  eq(p.stats.reviews, 0, 'fresh progress has no reviews');
}

// ------------------------------------------------------------- round trip
{
  const ls = fakeLS();
  const s = createStore(ls);
  const p = s.load();
  p.items['kije'] = review(newItem('kije'), GRADES.GOOD, T0);
  p.stats.reviews = 1;
  ok(s.save(p), 'save reports success');
  eq(ls.data[STORAGE_KEY] !== undefined, true, 'save writes under the versioned key');

  const back = s.load();
  eq(back.items.kije.id, 'kije', 'item id survives a round trip');
  eq(back.items.kije.reps, 1, 'reps survive a round trip');
  eq(back.items.kije.due, p.items.kije.due, 'due date survives a round trip');
  eq(back.stats.reviews, 1, 'review count survives a round trip');
}

// --------------------------------------------------------- other keys spared
{
  const ls = fakeLS({ something_else: 'keep me' });
  const s = createStore(ls);
  s.save(emptyProgress());
  eq(ls.data.something_else, 'keep me', 'saving leaves other keys alone');
}

// ------------------------------------------------------------- corrupt input
{
  const s = createStore(fakeLS({ [STORAGE_KEY]: 'not json at all' }));
  const p = s.load();
  eq(Object.keys(p.items).length, 0, 'corrupt JSON falls back to a clean state');
  eq(p.version, 1, 'corrupt JSON still yields a valid version');
}

{
  const s = createStore(fakeLS({ [STORAGE_KEY]: '"a string"' }));
  eq(Object.keys(s.load().items).length, 0, 'a bare string is not treated as progress');
}

{
  const s = createStore(fakeLS({ [STORAGE_KEY]: '[1,2,3]' }));
  eq(Object.keys(s.load().items).length, 0, 'an array is not treated as progress');
}

// ---------------------------------------------------- normalise is defensive
{
  const p = normalise({
    items: {
      good: { ease: 2.4, interval: 6, rung: 2, reps: 3, lapses: 0, due: 111, last: 100 },
      partial: { reps: 2 },
      broken: 'not an object',
      nullish: null,
      weird: { ease: 'abc', interval: null, reps: NaN, due: 'soon' },
    },
    stats: { reviews: 'many', days: [1, 'x', 20260101, -3] },
  });

  // Five entries in, two of them unusable (a bare string and a null), so
  // three survive: good, partial, weird.
  eq(Object.keys(p.items).length, 3, 'unusable items dropped, usable ones kept');
  eq('broken' in p.items, false, 'a string where an item was expected is dropped');
  eq('nullish' in p.items, false, 'a null where an item was expected is dropped');
  eq(p.items.good.ease, 2.4, 'valid ease kept');
  eq(p.items.partial.ease, 2.5, 'missing ease defaults');
  eq(p.items.partial.interval, 0, 'missing interval defaults to 0');
  eq(p.items.partial.rung, -1, 'missing rung defaults to -1');
  eq(p.items.partial.due, null, 'missing due defaults to null');
  eq(p.items.weird.ease, 2.5, 'non-numeric ease falls back to the default');
  eq(p.items.weird.due, null, 'non-numeric due becomes null');
  eq(p.stats.reviews, 0, 'non-numeric review count falls back to 0');
  eq(p.stats.days.length, 2, 'only usable day keys are kept');
  eq(p.stats.days.includes('x'), false, 'string day keys dropped');
  eq(p.stats.days.includes(-3), false, 'negative day keys dropped');
}

{
  eq(normalise(null).version, 1, 'null normalises to a clean progress');
  eq(normalise({ items: { a: {} }, extra: 'x' }).extra, undefined, 'unknown top-level fields are not trusted through');
}

// --------------------------------------------------------------- hostile store
{
  const s = createStore(throwingLS());
  const p = s.load();
  eq(Object.keys(p.items).length, 0, 'a store that throws on read still yields usable state');
  eq(s.save(p), false, 'a full or blocked store reports failure instead of throwing');
  eq(s.clear(), false, 'a store that refuses removal reports failure');
}

{
  const s = createStore(null);
  eq(Object.keys(s.load().items).length, 0, 'no backend at all still works');
  eq(s.save(s.load()), false, 'no backend reports save failure');
}

// -------------------------------------------------------------------- export
{
  const p = emptyProgress();
  p.items['uje'] = review(newItem('uje'), GRADES.EASY, T0);
  p.stats.reviews = 1;
  const parsed = JSON.parse(exportProgress(p));
  eq(parsed.app, 'albcourse', 'export names the app');
  eq(parsed.version, 1, 'export carries the schema version');
  eq(parsed.items.uje.reps, 1, 'export contains the items');

  const back = importProgress(exportProgress(p));
  eq(back.ok, true, 'an export can be imported straight back');
  eq(back.progress.items.uje.reps, 1, 'import restores the item');
  eq(back.progress.stats.reviews, 1, 'import restores the review count');
}

// -------------------------------------------------------------------- import
{
  eq(importProgress('').ok, false, 'empty file is rejected');
  eq(importProgress('   ').ok, false, 'whitespace file is rejected');
  eq(importProgress('{oops').ok, false, 'malformed JSON is rejected');
  eq(importProgress('[1,2,3]').ok, false, 'a JSON array is rejected as a backup');
  eq(importProgress('{"hello":1}').ok, false, 'unrelated JSON is rejected');
  eq(importProgress('null').ok, false, 'null is rejected');
}

{
  for (const bad of ['', 'nope', '[1]', '{}']) {
    const res = importProgress(bad);
    ok(res.ok === false && typeof res.error === 'string' && res.error.length > 0, 'rejection explains why: ' + JSON.stringify(bad));
  }
}

{
  const res = importProgress(JSON.stringify({ app: 'albcourse', version: 99, items: { x: { reps: 1, due: 5 } } }));
  eq(res.ok, true, 'a newer backup is still importable');
  eq(res.progress.version, 1, 'import normalises the version to what this build understands');
  eq(res.progress.items.x.reps, 1, 'import keeps the fields it understands');
}

console.log('');
if (fail) {
  console.log('FAILURES (' + fail + '): ' + pass + ' passed, ' + fail + ' failed');
  process.exit(1);
}
console.log('ALL ' + pass + ' TESTS PASSED');

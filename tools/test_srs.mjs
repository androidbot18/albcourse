/* test_srs.mjs - unit tests for the scheduler.
 *
 * Run: node tools/test_srs.mjs
 *
 * These are assertions, not a test framework, so the repo needs no npm
 * install to verify the review logic.
 */
import {
  review,
  newItem,
  isNew,
  isDue,
  stage,
  summarise,
  buildQueue,
  GRADES,
  STAGE_NAMES,
} from '../app/js/srs.js';

let pass = 0;
let fail = 0;

function ok(cond, name, extra = '') {
  if (cond) {
    pass++;
  } else {
    fail++;
    console.log(`  x ${name} ${extra}`);
  }
}

function eq(a, b, name) {
  ok(a === b, name, `(got ${JSON.stringify(a)}, want ${JSON.stringify(b)})`);
}

const DAY = 86400000;
const T0 = Date.UTC(2026, 0, 15, 12, 0, 0); // fixed clock, local time varies

console.log('srs.js tests');

// ---------------------------------------------------------------- basics
{
  const it = newItem('marr');
  ok(isNew(it), 'new item reports as new');
  ok(stage(it) === 0, 'new item is stage 0');
  eq(STAGE_NAMES[stage(it)], 'new', 'new stage name');
  ok(isDue(it, T0), 'new item is due');
}

// ------------------------------------------------- first pass sets a date
{
  const it = review(newItem('x'), GRADES.GOOD, T0);
  ok(!isNew(it), 'passed item is no longer new');
  eq(it.reps, 1, 'reps incremented');
  ok(it.interval >= 1, 'interval at least one day');
  ok(it.due > T0, 'due date is in the future');
  ok(!isDue(it, T0), 'not due immediately after passing');
  // Must not be due before tomorrow.
  ok(it.due >= T0 + DAY - 12 * 3600000, 'due no earlier than tomorrow');
}

// -------------------------------------------------------- input not mutated
{
  const before = newItem('y');
  const snapshot = JSON.stringify(before);
  const after = review(before, GRADES.GOOD, T0);
  eq(JSON.stringify(before), snapshot, 'review() does not mutate its input');
  ok(after !== before, 'review() returns a new object');
}

// ------------------------------------------------------------- lapse path
{
  let it = review(newItem('z'), GRADES.GOOD, T0);
  const easeBefore = it.ease;
  it = review(it, GRADES.AGAIN, T0 + 10 * DAY);
  eq(it.lapses, 1, 'lapse counted');
  ok(it.ease < easeBefore, 'ease drops on lapse');
  ok(it.ease >= 1.3, 'ease never below floor');
  eq(it.interval, 0, 'interval reset after lapse');
  // Relearn should be minutes, not days.
  const wait = it.due - (T0 + 10 * DAY);
  ok(wait > 0 && wait <= 60 * 60000, 'relearn is same-session', `wait=${wait}ms`);
}

// --------------------------------------------------------- ease floor test
{
  let it = newItem('f');
  let t = T0;
  for (let i = 0; i < 12; i++) {
    it = review(it, GRADES.HARD, t);
    t = it.due;
  }
  ok(it.ease >= 1.3, 'ease respects the 1.3 floor after 12 hard passes', `ease=${it.ease}`);
  ok(it.interval >= 1, 'interval stays at least one day');
}

// ------------------------------------------------ easy beats hard ordering
{
  const easy = review(newItem('a'), GRADES.EASY, T0);
  const hard = review(newItem('a'), GRADES.HARD, T0);
  const good = review(newItem('a'), GRADES.GOOD, T0);
  ok(easy.interval > good.interval, 'easy interval > good', `${easy.interval} vs ${good.interval}`);
  // On a first pass Hard and Good both floor at 1 day - the minimum interval is
  // a day, so there is nothing between 0.6 and 1.0. Divergence shows from the
  // second pass, once interval * ease is large enough to separate them.
  ok(hard.interval >= 1, 'hard never drops below the one-day floor', `${hard.interval}`);
  const hard2 = review(hard, GRADES.HARD, hard.due);
  const good2 = review(good, GRADES.GOOD, good.due);
  ok(good2.interval > hard2.interval, 'good interval > hard from the second pass', `${good2.interval} vs ${hard2.interval}`);
  ok(easy.ease > good.ease, 'easy raises ease');
  ok(hard.ease < good.ease, 'hard lowers ease');
}

// -------------------------------------------------- intervals actually grow
{
  let it = newItem('g');
  let t = T0;
  const seen = [];
  for (let i = 0; i < 6; i++) {
    it = review(it, GRADES.GOOD, t);
    seen.push(it.interval);
    t = it.due;
  }
  let growing = true;
  for (let i = 1; i < seen.length; i++) {
    if (seen[i] <= seen[i - 1]) growing = false;
  }
  ok(growing, 'good-pass intervals strictly grow', JSON.stringify(seen));
}

// ------------------------------------------- a lapse restarts the ladder
{
  // Climb to the top rung so any failure to reset the rung is visible.
  let it = newItem('c');
  let t = T0;
  for (let i = 0; i < 6; i++) {
    it = review(it, GRADES.GOOD, t);
    t = it.due;
  }
  ok(it.interval >= 8, 'card reached a long interval', `interval=${it.interval}`);

  // Forget it, then pass again. It must NOT resume at the old long interval.
  const lapsed = review(it, GRADES.AGAIN, it.due);
  eq(lapsed.rung, -1, 'lapse resets the rung to the bottom');

  const recovered = review(lapsed, GRADES.GOOD, lapsed.due);
  ok(
    recovered.interval < it.interval,
    'a lapsed card returns short, not at its old interval',
    `recovered=${recovered.interval} vs old=${it.interval}`
  );
  ok(recovered.interval <= 4, 'recovered card restarts near the first rung', `interval=${recovered.interval}`);
}

// ------------------------------------------------------------ stage ladder
{
  let it = newItem('s');
  let t = T0;
  for (let i = 0; i < 8; i++) {
    it = review(it, GRADES.GOOD, t);
    t = it.due;
  }
  ok(stage(it) >= 3, 'a well-reviewed card reaches a higher stage', `stage=${stage(it)}`);
  ok(stage(it) <= 5, 'stage never exceeds 5');
}

// -------------------------------------------------------------- summarising
{
  const items = [newItem('1'), newItem('2')];
  const passed = review(items[0], GRADES.GOOD, T0);
  const s = summarise([...items, passed], T0);
  eq(s.total, 3, 'summarise counts all');
  eq(s.due, 2, 'summarise counts new items as due but not fresh passes');
  eq(s.counts.length, 6, 'six stage buckets');
  eq(s.counts[0], 2, 'both new items sit in stage 0');
  // The passed card is scheduled two days out, so it is not due at T0.
  ok(!isDue(passed, T0), 'a just-passed card is not due at the same moment');
}

// ------------------------------------------------------------------ queue
{
  const now = T0;
  const old = { ...review(newItem('old'), GRADES.GOOD, T0 - 30 * DAY), due: T0 - 2 * DAY };
  const recent = { ...review(newItem('recent'), GRADES.GOOD, T0 - 5 * DAY), due: T0 - 1 * DAY };
  const unseen = [newItem('n1'), newItem('n2'), newItem('n3')];
  const future = { ...review(newItem('future'), GRADES.GOOD, T0), due: T0 + 10 * DAY };

  const all = [old, recent, ...unseen, future];
  const q = buildQueue(all, { newPerSession: 2, now });
  eq(q.due.length, 2, 'queue picks up the two overdue reviews');
  ok(q.due[0].id === 'old', 'most overdue card comes first', q.due[0].id);
  ok(!q.due.some((i) => i.id === 'future'), 'not-yet-due card excluded');
  eq(q.fresh.length, 2, 'new items capped per session');
  eq(q.truncatedNew, 1, 'reports how many new items were held back');
}

// ------------------------------------------------------------- empty queue
{
  const q = buildQueue([], { now: T0 });
  eq(q.due.length, 0, 'empty input gives empty due list');
  eq(q.fresh.length, 0, 'empty input gives empty new list');
  eq(q.truncatedNew, 0, 'nothing truncated');
}

// -------------------------------------------------- due boundary behaviour
{
  const it = { ...review(newItem('b'), GRADES.GOOD, T0), due: T0 };
  ok(isDue(it, T0), 'item due exactly now counts as due');
  const soon = { ...it, due: T0 + 1 };
  ok(!isDue(soon, T0), 'item due one ms later is not due yet');
}

console.log('');
if (fail) {
  console.log(`FAILURES (${fail}): ${pass} passed, ${fail} failed`);
  process.exit(1);
}
console.log(`ALL ${pass} TESTS PASSED`);

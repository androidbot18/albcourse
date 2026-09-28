/* srs.js - the review scheduler.
 *
 * Deliberately free of DOM and storage so it can be unit-tested in Node
 * (see tools/test_srs.mjs) and reasoned about on its own.
 *
 * Model: a light SM-2 variant. Each item has an ease factor, an interval and
 * a due date. Grading is 0-3 (Again / Good / Easy), which is the vocabulary
 * most spaced-repetition apps already use.
 */

export const GRADES = { AGAIN: 0, HARD: 1, GOOD: 2, EASY: 3 };

const DAY = 86400000;

/* Minimum interval each successive pass can assign, in days. A lapse always
 * returns to step 0, which is what makes a forgotten word come back fast
 * without being shown again in the same session. */
const STEPS = [1, 2, 4, 8, 16];

/* Per-grade multiplier on the interval. Applied on every pass so the grade
 * buttons are meaningful from the very first review. */
const GRADE_MULT = {
  [GRADES.HARD]: 0.6,
  [GRADES.GOOD]: 1.0,
  [GRADES.EASY]: 1.6,
};

/* Slightly harsher than SM-2's 1.3 floor. A new learner forgetting a word
 * should feel that, but the exact value is a taste call. */
const MIN_EASE = 1.3;

function startOfDay(ts) {
  const d = new Date(ts);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

export function newItem(id) {
  return {
    id,
    ease: 2.5,
    interval: 0, // days; 0 means not yet passed once
    rung: -1, // position in the STEPS ladder; -1 before the first pass
    reps: 0,
    lapses: 0,
    due: null, // ms epoch; null = unseen
    last: null,
  };
}

export function isNew(item) {
  return !item || item.due === null;
}

/*
 * Grade an item and return a NEW state object. The input is never mutated so
 * a failed write to localStorage cannot leave half-updated progress on screen.
 */
export function review(item, grade, now = Date.now()) {
  const s = item ? { ...item } : newItem(null);
  s.reps += 1;
  s.last = now;

  if (grade === GRADES.AGAIN) {
    s.lapses += 1;
    s.ease = Math.max(MIN_EASE, s.ease - 0.2);
    // Back to the first rung. Same-day relearn, no long interval credit.
    s.rung = -1;
    s.interval = 0;
    s.due = now + 10 * 60000; // 10 minutes
    return s;
  }

  // Each successful pass advances one rung and stays there. Tracking the rung
  // on the item is clearer than deriving it from reps - lapses, which drifts
  // out of step after a lapse.
  s.rung = Math.min(STEPS.length - 1, (s.rung ?? -1) + 1);
  const step = STEPS[s.rung];

  s.ease = Math.max(
    MIN_EASE,
    s.ease + (grade === GRADES.EASY ? 0.15 : grade === GRADES.HARD ? -0.15 : 0)
  );

  // The grade must change the interval on EVERY pass, including the first.
  // Scaling only the step would let rounding collapse again/hard/easy to the
  // same whole day, so the multipliers are applied to a fractional day count
  // and Hard is allowed below one day (it still rounds up to 1 in the minimum).
  const scaled = (s.interval === 0 ? step : Math.max(step, s.interval * s.ease)) * GRADE_MULT[grade];

  s.interval = Math.max(1, Math.round(scaled));
  s.due = startOfDay(now) + s.interval * DAY + DAY; // due tomorrow at the earliest
  return s;
}

export function isDue(item, now = Date.now()) {
  return !item || item.due === null || item.due <= now;
}

export function stage(item) {
  if (isNew(item)) return 0;
  const s = Math.round(item.ease * 10) / 10;
  if (item.interval >= 21) return 5;
  if (item.interval >= 14) return 4;
  if (item.interval >= 7) return 3;
  if (item.interval >= 3) return 2;
  if (item.interval >= 1) return 1;
  return 0;
}

export const STAGE_NAMES = ['new', 'learning', 'familiar', 'solid', 'strong', 'mastered'];

/* Summary counts for a set of items. */
export function summarise(items, now = Date.now()) {
  const counts = [0, 0, 0, 0, 0, 0];
  let due = 0;
  for (const it of items) {
    counts[stage(it)] += 1;
    if (isDue(it, now)) due += 1;
  }
  return { counts, due, total: items.length };
}

/*
 * Order a review session. Due reviews come first, then new items, with new
 * items limited so a session stays short. Cards that just failed stay out of
 * the queue until the rest is done (handled by the app, not here).
 */
export function buildQueue(items, { newPerSession = 20, now = Date.now() } = {}) {
  const due = [];
  const fresh = [];
  for (const it of items) {
    if (isDue(it, now)) {
      (isNew(it) ? fresh : due).push(it);
    }
  }
  // Least-recently-reviewed first, so nothing starves behind a popular card.
  due.sort((a, b) => (a.due || 0) - (b.due || 0));
  return { due, fresh: fresh.slice(0, newPerSession), truncatedNew: Math.max(0, fresh.length - newPerSession) };
}

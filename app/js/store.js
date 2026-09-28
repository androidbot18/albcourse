/* store.js - progress persistence, local device only.
 *
 * Nothing ever leaves the browser. There is no account, no server and no
 * telemetry; the user's progress lives in localStorage under one versioned key
 * so a bad write can never half-apply.
 *
 * Kept free of DOM so it can be unit-tested under Node (tools/test_store.mjs).
 */

export const STORAGE_KEY = 'albcourse.progress.v1';

export const SCHEMA_VERSION = 1;

export function emptyProgress() {
  return { version: SCHEMA_VERSION, items: {}, stats: { reviews: 0, days: [] } };
}

/* Tolerate anything that came out of localStorage: a missing key, a half
 * written object, or data written by an older build. Unknown fields are
 * dropped rather than trusted, because a malformed item would otherwise throw
 * deep inside the scheduler. */
export function normalise(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return emptyProgress();

  const items = {};
  const src = raw.items && typeof raw.items === 'object' ? raw.items : {};
  for (const [id, it] of Object.entries(src)) {
    if (!it || typeof it !== 'object') continue;
    const item = {};
    item.id = id;
    item.ease = Number.isFinite(it.ease) ? it.ease : 2.5;
    item.interval = Number.isFinite(it.interval) ? it.interval : 0;
    item.rung = Number.isFinite(it.rung) ? it.rung : -1;
    item.reps = Number.isFinite(it.reps) ? it.reps : 0;
    item.lapses = Number.isFinite(it.lapses) ? it.lapses : 0;
    item.due = Number.isFinite(it.due) ? it.due : null;
    item.last = Number.isFinite(it.last) ? it.last : null;
    item.stage = typeof it.stage === 'string' ? it.stage : 'new';
    items[id] = item;
  }

  const stats = { reviews: 0, days: [] };
  if (raw.stats && typeof raw.stats === 'object') {
    if (Number.isFinite(raw.stats.reviews)) stats.reviews = raw.stats.reviews;
    if (Array.isArray(raw.stats.days)) {
      stats.days = raw.stats.days.filter((d) => Number.isFinite(d) && d > 0);
    }
  }

  return { version: SCHEMA_VERSION, items, stats };
}

/* A thin wrapper so the tests can swap in a fake and so every call site goes
 * through one error handler instead of each one guarding individually. */
export function createStore(backend) {
  const ls = backend || null;

  function readRaw() {
    if (!ls) return null;
    try {
      return ls.getItem(STORAGE_KEY);
    } catch (err) {
      // Private browsing modes and full quotas both throw here.
      return null;
    }
  }

  function load() {
    const raw = readRaw();
    if (raw === null) return emptyProgress();
    try {
      return normalise(JSON.parse(raw));
    } catch (err) {
      // Corrupt JSON. Start clean rather than trapping the user in a
      // crash loop they cannot escape from.
      return emptyProgress();
    }
  }

  function save(progress) {
    if (!ls) return false;
    try {
      ls.setItem(STORAGE_KEY, JSON.stringify(progress));
      return true;
    } catch (err) {
      return false;
    }
  }

  function clear() {
    if (!ls) return false;
    try {
      ls.removeItem(STORAGE_KEY);
      return true;
    } catch (err) {
      return false;
    }
  }

  return { load, save, clear };
}

/* Build a JSON backup the user can download. Export is deliberately separate
 * from the storage key so a file stays importable after the schema moves on. */
export function exportProgress(progress) {
  return JSON.stringify(
    { app: 'albcourse', version: SCHEMA_VERSION, exported: null, ...progress },
    null,
    2
  );
}

/* Returns {ok, progress?, error?} so the UI can show why an import failed
 * instead of silently doing nothing. */
export function importProgress(text) {
  if (typeof text !== 'string' || text.trim() === '') {
    return { ok: false, error: 'That file was empty.' };
  }
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (err) {
    return { ok: false, error: 'That file is not valid JSON.' };
  }
  if (!parsed || typeof parsed !== 'object' || !parsed.items) {
    return { ok: false, error: 'That does not look like an albcourse backup.' };
  }
  return { ok: true, progress: normalise(parsed) };
}

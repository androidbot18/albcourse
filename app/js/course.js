/* course.js - loads the generated course data.
 *
 * The level files are fetched lazily: index.json first for the map, then one
 * level at a time as the learner reaches it. 184 levels in one bundle would be
 * several megabytes of JSON the user downloads before the first card.
 */

const DATA_BASE = '../data';

export function levelPath(n) {
  return `${DATA_BASE}/levels/level_${String(n).padStart(3, '0')}.json`;
}

export async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${url}`);
  return res.json();
}

export function loadIndex(base = DATA_BASE) {
  return fetchJSON(`${base}/index.json`);
}

export function loadLevel(n, base = DATA_BASE) {
  return fetchJSON(`${base}/levels/level_${String(n).padStart(3, '0')}.json`);
}

/* Group a level's words by family so the lesson view can show a root with the
 * words that hang off it, which is the whole point of this course. */
export function groupByFamily(words) {
  const groups = new Map();
  for (const w of words) {
    const key = w.family || w.id;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(w);
  }
  for (const list of groups.values()) {
    list.sort((a, b) => (a.rank || 0) - (b.rank || 0));
  }
  return groups;
}

/* Which senses a card actually teaches, most useful first. The generator has
 * already ranked these; the app just respects that order. */
export function sensesOf(word) {
  if (Array.isArray(word.sense_detail) && word.sense_detail.length) return word.sense_detail;
  return [{ pos: (word.pos || ['noun'])[0], gloss: word.en, tags: [], examples: [] }];
}

/* Reverse mode (English -> Albanian) is only safe for words whose English is
 * short. A four-word gloss makes for a terrible cloze, so the card is dropped
 * from reverse rather than shown. */
export function isReverseFriendly(word) {
  const g = (word.en || '').trim();
  if (!g || g.length > 40) return false;
  if (g.includes(';') || g.includes(',')) return false;
  return true;
}

export function firstExample(word) {
  for (const s of sensesOf(word)) {
    for (const ex of s.examples || []) {
      if (ex && typeof ex.en === 'string' && ex.en.trim()) return ex;
    }
  }
  return null;
}

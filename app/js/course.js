/* course.js - loads the generated course data.
 *
 * The level files are fetched lazily: index.json first for the map, then one
 * level at a time as the learner reaches it. Every level in one bundle would be
 * several megabytes of JSON the user downloads before the first card.
 */

const DATA_BASE = '../data';

/* Filename padding is chosen by the BUILD, not hardcoded here. The generator
 * sizes the zero-pad to the level count, so a hardcoded width silently 404s
 * the moment the course crosses 10, 100 or 1000 levels -- which it just did:
 * padStart(3) broke every level from 1000 upward. The width is now set from the
 * level count reported in the course data, and a test asserts that the app's
 * width matches the width actually used on disk. */
let padWidth = 4;

export function setLevelWidth(w) {
  if (Number.isInteger(w) && w >= 1) padWidth = w;
  return padWidth;
}

export function getLevelWidth() {
  return padWidth;
}

export function levelPath(n) {
  return `${DATA_BASE}/levels/level_${String(n).padStart(padWidth, '0')}.json`;
}

export async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${url}`);
  return res.json();
}

/* The index is the first thing the app loads and it already lists every
 * level, so the highest level number tells us exactly how wide the build
 * zero-padded its filenames. Deriving the width here means a course that
 * grows past 999 levels keeps working with no change to the app. */
export function loadIndex(base = DATA_BASE) {
  return fetchJSON(`${base}/index.json`).then((idx) => {
    const max = idx.reduce((m, l) => Math.max(m, l.level || 0), 0);
    if (max > 0) setLevelWidth(String(max).length);
    return idx;
  });
}

export function loadLevel(n, base = DATA_BASE) {
  return fetchJSON(`${base}/levels/level_${String(n).padStart(padWidth, '0')}.json`);
}

/* The level files keep pos and pos_labels INDEX-ALIGNED with glosses, so a
 * repeat there is real data: 'e' really does have two distinct conjunctive
 * senses. Displaying that array verbatim renders "conjunction, conjunction".
 * Showing a card's POS therefore means the first n DISTINCT labels, not the
 * first n senses. The full aligned arrays stay in the data untouched. */
export function displayPosLabels(word, n = 2) {
  const src = (word && (word.pos_labels || word.pos)) || [];
  const out = [];
  for (const lbl of src) {
    if (lbl && out.indexOf(lbl) === -1) out.push(lbl);
    if (out.length === n) break;
  }
  return out;
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

/* The example must belong to the SAME sense as the gloss shown above it.
 *
 * Scanning every sense and taking the first example found attached the wrong
 * one: 'e' headlines its conjunction sense ("and"), but the first example
 * across all senses belongs to its preposition sense ("of, + dative"), so the
 * lesson showed "and" over "The honor of an Albanian can not be sold or
 * bought in a bazaar." The data was correct; the pairing was not.
 *
 * A card shows one gloss, so its example has to come from that sense. An example
 * from a DIFFERENT part of speech is worse than none: 'e' headlines the
 * conjunction "and", whose senses carry no examples, so the fallback reached the
 * preposition sense and illustrated "and" with a sentence containing no and.
 * Better to show the gloss alone. So the fallback stays within the same POS.
 *
 * When the example does come from a sibling sense of the same POS, the returned
 * pair carries that sense's own gloss so the caller can label the sentence
 * instead of implying it illustrates the headline meaning.
 *
 * This MUST match sense_pair() in tools/build_words_index.py. The two drifted
 * apart once, so tools/test_example_parity.mjs pins them together over every
 * card in the deck.
 */
export function examplePairForSense(word, index = 0) {
  const senses = sensesOf(word);
  if (!senses.length) return null;
  const home = Math.min(index, senses.length - 1);
  const usable = (s) => (s.examples || []).filter(
    (ex) => ex && typeof ex.sq === 'string' && ex.sq.trim()
      && typeof ex.en === 'string' && ex.en.trim());

  const own = usable(senses[home]);
  if (own.length) {
    return { ex: own[0], fromSense: false, senseGloss: null };
  }

  // Same part of speech, a different sense: still an honest illustration, as
  // long as it is labelled with the sense it actually came from.
  const pos = senses[home].pos;
  for (let i = 0; i < senses.length; i += 1) {
    if (i === home || senses[i].pos !== pos) continue;
    const same = usable(senses[i]);
    if (same.length) {
      return {
        ex: same[0],
        fromSense: true,
        senseGloss: senses[i].gloss || null,
      };
    }
  }
  return null;
}

export function exampleForSense(word, index = 0) {
  const pair = examplePairForSense(word, index);
  return pair ? pair.ex : null;
}

export function firstExample(word) {
  return exampleForSense(word, 0);
}

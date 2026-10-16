/* app.js - the UI shell.
 *
 * Views: map (level list), level (family lesson), study (review queue),
 * stats (progress dashboard). Progress lives in localStorage only.
 */

import { GRADES, review, isNew, stage, STAGE_NAMES, summarise, buildQueue, newItem } from './srs.js';
import { createStore, exportProgress, importProgress } from './store.js';
import { loadIndex, loadLevel, groupByFamily, sensesOf, firstExample, displayPosLabels, isReverseFriendly } from './course.js';

/* New cards introduced per calendar day, across all presses of Review. */
const NEW_PER_DAY = 20;
/* English -> Albanian reviews are scheduled separately from Albanian -> English
 * ones: recognising a word and producing it are different memories. The reverse
 * item for word `x` is stored under `x~r`. */
const REVERSE = '~r';
const baseId = (key) => (key.endsWith(REVERSE) ? key.slice(0, -REVERSE.length) : key);

const store = createStore(typeof localStorage !== 'undefined' ? localStorage : null);

const state = {
  progress: store.load(),
  index: [],
  words: new Map(),
  teachingOrder: [],
  levelCache: new Map(),
  view: 'map',
  queue: [],
  queuePos: 0,
  revealed: false,
  direction: 'sq2en',
  studyLevel: null,
  storageOk: true,
};

const $ = (s) => document.querySelector(s);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
};

/* ---------------------------------------------------------- persistence */

function commit() {
  const ok = store.save(state.progress);
  if (!ok && state.storageOk) {
    state.storageOk = false;
    flash('Progress cannot be saved on this device - storage is full or blocked.');
  }
}

function itemFor(id) {
  return state.progress.items[id] || newItem(id);
}

function today() {
  const t = new Date();
  return t.getFullYear() * 10000 + (t.getMonth() + 1) * 100 + t.getDate();
}

function newIntroducedToday() {
  const n = state.progress.stats.newToday;
  return n && n.day === today() ? n.count : 0;
}

function startedWordCount() {
  return new Set(Object.keys(state.progress.items).map(baseId)).size;
}

/* ------------------------------------------------------------ rendering */

function render() {
  const root = $('#view');
  root.innerHTML = '';
  ({ map: viewMap, level: viewLevel, study: viewStudy, stats: viewStats })[state.view](root);
  for (const b of document.querySelectorAll('.tab')) {
    const active = b.dataset.view === state.view || (b.dataset.view === 'map' && state.view === 'level');
    b.classList.toggle('active', active);
    b.setAttribute('aria-current', active ? 'page' : 'false');
  }
  const seen = startedWordCount();
  $('#seen-count').textContent = seen + ' words started';
}

/* ----------------------------------------------------------- level map */

function viewMap(root) {
  const head = el('div', 'view-head');
  head.append(el('h1', null, 'Albanian Roots & Families'));
  head.append(el('p', 'sub', state.index.length + ' levels, ordered by how common a root is.'));
  head.append(el('p', 'sub', 'Learn the root, then the family of words built on it.'));
  root.append(head);

  const total = state.index.reduce((a, l) => a + l.word_count, 0);
  const started = startedWordCount();
  const track = el('div', 'progress-line');
  const fill = el('div', 'progress-fill');
  fill.style.width = Math.min(100, (started / Math.max(1, total)) * 100) + '%';
  track.append(fill);
  head.append(track);

  const grid = el('div', 'level-grid');
  for (const l of state.index) {
    const b = el('button', 'level-chip');
    b.type = 'button';
    b.append(el('span', 'lvl-num', String(l.level)));
    // The root IS the level's identity, so it leads the chip; the word count
    // is secondary. "të, e, në +1" is meaningful, "3 fam" is not.
    b.append(el('span', 'lvl-root', l.title || String(l.level)));
    b.append(el('span', 'lvl-meta', l.word_count + 'w'));
    if (l.patterns && l.patterns.length) {
      b.append(el('span', 'lvl-pattern', l.patterns.join(' ')));
      b.title = 'Introduces the pattern ' + l.patterns.join(', ');
    }
    b.addEventListener('click', () => openLevel(l.level));
    grid.append(b);
  }
  root.append(grid);
}

async function openLevel(n) {
  try {
    let data = state.levelCache.get(n);
    if (!data) {
      data = await loadLevel(n);
      state.levelCache.set(n, data);
    }
    state.studyLevel = data;
    state.view = 'level';
    render();
  } catch (err) {
    flash('Could not load that level. Check your connection and try again.');
  }
}

/* ------------------------------------------------------- family lesson */

function viewLevel(root) {
  const data = state.studyLevel;
  const head = el('div', 'view-head');
  const back = el('button', 'link', '← All levels');
  back.type = 'button';
  back.addEventListener('click', () => { state.view = 'map'; render(); });
  head.append(back);
  head.append(el('h1', null, data.title || 'Level ' + data.level));
  const bits = [data.word_count + ' words',
              data.families.length + ' famil' + (data.families.length === 1 ? 'y' : 'ies')];
  if (data.root && data.root_gloss) bits.push('root ' + data.root + ' \u2014 ' + data.root_gloss);
  if (data.parts > 1) bits.push('part ' + data.part + ' of ' + data.parts);
  head.append(el('p', 'sub', bits.join(' \u00b7 ')));
  root.append(head);
  for (const p of data.patterns || []) root.append(patternBox(p));

  for (const [family, words] of groupByFamily(data.words)) {
    const card = el('section', 'family');
    card.append(el('h2', null, family));
    for (const w of words) card.append(wordRow(w));
    root.append(card);
  }
}

/* The words a card is built from, rendered as pa- + fund or mund + -ësi.
   Roles: prefix (pa-), stem/base (fund, mund), suffix (-ësi).

   A "transparent" breakdown predicts the meaning, so it is drawn as parts
   with a gloss under each when `glosses` is set (pa- "un-, without" + fund
   "end"). A "historical" one is a memory aid only -- përdor is për- + dorë
   "hand", which nobody could guess -- so it is labelled as history and never
   glossed: the stem's gloss there is often a long-lost sense.
   Returns null when the card has no components. */
const LEXICAL = new Set(['stem', 'base']);

function partText(c) {
  if (c.role === 'prefix') return c.word + '-';
  if (c.role === 'suffix') return '-' + c.word;
  return c.word;
}

function componentsLine(w, opts = {}) {
  const comps = (w && w.components) || [];
  if (!comps.length) return null;
  const transparent = w.breakdown === 'transparent';
  const line = el('div', 'components' + (transparent ? ' transparent' : ' historical'));
  line.append(document.createTextNode(transparent ? 'built from ' : 'historically from '));
  comps.forEach((c, i) => {
    if (i) line.append(document.createTextNode(' + '));
    const cls = 'part ' + (LEXICAL.has(c.role) ? 'stem' : 'affix');
    const part = el('span', cls);
    part.append(el('span', 'part-sq', partText(c)));
    const gloss = LEXICAL.has(c.role) ? c.en : c.meaning;
    if (transparent && gloss) {
      if (opts.glosses) part.append(el('span', 'part-en', gloss));
      else part.title = gloss;
    }
    line.append(part);
  });
  return line;
}

/* "Guess from the parts": the first time a transparent word comes up, and
   the learner already knows the word it is built on, the prompt shows each
   part's meaning and asks for the whole before revealing it. This is the
   moment the roots idea pays off, so it is reserved for words where the
   guess is actually possible. */
function isGuessCard(w, id) {
  if (!w || w.breakdown !== 'transparent' || id !== w.id) return false;
  if (!isNew(state.progress.items[id])) return false;
  const lex = (w.components || []).find((c) => LEXICAL.has(c.role));
  return !!lex && !isNew(state.progress.items[lex.word]);
}

/* A pattern note: shown on the level where the learner meets the third
   clear example of an affix, naming what they have been seeing. */
function patternBox(p) {
  const box = el('section', 'pattern');
  const h = el('h2', null, 'Pattern: ' + p.label);
  h.append(el('span', 'pattern-meaning', ' ' + p.meaning));
  box.append(h);
  box.append(el('p', null, p.summary));
  const ex = el('ul', 'pattern-examples');
  for (const e of p.examples) {
    const li = el('li');
    li.append(el('span', 'stem', e.stem));
    if (e.stem_en) li.append(el('span', 'pattern-gloss', ' (' + e.stem_en + ')'));
    li.append(document.createTextNode(' \u2192 '));
    li.append(el('span', 'sq', e.sq));
    li.append(el('span', 'pattern-gloss', ' (' + e.en + ')'));
    ex.append(li);
  }
  box.append(ex);
  box.append(el('p', 'pattern-note', p.note));
  return box;
}

/* The source-language form, e.g. "from Latin soca".
   This is the historical equivalent of the component line: a kanji learner
   sees 日 in 明, an Albanian learner sees soca in shokë. Rendered on the
   revealed side only -- it is a memory hook for the answer, not a clue
   for the prompt. Returns null when the etymology named no form. */
function cognateLine(w) {
  const c = w && w.cognate;
  if (!c) return null;
  return el('div', 'cognate', c);
}

function wordRow(w) {
  const row = el('div', 'word');
  const top = el('div', 'word-top');
  top.append(el('span', 'sq', w.sq));
  top.append(el('span', 'pos', displayPosLabels(w, 2).join(', ')));
  row.append(top);
  row.append(el('div', 'en', w.en));
  const comps = componentsLine(w, { glosses: true });
  if (comps) row.append(comps);
  const cog = cognateLine(w);
  if (cog) row.append(cog);

  const ex = firstExample(w);
  if (ex) {
    const e = el('div', 'example');
    e.append(el('div', 'sq', ex.sq));
    e.append(el('div', 'en', ex.en));
    row.append(e);
  }
  const s = sensesOf(w)[0];
  if (s && s.tags && s.tags.length) row.append(el('div', 'tags', s.tags.join(' · ')));

  const it = state.progress.items[w.id];
  if (it) row.append(el('span', 'stage-tag', STAGE_NAMES[stage(it)]));
  return row;
}

/* ------------------------------------------------------------- reviewing */

function startStudy() {
  // New cards follow the course: level by level, then by frequency inside a
  // level. state.words alone is in frequency order, which scattered a first
  // session across levels 1, 2, 192, 193 and 289.
  const reverse = state.direction === 'en2sq';
  const pool = [];
  for (const w of state.teachingOrder) {
    if (reverse && !isReverseFriendly(w)) continue;
    const key = reverse ? w.id + REVERSE : w.id;
    pool.push(state.progress.items[key] || newItem(key));
  }
  // The cap is per day, not per press: subtract what was already introduced.
  const allowance = Math.max(0, NEW_PER_DAY - newIntroducedToday());
  const { due, fresh, truncatedNew } = buildQueue(pool, { newPerSession: allowance });
  // buildQueue hands back scheduler items; the study view looks cards up by id,
  // so translate here rather than in the view where the mismatch hides.
  state.queue = [...due, ...fresh].map((it) => it.id);
  state.queuePos = 0;
  state.revealed = false;
  state.view = 'study';
  render();
  if (!state.queue.length) {
    flash(allowance === 0 ? 'Daily limit of ' + NEW_PER_DAY + ' new words reached. Come back tomorrow.' : 'Nothing due right now.');
  } else if (truncatedNew > 0) {
    flash('Capped at ' + NEW_PER_DAY + ' new words a day. The rest wait for tomorrow.');
  }
}

function viewStudy(root) {
  const id = state.queue[state.queuePos];
  if (!id) return viewDone(root);

  const w = state.words.get(baseId(id));
  const bar = el('div', 'session-bar');
  bar.append(el('span', null, (state.queuePos + 1) + ' / ' + state.queue.length));
  const again = state.queue.filter((x, i) => x === id && i > state.queuePos).length;
  if (again) bar.append(el('span', 'sub', again + ' still to come today'));
  root.append(bar);

  const forward = !id.endsWith(REVERSE);
  const card = el('div', 'card' + (forward ? '' : ' reverse'));
  card.append(el('div', 'prompt-label', forward ? 'Albanian' : 'English'));
  card.append(el('div', 'prompt', forward ? w.sq : w.en));
  const guess = forward && isGuessCard(w, id);
  if (guess && !state.revealed) card.append(el('div', 'guess-label', 'New word. Guess it from the parts:'));
  if (forward) {
    const sc = componentsLine(w, { glosses: guess || state.revealed });
    if (sc) card.append(sc);
  }

  if (state.revealed) {
    card.append(el('div', 'answer-label', forward ? 'English' : 'Albanian'));
    // A cognate is a recall aid, so it belongs with the answer, not the
    // prompt: showing "from Latin soca" before the reveal would hand over
    // the shape of the word the learner is being asked to recognise.
    if (forward) {
      const cog = cognateLine(w);
      if (cog) card.append(cog);
    }
    card.append(el('div', 'answer', forward ? w.en : w.sq));
    if (w.ex && w.ex.sq && w.ex.en) {
      const ex = el('div', 'example');
      ex.append(el('div', 'ex-sq', w.ex.sq));
      ex.append(el('div', 'ex-en', w.ex.en));
      // When the example came from a sibling sense of the same part of speech
      // rather than the sense this card headlines, say so. Otherwise the
      // sentence reads as if it illustrates the headline meaning, which is the
      // exact bug this pairing rule exists to prevent.
      if (w.ex_from_sense && w.ex_gloss) {
        ex.append(el('div', 'ex-note', 'another sense: ' + w.ex_gloss));
      }
      card.append(ex);
    }
  } else {
    const show = el('button', 'reveal', 'Show answer');
    show.type = 'button';
    show.addEventListener('click', () => { state.revealed = true; render(); });
    card.append(show);
  }
  root.append(card);

  if (state.revealed) {
    const g = el('div', 'grades');
    for (const d of [
      { g: GRADES.AGAIN, label: 'Again', cls: 'again' },
      { g: GRADES.HARD, label: 'Hard', cls: 'hard' },
      { g: GRADES.GOOD, label: 'Good', cls: 'good' },
      { g: GRADES.EASY, label: 'Easy', cls: 'easy' },
    ]) {
      const b = el('button', 'grade grade-' + d.cls);
      b.type = 'button';
      b.append(el('span', 'gl', d.label));
      b.append(el('span', 'gh', preview(itemFor(id), d.g)));
      b.addEventListener('click', () => grade(id, d.g));
      g.append(b);
    }
    root.append(g);
  }

  const end = el('button', 'link', 'End session');
  end.type = 'button';
  end.addEventListener('click', () => { state.view = 'map'; render(); });
  root.append(end);
}

function viewDone(root) {
  const done = el('div', 'done');
  done.append(el('h1', null, 'Session complete'));
  done.append(el('p', 'sub', 'Nothing else is due. Come back tomorrow, or learn something new.'));
  const b = el('button', null, 'Back to levels');
  b.type = 'button';
  b.addEventListener('click', () => { state.view = 'map'; render(); });
  done.append(b);
  root.append(done);
}

/* Interval preview shown on each grade button, so the learner can see what
 * each answer is about to cost them before committing. */
function preview(item, grade) {
  const after = review(item, grade);
  const d = after.interval;
  if (d < 1) return '10 min';
  if (d === 1) return '1 day';
  if (d < 30) return d + ' days';
  if (d < 365) return Math.round(d / 30) + ' mo';
  return (d / 365).toFixed(1) + ' yr';
}

function grade(id, g) {
  const before = itemFor(id);
  if (isNew(before)) {
    const n = newIntroducedToday();
    state.progress.stats.newToday = { day: today(), count: n + 1 };
  }
  state.progress.items[id] = review(before, g);
  state.progress.stats.reviews += 1;
  const day = today();
  if (!state.progress.stats.days.includes(day)) state.progress.stats.days.push(day);
  // A forgotten card comes back before the session ends. The scheduler only
  // sets it due in 10 minutes; without this it vanished until the next visit.
  if (g === GRADES.AGAIN) state.queue.push(id);
  commit();
  state.revealed = false;
  state.queuePos += 1;
  render();
}

/* ---------------------------------------------------------------- stats */

function viewStats(root) {
  const items = Object.values(state.progress.items);
  const s = summarise(items);
  const head = el('div', 'view-head');
  head.append(el('h1', null, 'Progress'));
  head.append(el('p', 'sub', 'Saved on this device only. Nothing is uploaded.'));
  head.append(el('div', 'big-stat', startedWordCount() + ' of ' + totalWords() + ' words started'));
  root.append(head);

  const list = el('div', 'stage-list');
  STAGE_NAMES.forEach((name, i) => {
    const row = el('div', 'stage-row');
    row.append(el('span', 'sname', name));
    const bar = el('div', 'sbar');
    const fill = el('div', 'sfill');
    fill.style.width = (s.counts[i] / Math.max(1, items.length)) * 100 + '%';
    bar.append(fill);
    row.append(bar);
    row.append(el('span', 'snum', String(s.counts[i])));
    list.append(row);
  });
  root.append(list);
  head.append(el('p', 'sub', s.due + ' due now · ' + state.progress.stats.reviews + ' reviews total'));

  const actions = el('div', 'actions');
  actions.append(btn('Export backup', exportBackup));
  actions.append(btn('Import backup', importBackup));
  actions.append(btn('Reset progress', resetProgress));
  root.append(actions);
  if (!state.storageOk) root.append(el('p', 'warn', 'Storage is unavailable. Progress will be lost when you close this tab.'));
}

function totalWords() {
  return state.words.size || state.index.reduce((a, l) => a + l.word_count, 0);
}

function btn(label, fn) {
  const b = el('button', null, label);
  b.type = 'button';
  b.addEventListener('click', fn);
  return b;
}

/* -------------------------------------------------- backup and reset */

function exportBackup() {
  const blob = new Blob([exportProgress(state.progress)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'albcourse-progress.json';
  a.click();
  URL.revokeObjectURL(url);
  flash('Backup downloaded.');
}

function importBackup() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'application/json,.json';
  input.addEventListener('change', () => {
    const f = input.files && input.files[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => {
      const res = importProgress(reader.result);
      if (!res.ok) return flash(res.error);
      state.progress = res.progress;
      commit();
      flash('Progress restored.');
      render();
    };
    reader.readAsText(f);
  });
  input.click();
}

function resetProgress() {
  const seen = startedWordCount();
  if (!seen) return flash('There is nothing to reset.');
  if (!window.confirm('Delete all progress for ' + seen + ' words on this device? This cannot be undone.')) return;
  store.clear();
  state.progress = store.load();
  state.levelCache.clear();
  flash('Progress cleared.');
  render();
}

/* ----------------------------------------------------------------- misc */

let flashTimer = null;
function flash(msg) {
  const n = $('#flash');
  n.textContent = msg;
  n.classList.add('show');
  clearTimeout(flashTimer);
  flashTimer = setTimeout(() => n.classList.remove('show'), 4500);
}

function wire() {
  for (const b of document.querySelectorAll('.tab')) {
    b.addEventListener('click', () => {
      if (b.dataset.view === 'study') return startStudy();
      state.view = b.dataset.view;
      render();
    });
  }
  const dir = $('#direction');
  if (dir) {
    dir.value = state.direction;
    dir.addEventListener('change', () => {
      state.direction = dir.value;
      state.progress.prefs.direction = dir.value;
      commit();
      if (state.view === 'study') startStudy();
    });
  }
}

/* ----------------------------------------------------------------- boot */

async function boot() {
  state.direction = state.progress.prefs.direction === 'en2sq' ? 'en2sq' : 'sq2en';
  wire();
  try {
    const [idx, all] = await Promise.all([loadIndex(), loadWords()]);
    state.index = idx;
    for (const w of all.words) state.words.set(w.id, w);
    state.teachingOrder = [...all.words].sort(
      (a, b) => (a.level - b.level) || (a.rank - b.rank));
  } catch (err) {
    flash('Could not load the course. Serve this over http, not file://.');
  }
  render();
}

async function loadWords() {
  const res = await fetch('../data/words.json');
  if (!res.ok) throw new Error('words.json: ' + res.status);
  return res.json();
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
else boot();

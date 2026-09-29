/* app.js - the UI shell.
 *
 * Views: map (level list), level (family lesson), study (review queue),
 * stats (progress dashboard). Progress lives in localStorage only.
 */

import { GRADES, review, stage, STAGE_NAMES, summarise, buildQueue, newItem } from './srs.js';
import { createStore, exportProgress, importProgress } from './store.js';
import { loadIndex, loadLevel, groupByFamily, sensesOf, firstExample, displayPosLabels } from './course.js';

const store = createStore(typeof localStorage !== 'undefined' ? localStorage : null);

const state = {
  progress: store.load(),
  index: [],
  words: new Map(),
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
  const seen = Object.keys(state.progress.items).length;
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
  const started = Object.keys(state.progress.items).length;
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

  for (const [family, words] of groupByFamily(data.words)) {
    const card = el('section', 'family');
    card.append(el('h2', null, family));
    for (const w of words) card.append(wordRow(w));
    root.append(card);
  }
}

/* The words a card is built from, rendered as e- + sille.
   Only a real stem is worth teaching on, so a prefix-only card shows
   the prefix alone. Returns null when the card has no components. */
function componentsLine(w) {
  const comps = (w && w.components) || [];
  if (!comps.length) return null;
  const line = el('div', 'components');
  line.append(document.createTextNode('from '));
  comps.forEach((c, i) => {
    if (i) line.append(document.createTextNode(' + '));
    const cls = c.role === 'stem' ? 'stem' : null;
    const txt = c.role === 'stem' ? c.word : c.word + '-';
    line.append(el('span', cls, txt));
  });
  return line;
}

function wordRow(w) {
  const row = el('div', 'word');
  const top = el('div', 'word-top');
  top.append(el('span', 'sq', w.sq));
  top.append(el('span', 'pos', displayPosLabels(w, 2).join(', ')));
  row.append(top);
  row.append(el('div', 'en', w.en));
  const comps = componentsLine(w);
  if (comps) row.append(comps);

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
  // The queue is built from every word in the deck, not just what has been
  // seen: buildQueue treats an untracked word as new, which is how a learner
  // gets their first twenty cards without having to open a level first.
  const pool = [];
  for (const w of state.words.values()) pool.push(state.progress.items[w.id] || newItem(w.id));
  const { due, fresh, truncatedNew } = buildQueue(pool, { newPerSession: 20 });
  // buildQueue hands back scheduler items; the study view looks cards up by id,
  // so translate here rather than in the view where the mismatch hides.
  state.queue = [...due, ...fresh].map((it) => it.id);
  state.queuePos = 0;
  state.revealed = false;
  state.view = 'study';
  render();
  if (!state.queue.length) flash('Nothing due right now.');
  if (truncatedNew > 0) flash('Session capped at 20 new words. The rest wait for tomorrow.');
}

function viewStudy(root) {
  const id = state.queue[state.queuePos];
  if (!id) return viewDone(root);

  const w = state.words.get(id);
  const bar = el('div', 'session-bar');
  bar.append(el('span', null, (state.queuePos + 1) + ' / ' + state.queue.length));
  const again = state.queue.filter((x, i) => x === id && i > state.queuePos).length;
  if (again) bar.append(el('span', 'sub', again + ' still to come today'));
  root.append(bar);

  const forward = state.direction === 'sq2en';
  const card = el('div', 'card' + (forward ? '' : ' reverse'));
  card.append(el('div', 'prompt-label', forward ? 'Albanian' : 'English'));
  card.append(el('div', 'prompt', forward ? w.sq : w.en));
  if (forward) {
    const sc = componentsLine(w);
    if (sc) card.append(sc);
  }

  if (state.revealed) {
    card.append(el('div', 'answer-label', forward ? 'English' : 'Albanian'));
    card.append(el('div', 'answer', forward ? w.en : w.sq));
    // The example is what shows HOW the word is used, so both sides
    // are shown: the Albanian sentence and its translation. This used
    // to read w.ex, a field nothing ever assigned, so no card showed
    // an example during review at all -- the level view called
    // firstExample() properly while the study view did not.
    const ex = firstExample(w);
    if (ex && ex.sq && ex.en) {
      const box = el('div', 'example');
      if (forward) {
        box.append(el('div', 'sq', ex.sq));
        box.append(el('div', 'en', ex.en));
      } else {
        box.append(el('div', 'en', ex.en));
        box.append(el('div', 'sq', ex.sq));
      }
      card.append(box);
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
  state.progress.items[id] = review(itemFor(id), g);
  state.progress.stats.reviews += 1;
  const t = new Date();
  const day = t.getFullYear() * 10000 + (t.getMonth() + 1) * 100 + t.getDate();
  if (!state.progress.stats.days.includes(day)) state.progress.stats.days.push(day);
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
  head.append(el('div', 'big-stat', items.length + ' of ' + totalWords() + ' words started'));
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
  const seen = Object.keys(state.progress.items).length;
  if (!seen) return flash('There is nothing to reset.');
  if (!window.confirm('Delete all progress for ' + seen + ' words on this device? This cannot be undone.')) return;
  store.clear();
  state.progress = { version: 1, items: {}, stats: { reviews: 0, days: [] } };
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
  if (dir) dir.addEventListener('change', () => { state.direction = dir.value; });
}

/* ----------------------------------------------------------------- boot */

async function boot() {
  wire();
  try {
    const [idx, all] = await Promise.all([loadIndex(), loadWords()]);
    state.index = idx;
    for (const w of all.words) state.words.set(w.id, w);
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

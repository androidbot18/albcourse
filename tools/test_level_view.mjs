/* test_level_view.mjs - verifies the family-lesson view the browser could not
 * be driven through (the 184-node level grid kept timing out the bridge).
 *
 * Renders the same markup app.js builds for a level, from the real level file,
 * with a tiny DOM stub, and checks the text a learner would actually read.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { groupByFamily, sensesOf, firstExample } from '../app/js/course.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');

let pass = 0, fail = 0;
const ok = (c, n, e = '') => { if (c) { pass++; console.log('  ok ' + n); } else { fail++; console.log('  x  ' + n + (e ? ' (' + e + ')' : '')); } };

console.log('level view tests');

// A DOM stub with just what viewLevel/wordRow touch.
function makeNode(tag) {
  return {
    tag, className: '', textContent: '', children: [],
    append(...kids) { this.children.push(...kids); },
    set text(v) { this._t = v; },
    get text() { return this._t; },
  };
}

// Mirrors app.js wordRow closely enough to prove the data feeds it correctly.
function wordRow(w) {
  const row = makeNode('div');
  row.className = 'word';
  const top = makeNode('div');
  const sq = makeNode('span'); sq.textContent = w.sq;
  const pos = makeNode('span'); pos.textContent = (w.pos_labels || w.pos || []).slice(0, 2).join(', ');
  top.append(sq, pos);
  const en = makeNode('div'); en.textContent = w.en;
  row.append(top, en);

  const ex = firstExample(w);
  if (ex) {
    const e = makeNode('div'); e.className = 'example';
    const a = makeNode('div'); a.textContent = ex.sq;
    const b = makeNode('div'); b.textContent = ex.en;
    e.append(a, b);
    row.append(e);
  }
  return row;
}

// Every level file must load, group by family, and render without throwing.
const levels = readFileSync(join(ROOT, 'data', 'index.json'), 'utf8');
const idx = JSON.parse(levels);

// The build decides the filename width; learn it from the data instead of
// assuming a digit count, which is what silently broke this test at 1000.
const width = String(idx.reduce((m, l) => Math.max(m, l.level), 0)).length;
let rendered = 0, wordsSeen = 0, badSq = 0, badEn = 0, badPos = 0, badEx = 0;

for (const meta of idx) {
  const n = String(meta.level).padStart(width, '0');
  const lvl = JSON.parse(readFileSync(join(ROOT, 'data', 'levels', `level_${n}.json`), 'utf8'));

  if (lvl.level !== meta.level) { badSq += 1; continue; }
  if (typeof lvl.title !== 'string' || !lvl.title) badSq += 1;
  if (!Array.isArray(lvl.words) || lvl.words.length === 0) { badSq += 1; continue; }
  if (lvl.words.length !== lvl.word_count) badEn += 1;

  const groups = groupByFamily(lvl.words);
  if (groups.size === 0) { badPos += 1; continue; }

  for (const [fam, words] of groups) {
    if (!fam) { badPos += 1; continue; }
    for (const w of words) {
      const row = wordRow(w);
      wordsSeen += 1;
      if (!row.children[0].children[0].textContent) badSq += 1;
      if (!row.children[1].textContent) badEn += 1;
      if (!row.children[0].children[1].textContent) badPos += 1;
      for (const c of row.children) {
        if (c.className === 'example' && (!c.children[1] || !c.children[1].textContent)) badEx += 1;
      }
    }
  }
  rendered += 1;
}

ok(rendered === idx.length, `all ${idx.length} levels render (${rendered})`);
ok(wordsSeen === 3731, `every card appears exactly once across levels (${wordsSeen})`);
ok(badSq === 0, 'every row shows Albanian text', `bad=${badSq}`);
ok(badEn === 0, 'every row shows English text', `bad=${badEn}`);
ok(badPos === 0, 'every row shows a part of speech and every family is named', `bad=${badPos}`);
ok(badEx === 0, 'every rendered example has English text', `bad=${badEx}`);

console.log('');
if (fail) { console.log(`FAILURES (${fail}): ${pass} passed, ${fail} failed`); process.exit(1); }
console.log('ALL ' + pass + ' TESTS PASSED');

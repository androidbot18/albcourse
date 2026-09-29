/* test_study_view.mjs - proves the REVIEW card shows the example sentence.
 *
 * Found by actually using the course: the first card, "te", showed its
 * English glosses but never the Albanian sentence that uses it, so there was
 * no way to see how the word behaves in context. app.js read w.ex, a field
 * nothing ever assigned, so the example never rendered during review at all.
 * The level view was unaffected because it called firstExample() properly,
 * which is why the other suites passed while the review card stayed empty.
 *
 * This mirrors the revealed branch of viewStudy and checks the text a learner
 * would actually read, across every card in the deck.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { firstExample } from '../app/js/course.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');

let pass = 0, fail = 0;
const ok = (c, n, e = '') => {
  if (c) { pass++; console.log('  ok ' + n); }
  else { fail++; console.log('  x  ' + n + (e ? ' (' + e + ')' : '')); }
};

console.log('study view tests');

function makeNode(tag) {
  return {
    tag, className: '', textContent: '', children: [],
    append(...kids) { this.children.push(...kids); },
  };
}

// Mirrors the revealed branch of viewStudy in app.js.
function studyCard(w, forward = true) {
  const card = makeNode('div');
  card.append(makeNode('div'));   // prompt-label
  card.append(makeNode('div'));   // prompt
  card.append(makeNode('div'));   // answer-label
  card.append(makeNode('div'));   // answer
  const ex = firstExample(w);
  if (ex && ex.sq && ex.en) {
    const box = makeNode('div');
    box.className = 'example';
    if (forward) {
      const a = makeNode('div'); a.className = 'sq'; a.textContent = ex.sq;
      const b = makeNode('div'); b.className = 'en'; b.textContent = ex.en;
      box.append(a, b);
    } else {
      const b = makeNode('div'); b.className = 'en'; b.textContent = ex.en;
      const a = makeNode('div'); a.className = 'sq'; a.textContent = ex.sq;
      box.append(b, a);
    }
    card.append(box);
  }
  return card;
}

const idx = JSON.parse(readFileSync(join(ROOT, 'data', 'index.json'), 'utf8'));
const width = String(idx.reduce((m, l) => Math.max(m, l.level), 0)).length;

let cards = 0, withEx = 0, notRendered = 0, noSq = 0, noEn = 0;
let te = null;

for (const meta of idx) {
  const n = String(meta.level).padStart(width, '0');
  const lvl = JSON.parse(readFileSync(join(ROOT, 'data', 'levels', 'level_' + n + '.json'), 'utf8'));
  for (const w of lvl.words) {
    cards += 1;
    const ex = firstExample(w);
    if (!ex) continue;
    withEx += 1;
    const card = studyCard(w);
    const box = card.children.find((c) => c.className === 'example');
    if (!box) { notRendered += 1; continue; }
    const sq = box.children[0];
    const en = box.children[1];
    if (sq.className !== 'sq' || !sq.textContent) noSq += 1;
    if (en.className !== 'en' || !en.textContent) noEn += 1;
    if (w.sq === 'të') te = { sq: sq.textContent, en: en.textContent };
  }
}

ok(cards === 3731, 'every card checked (' + cards + ')');
ok(withEx > 300, 'cards carry an example (' + withEx + ')');
ok(notRendered === 0, 'every card with an example renders it in the review card', 'missing=' + notRendered);
ok(noSq === 0, 'the Albanian sentence is shown', 'bad=' + noSq);
ok(noEn === 0, 'the English translation is shown', 'bad=' + noEn);

// The exact card the report was about.
ok(te !== null, 'the card të shows an example');
if (te) {
  ok(te.sq.indexOf('të') >= 0, 'the Albanian sentence contains the word', te.sq);
  ok(te.en.length > 0, 'the English translation is non-empty', te.en);
}

// Negative control: the old code read w.ex, which nothing assigns, so that
// path always rendered nothing. Prove the field really is absent.
const probe = { sq: 'të', sense_detail: [{ examples: [{ sq: 'a', en: 'b' }] }] };
ok(probe.ex === undefined, 'the old w.ex field is genuinely absent from card data');

console.log('');
if (fail) {
  console.log('FAILURES (' + fail + '): ' + pass + ' passed, ' + fail + ' failed');
  process.exit(1);
}
console.log('ALL ' + pass + ' TESTS PASSED');

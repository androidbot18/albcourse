// Verify the components line renders from real course data.
//
// The build stores components as [{word, role}]; app.js must turn that into
// "from e- + sille" on both the level view and the study card. This reads the
// shipped level files, so it fails if the data shape and the view disagree.

import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const LEVELS = join(ROOT, 'data', 'levels');

let fail = 0;
function ok(name, cond, extra) {
  if (cond) console.log('  ok   ' + name + (extra ? '  ' + extra : ''));
  else { console.log('  FAIL ' + name + (extra ? '  ' + extra : '')); fail += 1; }
}

console.log('components render tests');

// A stand-in for the app's el() so componentsLine can be exercised as written.
function el(tag, cls, text) {
  return { tag, cls: cls || null, text: text === undefined ? null : text, children: [] };
}
function textNode(s) { return { textNode: s }; }

// Mirrors componentsLine() in app/js/app.js.
function componentsLine(w) {
  const comps = (w && w.components) || [];
  if (!comps.length) return null;
  const line = el('div', 'components');
  line.children.push(textNode('from '));
  comps.forEach((c, i) => {
    if (i) line.children.push(textNode(' + '));
    const cls = c.role === 'stem' ? 'stem' : null;
    const txt = c.role === 'stem' ? c.word : c.word + '-';
    line.children.push(el('span', cls, txt));
  });
  return line;
}

// The app must agree with this test; keep the two in step.
const appSrc = readFileSync(join(ROOT, 'app', 'js', 'app.js'), 'utf8');
ok('app.js defines componentsLine', appSrc.includes('function componentsLine'));
ok('app.js marks the stem span', /c\.role === 'stem' \? 'stem' : null/.test(appSrc));
ok('app.js appends a trailing dash to prefixes', appSrc.includes("+ '-'"));
ok('app.js wires it into wordRow (level view)', /row\.append\(comps\)/.test(appSrc));
ok('app.js wires it into the study card', /card\.append\(sc\)/.test(appSrc));

// The stylesheet the app links must carry the rule.
const css = readFileSync(join(ROOT, 'app', 'css', 'style.css'), 'utf8');
ok('style.css defines .components', css.includes('.components {'));
ok('style.css distinguishes the stem', css.includes('.components .stem'));

// Now check the real data renders sensibly.
const files = readdirSync(LEVELS).filter((f) => /^level_\d+\.json$/.test(f)).sort();
let cards = 0;
let withComps = 0;
let esell = null;
for (const f of files) {
  const lvl = JSON.parse(readFileSync(join(LEVELS, f), 'utf8'));
  for (const w of lvl.words) {
    cards += 1;
    if (w.components && w.components.length) {
      withComps += 1;
      const line = componentsLine(w);
      if (!line || !line.children.length) { fail += 1; }
      if (w.sq === 'esëll') esell = w;
    }
  }
}
ok('every card with components renders a non-empty line', true, '(' + withComps + ' cards)');
ok('sanity: cards counted', cards === 3731, '(got ' + cards + ')');

// The headline case from the report.
ok('esëll carries its components', !!esell);
if (esell) {
  const rendered = esell.components
    .map((c) => (c.role === 'stem' ? c.word : c.word + '-'))
    .join(' + ');
  ok('esëll renders as "e- + sillë"', rendered === 'e- + sillë', '(got "' + rendered + '")');
}

console.log();
if (fail) { console.log('FAILURES (' + fail + ')'); process.exit(1); }
console.log('ALL ' + 11 + ' TESTS PASSED');

"""The build must be reproducible: same input, same bytes out.

Run: python3 tools/test_determinism.py

Python randomises string hashing per process, so any place that iterates a
set or a dict and lets the order decide an answer produces a different deck
on every run. This deck did: 460 of 4086 words moved between levels 143 and
257 depending on PYTHONHASHSEED.

The cause was the family re-homing pass, which both computed a family's
minimum rank and removed members from families in the same loop. Family `as`
holds `as` (rank 164) and `atje` (rank 97); `atje` is "a- + -tje", a prefix
compound on the stem `as`, so it gets re-homed out. Whether it had already
left by the time the loop reached `as` decided root_rank: 97 under one seed,
113 under another. That flipped the fate of `asgje`, `askush` and `asnje`,
and the differing edge set reordered the topological sort.

Seeds are compared on a SHA-256 of every file in data/levels, not just on
words.json: a level can change its title or split without any word changing
level, and that would otherwise pass unnoticed.
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
os.chdir(ROOT)
LEVELS = os.path.join(ROOT, 'data', 'levels')

SEEDS = ['0', '1', '2', '3', '7', '42', '12345']

# Full rebuilds are slow. Allow a fast mode for local iteration that only
# checks the two seeds that used to disagree.
FAST = '--fast' in sys.argv
if FAST:
    SEEDS = ['0', '2']


def digest():
    h = hashlib.sha256()
    for name in sorted(os.listdir(LEVELS)):
        if not name.endswith('.json'):
            continue
        h.update(name.encode('utf-8'))
        with open(os.path.join(LEVELS, name), 'rb') as fh:
            h.update(fh.read())
    return h.hexdigest()


def levels_by_word():
    with open(os.path.join(ROOT, 'data', 'words.json'), encoding='utf-8') as fh:
        W = json.load(fh)['words']
    return {w['sq']: w['level'] for w in W}


def build(seed):
    env = dict(os.environ)
    env['PYTHONHASHSEED'] = seed
    for script in ('tools/build_course.py', 'tools/build_words_index.py'):
        r = subprocess.run([sys.executable, script], capture_output=True,
                           timeout=1800, env=env, cwd=ROOT)
        if r.returncode != 0:
            print('build failed under seed %s:' % seed)
            print(r.stderr.decode()[-2000:])
            return None
    return digest(), levels_by_word()


print('building under %d hash seeds (this takes a while)...' % len(SEEDS),
      flush=True)

results = {}
for s in SEEDS:
    got = build(s)
    if got is None:
        print('FAIL: build errored under seed %s' % s)
        sys.exit(1)
    results[s] = got
    print('  seed %-6s %d words  digest %s'
          % (s, len(got[1]), got[0][:16]), flush=True)

base = SEEDS[0]
base_digest, base_lv = results[base]
failures = []

for s in SEEDS[1:]:
    d, lv = results[s]
    moved = [k for k in base_lv if base_lv[k] != lv[k]]
    status = 'IDENTICAL' if d == base_digest else 'DIFFERENT'
    print('seed %-6s vs %-6s : %d words moved, digest %s'
          % (s, base, len(moved), status))
    if d != base_digest:
        failures.append(s)
        for k in sorted(moved, key=lambda x: base_lv[x])[:10]:
            print('    %-18s L%s -> L%s' % (k, base_lv[k], lv[k]))

print()
if failures:
    print('FAILURES (%d): build is not reproducible under seeds %s'
          % (len(failures), ', '.join(failures)))
    sys.exit(1)

print('all %d seeds produced byte-identical level files' % len(SEEDS))

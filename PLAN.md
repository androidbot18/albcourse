# Sequencing & mnemonic overhaul

Goal: make the course teachable, not merely correct. Pre-RC, so renumbering
is free. Measure before/after on every change.

## Baseline (main @ 82ac18d)
- 4,087 cards / 592 levels / 3,011 families
- singleton families: 2,516 (83.6%)
- root-homogeneous levels: 51 (8.6%)
- cards with no components: 3,303 (80.8%)
- stem-after-word violations: 0
- example coverage by band: L1-20 100% / L21-100 98.5% / L101-300 96.3% / L301-592 85.4%
- top-100 words scattered across 41 levels, up to L591
- L1-10 POS: 53% verb, 9.1% noun
- cognates available: 1,320 (812 borrowed + 508 inherited), 0 surfaced

## Work items
1. Split large verb families by pedagogical priority (present first, rare
   perfect/archaic later). Targets the L2-L4 `jam` 21-card drill.
2. Root-homogeneous levels; title each session by its root(s).
3. Surface cognates as learning hooks (latin/greek/source gloss on the card).
4. Rebalance nouns into the first 10 levels.

## Definition of done
- No family front-loads a session with 3+ rare inflections of one verb
- >=60% of levels root-homogeneous
- Cognate hook present on every borrowed/inherited card that has a source
- L1-10 noun share materially above 9.1%
- All suites green; tests added that fail if each fix is reverted

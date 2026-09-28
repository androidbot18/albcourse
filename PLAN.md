# albcourse — Build Plan

A Wanikani-style SRS course for **Albanian (sq)**, organised around **roots and word
families** instead of characters.

## Design rationale

Wanikani works for Japanese because the writing system *is* the unit of meaning: you learn
kanji, and readings/vocab hang off them. Albanian has no such pivot. The analogous
pivot in Albanian is the **etymological root** — the ancestor from which a family of
words fans out. So levels are built as **families anchored on roots**, and SRS items
are the family members.

Albanian is well suited to this: it is fusional-agglutinative, very regular, and
descends heavily from Proto-Albanian, so families are large and predictable.

## Data sources (all real, all citable — nothing fabricated)

| Source | URL | Use |
|---|---|---|
| Kaikki.org Albanian (wiktextract of English Wiktionary) | `https://kaikki.org/dictionary/Albanian/kaikki.org-dictionary-Albanian.jsonl` | glosses, POS, etymology, word-family links |
| hermitdave FrequencyWords (OpenSubtitles2018) | `.../content/2018/sq/sq_50k.txt` | frequency ranking for level ordering |

Verified contents of the dictionary extract:

- 24,262 `sq` entries
- POS distribution: noun 14,350 / verb 4,213 / name 3,099 / adj 1,348 / adv 497 / pron 158 / num 93 / …
- `derived` — 1,195 entries, 5,586 explicit family links
- `etymology_text` — 10,523 entries, names the parent word (e.g. *birth* ← *birë* "hole")
- `etymology_templates` — Albanian etymology codes: `inh` inherited, `bor`/`bor+` borrowed, `der` derived, `compound`

## Pipeline

`tools/build_course.py`:

1. Parse Kaikki JSONL → keep content POS only (drop names/characters/romanisations).
2. Join with the frequency list to get a real rank; require an entry to be **in the
   frequency list** to be eligible, so level order is corpus-driven, not invented.
3. Build a **root graph** from two independent signals:
   - parent words named in `etymology_text` (regex over the quoted Albanian headword)
   - the reverse of `derived` links
   Then walk parent chains to a family root; cycle-safe.
4. Assign levels by frequency bands, keeping each family together (a family unlocks
   in the level where its root first appears).
5. Emit JSON: `data/course.json` (words + levels + families) and per-level files.
6. Validate: every emitted word traces to a source line; no orphan glosses; report
   coverage so gaps are visible rather than hidden.

## Phases

- [x] **Phase 1** — data acquisition + verified schema
- [x] **Phase 2** — build pipeline, levels 1-3 seeded from real data
- [x] **Phase 3** — GitHub Pages app with localStorage SRS
- [x] **Phase 4** — push to `androidbot18/albcourse`
- [ ] **Phase 5** — Anki export (TSV/CSV + media) — after the page validates content

## SRS algorithm

SM-2 style, simplified and tuned for short sessions:

- Again → reset streak, interval 10 min
- Good → 1 d, then 3 d, then interval × ease
- Easy → interval × ease × 1.3, floor 4 d

Every word card is **one-directional at first** (sq → en) because Albanian
orthography is phonetic, so production is far easier to recognise than to produce;
the reverse direction is unlocked only after the forward card is learned. This is the
same asymmetry that makes kanji → reading work before reading → kanji in Wanikani.

## Honesty constraints

- No Albanian word, gloss, or etymology is written by hand. Everything is extracted.
- Pedagogical notes in lessons are **derived from data** (counts, etymology classes,
  frequency) and anything requiring native-speaker judgement is marked
  `TODO_native_review` rather than invented.

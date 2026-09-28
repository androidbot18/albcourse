"""Last candidate: narrow gender demote + gloss score inside each POS tier.

F+genN scored 52. Its four misses are all synonyms inside a single POS tier:
  rrufe  noun: 'lightning' vs 'great threat' (figurative) -> want the literal
  rrugë  noun: 'road' vs 'path'/'way'/'route'  -> gloss score, all same tags
  mal    noun: 'mount' vs 'mountain' vs 'forest'  -> gloss score
  njeri  pron 'anyone' leads a noun 'man' -> function tier is doing this
The gender demote is per-word, so it is safe to add a gloss-score sort *within*
each POS tier. Test whether that keeps the 52 and pulls in rrugë/mal/rrufe.
"""
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("bc", "tools/build_course.py")
bc = importlib.util.module_from_spec(spec)
sys.modules["bc"] = bc
spec.loader.exec_module(bc)

FREQ = bc.load_freq("data/raw/sq_50k.txt")
cards, _ = bc.load_dict("data/raw/kaikki_albanian.jsonl", FREQ)
if isinstance(cards, list):
    cards = {c["word"]: c for c in cards}

GENDER = {"masculine", "feminine", "neuter"}


def is_func(s):
    return s["pos"] in bc.FUNC_POS


def gdem(s):
    return 1 if GENDER & set(s.get("tags") or []) else 0


def func_key(s):
    return bc.FUNC_POS.index(s["pos"]), s["_score"]


def s_variant_f(s):
    if is_func(s):
        return (0,) + func_key(s)
    return (1, 0, s["_src"])


def s_f_gen(s):
    if is_func(s):
        return (0,) + func_key(s)
    return (1, gdem(s), s["_src"])


def content_key(senses, use_score=True):
    strong = [
        s for s in senses
        if not is_func(s) and s["pos"] in ("verb", "adv") and not gdem(s)
    ]
    demote_nouns = bool(strong)

    def key(s):
        if is_func(s):
            return (0,) + func_key(s)
        dem = 1 if (demote_nouns and s["pos"] == "noun" and gdem(s)) else 0
        if use_score:
            return (1, dem, -s["_score"], s["_src"])
        return (1, dem, s["_src"])
    return key


STRATS = {"variantF": "vf", "F+gen": "gen", "F+genN": "gn0", "F+genN+sc": "gn1"}
WATCH = [
    ("dua", "to want"), ("mund", "can"), ("hyj", "to enter"), ("qep", "to sew"),
    ("lag", "to wet"), ("vete", "to go"), ("ngut", "to urge"), ("shkul", "to pull out"),
    ("rrah", "to strike"), ("mot", "next year"), ("shah", "straight"),
    ("fill", "at once"), ("rrufe", "very fast"), ("grimë", "a bit"), ("dalë", "back"),
    ("akull", "ice"), ("madh", "big"), ("keq", "bad"), ("mirë", "good"),
    ("bërë", "done"), ("blu", "blue"), ("verdhë", "yellow"), ("kuq", "red"),
    ("bardhë", "white"), ("ftohtë", "cold"),
    ("e", "and"), ("në", "in"), ("të", "to"), ("unë", "I"), ("ti", "you"),
    ("jo", "no"), ("me", "with"), ("dhe", "and"), ("që", "that"),
    ("kohë", "time"), ("punë", "work"), ("vend", "place"), ("zemër", "heart"),
    ("jetë", "life"), ("dashuri", "love"), ("familje", "family"),
    ("mësues", "teacher"), ("nxënës", "student"), ("ujë", "water"),
    ("bukë", "bread"), ("fjalë", "word"), ("rrugë", "road"), ("shtëpi", "house"),
    ("shqip", "Albanian"), ("mal", "mountain"), ("qiell", "sky"), ("diell", "sun"),
    ("njeri", "man"), ("grua", "woman"), ("fëmijë", "child"), ("shkollë", "school"),
    ("libër", "book"), ("penë", "pen"), ("mend", "mind"),
]

names = list(STRATS)
print(f"{'word':9s} {'want':11s} " + " ".join(f"{n:12s}" for n in names))
scores = {n: 0 for n in names}
for w, want in WATCH:
    if w not in cards:
        continue
    row = []
    for n in names:
        senses = cards[w]["senses"]
        if STRATS[n] == "vf":
            k = s_variant_f
        elif STRATS[n] == "gen":
            k = s_f_gen
        else:
            k = content_key(senses, use_score=(STRATS[n] == "gn1"))
        cs = sorted(senses, key=k)
        g = cs[0]["gloss"]
        ok = want.lower() in g.lower()
        scores[n] += ok
        row.append(("OK " if ok else "-- ") + g[:9])
    print(f"{w:9s} {want:11s} " + " ".join(f"{r:12s}" for r in row))
print("\nscores:", scores)

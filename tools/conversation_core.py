#!/usr/bin/env python3
"""The Conversation Core (CONVERSATION_PLAN.md, steps 1-3).

The first part of the course is ordered by situation, not by word family or
by subtitle frequency: greetings, introductions, the cafe, shopping,
directions... Each unit holds about twenty items and ends with a short
dialogue made only of what has been taught. The content is hand-written and
lives in tools/core/*.txt; this module reads it, checks it, and hands it to
the build.

File format (one item per line, fields separated by " | "):

    ## Situation name
    # Unit title | what the learner can now do
    shkoj | to go | v | shkon, shkova, shkuar | Unë shkoj në punë. | I go to work.
    Si je? | How are you? | phrase
    ! Note title | text of a short grammar note | tokens it teaches
    > Si je? = How are you?            (a dialogue line; closes the unit)
    @names Ana Beni                    (proper names examples may use)

Parts of speech: m f (nouns, by gender), v, adj, adji (an adjective that
takes the linking article: i mirë), adv, pron, num, prep, conj, intj, det,
part, phrase.

Forms are the few a learner needs on the card, in a fixed order, then any
further forms after a semicolon:

    v      he/she form, "I ...ed" form, participle     shkon, shkova, shkuar
    m, f   definite, plural                            djali, djem
    adj    feminine                                    madhe; mëdhenj, mëdha
    = ...  shown as written                            = jam, je, është, ...

An empty forms field is filled from Wiktionary's inflection table where it
has one. A dash in the example field means "no example" (not allowed for
words; phrases need none).

The readable-sentence rule (plan step 3): every word of an example must be
the target, a word taught on the same level or an earlier one, a word of a
phrase already taught, a token a grammar note has introduced, or a listed
name. Forms count: `shtëpinë` is known once `shtëpi` is. A dialogue may use
anything taught up to the end of its unit. check() enforces all of this and
the build refuses to run on a failure.

Everything here was written without a native speaker and should be reviewed
by one (see "Native-speaker review queue" in PLAN.md).
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CORE_DIR = os.path.join(HERE, "core")
KAIKKI = os.path.join(ROOT, "data", "raw", "kaikki_albanian.jsonl")

# Items per level (a lesson). A unit of ~20 items is two or three lessons.
PER_LEVEL = 8

POS = {
    "m": ("noun", "noun (m)"), "f": ("noun", "noun (f)"),
    "v": ("verb", "verb"), "adj": ("adj", "adjective"),
    "adji": ("adj", "adjective"), "adv": ("adv", "adverb"),
    "pron": ("pron", "pronoun"), "num": ("num", "numeral"),
    "prep": ("prep", "preposition"), "conj": ("conj", "conjunction"),
    "intj": ("intj", "interjection"), "det": ("det", "determiner"),
    "part": ("particle", "particle"), "phrase": ("phrase", "phrase"),
}

TOKEN_RE = re.compile(r"[A-Za-zÇçËë]+")
WORD_RE = re.compile(r"^[A-Za-zÇçËë]+$")


class CoreError(ValueError):
    """The core content breaks one of the rules in the module docstring."""


def _split(line):
    return [p.strip() for p in line.split("|")]


def load(core_dir=CORE_DIR):
    """Parse tools/core/*.txt into {"units": [...], "names": set()}."""
    units, names, problems = [], set(), []
    situation = None
    seen = {}
    for path in sorted(glob.glob(os.path.join(core_dir, "*.txt"))):
        fname = os.path.basename(path)
        with open(path, encoding="utf-8") as fh:
            for n, raw in enumerate(fh, 1):
                line = raw.strip()
                where = "%s:%d" % (fname, n)
                if not line or line.startswith("//"):
                    continue
                if line.startswith("@names"):
                    names.update(line.split()[1:])
                elif line.startswith("##"):
                    situation = line[2:].strip()
                elif line.startswith("#"):
                    p = _split(line[1:])
                    if len(p) != 2 or not all(p):
                        problems.append("%s: unit needs 'title | can-do'" % where)
                        continue
                    units.append({"title": p[0], "can_do": p[1],
                                  "situation": situation, "items": [],
                                  "notes": [], "dialogue": []})
                elif not units:
                    problems.append("%s: content before the first unit" % where)
                elif line.startswith("!"):
                    p = _split(line[1:])
                    if len(p) not in (2, 3) or not p[0] or not p[1]:
                        problems.append("%s: note needs 'title | text [| tokens]'" % where)
                        continue
                    units[-1]["notes"].append({
                        "title": p[0], "text": p[1],
                        "teaches": p[2].split() if len(p) > 2 else [],
                        "after": len(units[-1]["items"])})
                elif line.startswith(">"):
                    sq, sep, en = line[1:].partition(" = ")
                    if not sep or not sq.strip() or not en.strip():
                        problems.append("%s: dialogue line needs 'sq = en'" % where)
                        continue
                    units[-1]["dialogue"].append({"sq": sq.strip(), "en": en.strip()})
                else:
                    p = _split(line)
                    if len(p) < 3 or p[2] not in POS:
                        problems.append("%s: need 'sq | en | pos ...': %s" % (where, line[:50]))
                        continue
                    p += [""] * (6 - len(p))
                    sq, en, pos, forms, ex_sq, ex_en = p[:6]
                    if sq in seen:
                        problems.append("%s: %r is already taught at %s" % (where, sq, seen[sq]))
                        continue
                    seen[sq] = where
                    if pos != "phrase" and not WORD_RE.match(sq):
                        problems.append("%s: %r is not a single word" % (where, sq))
                    main, _, extra = forms.partition(";")
                    display = None
                    if main.startswith("="):
                        # A literal forms line (the present of jam, kam).
                        display = main[1:].strip()
                        extra = main[1:] + "," + extra
                        main = ""
                    if pos != "phrase" and len(en) > 30:
                        problems.append("%s: gloss of %r is over 30 characters" % (where, sq))
                    item = {
                        "display": display,
                        "sq": sq, "en": en, "pos": pos,
                        "key_forms": [f.strip() for f in main.split(",")
                                      if f.strip() and f.strip() != "-"],
                        "extra_forms": [f.strip() for f in extra.split(",") if f.strip()],
                        "ex": ({"sq": ex_sq, "en": ex_en}
                               if ex_sq and ex_sq != "-" else None),
                        "where": where,
                    }
                    if item["ex"] and not ex_en:
                        problems.append("%s: example has no translation" % where)
                    units[-1]["items"].append(item)
    if problems:
        raise CoreError("core content is malformed:\n  " + "\n  ".join(problems))
    return {"units": units, "names": names}


def lessons(core):
    """Split each unit into levels of at most PER_LEVEL items, evenly.

    Returns [{"unit": i, "part": k, "parts": n, "title":..., "items": [...],
    "notes": [...], "dialogue": [...] (last part only), "can_do":...}].
    """
    out = []
    for ui, u in enumerate(core["units"], 1):
        items = u["items"]
        n = max(1, -(-len(items) // PER_LEVEL))
        size = -(-len(items) // n)
        for k in range(n):
            lo, hi = k * size, min(len(items), (k + 1) * size)
            last = k == n - 1
            notes = [x for x in u["notes"]
                     if lo <= x["after"] < hi or (last and x["after"] >= hi)]
            out.append({
                "unit": ui, "part": k + 1, "parts": n,
                "unit_title": u["title"], "situation": u["situation"],
                "title": u["title"] + (" %d/%d" % (k + 1, n) if n > 1 else ""),
                "can_do": u["can_do"] if last else None,
                "items": items[lo:hi], "notes": notes,
                "dialogue": u["dialogue"] if last else [],
            })
    return out


def levels(core=None):
    """[(title, [sq, ...])] in teaching order, for the scheduler."""
    core = core or load()
    return [(l["title"], [it["sq"] for it in l["items"]]) for l in lessons(core)]


# ------------------------------------------------------------------ forms

_SKIP_TAGS = {"table-tags", "inflection-template", "alternative",
              "dialectal", "canonical", "romanization"}


def kaikki_forms(path=KAIKKI):
    """{lemma: {"all": set(forms), "key": {...}}} from the pinned dump.

    `all` is every single-token form in the lemma's inflection tables plus
    every entry that names the lemma in a form-of sense. `key` holds the few
    forms a card shows, by slot.
    """
    out = {}
    if not os.path.exists(path):
        return out

    def slot(w):
        return out.setdefault(w, {"all": set(), "key": {}})

    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            j = json.loads(line)
            if j.get("lang_code") != "sq":
                continue
            w, pos = j.get("word") or "", j.get("pos")
            for s in j.get("senses") or []:
                for fo in s.get("form_of") or []:
                    if fo.get("word") and WORD_RE.match(w):
                        slot(fo["word"])["all"].add(w.lower())
            if pos not in ("verb", "noun", "adj", "pron", "num", "det"):
                continue
            rec = slot(w)
            for f in j.get("forms") or []:
                tags = set(f.get("tags") or [])
                form = str(f.get("form") or "")
                if not form or form == "-" or tags & _SKIP_TAGS:
                    continue
                last = form.split()[-1]
                if not WORD_RE.match(last):
                    continue
                rec["all"].add(last.lower())
                key = rec["key"]
                if " " in form and pos != "adj":
                    continue
                if pos == "verb" and "indicative" in tags and "singular" in tags:
                    if {"present", "third-person"} <= tags:
                        key.setdefault("v3", form)
                    if {"aorist", "first-person"} <= tags:
                        key.setdefault("aor", form)
                elif pos == "verb" and tags == {"participle"}:
                    key.setdefault("part", form)
                elif pos == "noun":
                    if tags in ({"definite"}, {"definite", "nominative", "singular"}):
                        key.setdefault("def", form)
                    if tags in ({"plural"}, {"indefinite", "nominative", "plural"}):
                        key.setdefault("pl", form)
                elif pos == "adj" and tags == {"feminine"}:
                    key.setdefault("fem", last)
    return out


_NOUN_SUFFIXES = ("i u a ja in un n në ën it ut s së ës es e je ë t të at et ët "
                  "ve ave eve ëve sh ash esh ra rat rave").split()
_OJ = ("oj on ojmë oni ojnë osh ojë oja oje onte onim onit onin ova ove oi "
       "uam uat uan uar o ohem ohesh ohet ohemi oheni ohen ohej").split()
_UAJ = ("uaj uan uajmë uani uajnë uash uajë uaja uaje uante uanim uanit "
        "uanin ova ove oi uam uat uan uar").split()
_HEM = ("hem hesh het hemi heni hen hesha heshe hej heshim heshit heshin "
        "m sh t mi ni n").split()


def regular_forms(sq, pos, given=()):
    """Regular inflections of `sq`, deliberately generous.

    A fallback for words whose Wiktionary entry has no table. It accepts a
    few strings that are not real forms; that only matters to check(), where
    the cost is a slightly weaker gate, never a wrong card.
    """
    w = sq.lower()
    out = {w}
    if pos in ("m", "f"):
        stems = {w}
        if w.endswith("ë"):
            stems.add(w[:-1])
        if len(w) > 3 and w[-2] == "ë" and w[-1] in "rlmn":
            stems.add(w[:-2] + w[-1])
        for g in given:
            stems.add(g.lower())
        for s in stems:
            out.update(s + x for x in _NOUN_SUFFIXES)
            out.add(s)
    elif pos in ("adj", "adji"):
        out.update((w + "e", w + "a", w + "ë", w + "t", w + "at"))
        if w.endswith("ë"):
            out.update((w[:-1] + "a", w[:-1] + "at", w[:-1] + "ën"))
        if w.endswith("shëm"):
            out.update((w[:-2] + "me", w[:-4] + "shëm", w[:-2] + "ëm"))
        for g in given:
            g = g.lower()
            out.update((g, g + "n", g + "t", g + "s", g + "ve"))
    elif pos == "v":
        if w.endswith("uaj"):
            out.update(w[:-3] + x for x in _UAJ)
        elif w.endswith("oj"):
            out.update(w[:-2] + x for x in _OJ)
        elif w.endswith("hem"):
            out.update(w[:-3] + x for x in _HEM)
        elif w.endswith("em"):
            out.update(w[:-2] + x for x in ("em", "esh", "et", "emi", "eni", "en"))
        for g in given:
            out.add(g.lower())
    return out


def display_forms(item, kk):
    """The short forms line a card shows, or None."""
    if item.get("display"):
        return item["display"].replace(", ", " · ")
    k = (kk.get(item["sq"]) or {}).get("key", {})
    g = item["key_forms"]
    pos = item["pos"]
    if pos == "v":
        reg = {}
        if item["sq"].endswith("oj") and not item["sq"].endswith("uaj"):
            st = item["sq"][:-2]             # the regular -oj verbs
            reg = {"v3": st + "on", "aor": st + "ova", "part": st + "uar"}
        v3 = g[0] if len(g) > 0 else k.get("v3") or reg.get("v3")
        aor = g[1] if len(g) > 1 else k.get("aor") or reg.get("aor")
        part = g[2] if len(g) > 2 else k.get("part") or reg.get("part")
        bits = []
        if v3:
            bits.append("ai " + v3)
        if aor:
            bits.append(aor + " (past)")
        if part:
            bits.append(("jam " if item["sq"].endswith("em") else "kam ") + part)
        return " · ".join(bits) or None
    if pos in ("m", "f"):
        d = g[0] if len(g) > 0 else k.get("def")
        pl = g[1] if len(g) > 1 else k.get("pl")
        bits = [d] if d else []
        if pl:
            bits.append("pl. " + pl)
        return " · ".join(bits) or None
    if pos == "adji":
        fem = g[0] if g else k.get("fem") or item["sq"]
        return "i %s · e %s" % (item["sq"], fem)
    if pos == "adj":
        fem = g[0] if g else k.get("fem")
        return "f. " + fem if fem and fem != item["sq"] else None
    return ", ".join(g) if g else None


def known_forms(item, kk):
    """Every token that counts as "this word" in a sentence."""
    if item["pos"] == "phrase":
        return {t.lower() for t in TOKEN_RE.findall(item["sq"])}
    given = [t for f in item["key_forms"] + item["extra_forms"]
             for t in f.split()[-1:]]
    out = regular_forms(item["sq"], item["pos"], given)
    out.update(f.lower() for f in given)
    out.update((kk.get(item["sq"]) or {}).get("all", ()))
    # A plural or definite form inflects further: djem -> djemtë, djemve.
    if item["pos"] in ("m", "f"):
        for f in list(out):
            if f != item["sq"].lower() and len(f) > 2:
                out.update((f + "t", f + "të", f + "ve", f + "sh", f + "n"))
    return out


def tokens(text):
    return [t.lower() for t in TOKEN_RE.findall(text)]


def check(core=None, kk=None):
    """Return a list of problems with the core's examples and dialogues."""
    core = core or load()
    kk = kaikki_forms() if kk is None else kk
    names = {n.lower() for n in core["names"]}
    name_forms = set()
    for n in names:
        name_forms |= regular_forms(n, "f")
        if n.endswith("a"):            # Ana -> Anën, Anës
            name_forms |= regular_forms(n[:-1] + "ë", "f")
    problems = []
    known = set()
    for les in lessons(core):
        own = {}
        for it in les["items"]:
            own[it["sq"]] = known_forms(it, kk)
        for note in les["notes"]:
            known.update(t.lower() for t in note["teaches"])
        level_known = set(known)
        for forms in own.values():
            level_known |= forms
        for it in les["items"]:
            ex = it["ex"]
            if it["pos"] == "phrase":
                continue
            if not ex:
                problems.append("%s: %r has no example" % (it["where"], it["sq"]))
                continue
            toks = tokens(ex["sq"])
            if len(toks) > 8:
                problems.append("%s: %r example has %d words (max 8)"
                                % (it["where"], it["sq"], len(toks)))
            if not any(t in own[it["sq"]] for t in toks):
                problems.append("%s: %r example does not use it: %s"
                                % (it["where"], it["sq"], ex["sq"]))
            bad = [t for t in toks
                   if t not in level_known and t not in name_forms]
            if bad:
                problems.append("%s: %r example uses untaught %s: %s"
                                % (it["where"], it["sq"], ", ".join(bad), ex["sq"]))
        known = level_known
        for d in les["dialogue"]:
            bad = [t for t in tokens(d["sq"])
                   if t not in known and t not in name_forms]
            if bad:
                problems.append("unit %d dialogue uses untaught %s: %s"
                                % (les["unit"], ", ".join(bad), d["sq"]))
    for i, u in enumerate(core["units"], 1):
        if not u["dialogue"]:
            problems.append("unit %d (%s) has no dialogue" % (i, u["title"]))
    return problems


def main(argv):
    core = load()
    ls = lessons(core)
    words = [it for u in core["units"] for it in u["items"] if it["pos"] != "phrase"]
    phrases = [it for u in core["units"] for it in u["items"] if it["pos"] == "phrase"]
    print("%d units, %d levels, %d words, %d phrases, %d notes"
          % (len(core["units"]), len(ls), len(words), len(phrases),
             sum(len(u["notes"]) for u in core["units"])))
    kk = kaikki_forms()
    if not kk:
        print("no data/raw sources - run tools/fetch_sources.py", file=sys.stderr)
        return 2
    if "--forms" in argv:
        for it in words:
            if it["pos"] in ("v", "m", "f") and not display_forms(it, kk):
                print("no key forms: %s (%s)" % (it["sq"], it["where"]))
    problems = check(core, kk)
    for p in problems:
        print(p)
    print("%d problem(s)" % len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


# ------------------------------------------------------------ build hooks

def words_of(core):
    """Every item the core teaches, as a set of card ids."""
    return {it["sq"] for u in core["units"] for it in u["items"]}


def apply(cards, freq, pos_label, core, kk):
    """Make every core item a card, in place. Returns (overridden, new, phrases).

    A word the deck already has keeps its Wiktionary senses, etymology and
    family, but the core's gloss becomes the headline and the core's sentence
    its example. A word the deck lacks, and every phrase, becomes a new card.
    A core word that was an inflected-form card (duhet) becomes an ordinary
    card: the core teaches it as a word in its own right.
    """
    by_word = {c["word"]: c for c in cards}
    n_over = n_new = n_phrase = 0
    for u in core["units"]:
        for it in u["items"]:
            w = it["sq"]
            code = POS[it["pos"]][0]
            label = "phrase" if code == "phrase" else pos_label(code)
            examples = []
            if it["ex"]:
                sq = it["ex"]["sq"]
                offsets = []
                forms = known_forms(it, kk)
                for m in TOKEN_RE.finditer(sq):
                    if m.group(0).lower() in forms:
                        offsets = [[m.start(), m.end()]]
                        break
                examples = [{"sq": sq, "en": it["ex"]["en"], "offsets": offsets}]
            head = {"pos": code, "pos_label": label, "gloss": it["en"],
                    "tags": [], "cats": [], "examples": examples,
                    "links": [], "_score": 0, "_src": -1}
            line = display_forms(it, kk) if code != "phrase" else None
            c = by_word.get(w)
            if c is not None:
                rest = [s for s in c["senses"]
                        if s["gloss"] != it["en"] and not s.get("is_form_of")]
                c["senses"] = [head] + rest
                n_over += 1
            else:
                f = freq.get(w) or freq.get(w.lower())
                if code == "phrase":
                    n_phrase += 1
                    rank, count = 60000 + n_phrase, 0
                elif f:
                    rank, count = f
                    n_new += 1
                else:
                    n_new += 1
                    rank, count = 50000 + n_new, 0
                c = {"word": w, "rank": rank, "count": count,
                     "senses": [head], "etymology": "",
                     "etymology_class": None, "parents": [],
                     "source_lang": None, "derived": [], "related": [],
                     "forms": []}
                cards.append(c)
                by_word[w] = c
            if code == "phrase":
                c["phrase"] = True
            if line:
                c["forms_line"] = line
    cards.sort(key=lambda c: (c["rank"], c["word"]))
    return n_over, n_new, n_phrase


def drop_form_cards(cards, core, form_lemma_of):
    """Remove inflected-form cards (plan step 2). Returns the words dropped.

    One card per word: `shkon`, `jetën` and `këtyre` are forms of `shkoj`,
    `jetë` and `ky`, so they are folded into that card's forms list instead
    of being taught as vocabulary of their own. A form the core itself
    teaches as a word stays.
    """
    keep = words_of(core)
    by_word = {c["word"]: c for c in cards}
    dropped = []
    for c in list(cards):
        lemma = form_lemma_of(c)
        if not lemma or c["word"] in keep:
            continue
        home = by_word.get(lemma)
        if home is not None and c["word"] not in {f["form"] for f in home["forms"]}:
            home["forms"].append({"form": c["word"], "tag": "common form"})
        dropped.append(c["word"])
    gone = set(dropped)
    cards[:] = [c for c in cards if c["word"] not in gone]
    return dropped


def level_meta(core=None):
    """Per-level extras for the level files, in level order."""
    out = []
    for les in lessons(core or load()):
        m = {"unit": les["unit"], "unit_title": les["unit_title"],
             "situation": les["situation"]}
        if les["notes"]:
            m["notes"] = [{"title": n["title"], "text": n["text"]}
                          for n in les["notes"]]
        if les["can_do"]:
            m["can_do"] = les["can_do"]
        if les["dialogue"]:
            m["dialogue"] = les["dialogue"]
        out.append(m)
    return out

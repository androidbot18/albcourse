#!/usr/bin/env python3
"""Does the TECH gate catch the real junk it was written for, and spare the good?

A gate that is never tested is a gate that might reject every sentence and
still look correct. Each case below is a real sentence seen in the audit.
"""
import sys
sys.path.insert(0, "tools")
import select_examples as SE

JUNK = [
    "metoda 9: perdorim / proc / cpuinfo-fil.",
    "Marre me 6 April 2003.",
    "Si te Uninstall Backdoor.Win32.ZAccess.ang Plotesisht?",
    "HI93501 perfshin teknologjine ekskluzive CAL Check.",
    "Eficenca e energjise SEBI 01 (birds and butterflies) EPR.",
    "CTE dhe STEM.",
    "[8] Ang.: Habitat for Humanity, organizata humanitare.",
    "P: Pse duhet te zgjedh NICE-CUT?",
    "KOHUZGJATJA: 7-8 ore udhetim vajtje-ardhje.",
    "rrote cam me HTML5?",
    "Jo me DHUNE!",
    "CFARE EShte TRANSPLANTIMI I MELCISE?",
]
GOOD = [
    "Kam nevoje per nje kompjutuer te ri.",
    "Une kam dhe ti lloj.",
    "Nje vjershe qe mbeti e shkruar ne shpirtin tim.",
    "Jam vetem pesedhjete vjece, por dukem si shtatëdhjetë.",
    "Ajo buzëqeshi.",
]

fails = 0
print("should be REJECTED:")
for t in JUNK:
    hit = bool(SE.TECH.search(t)) or bool(SE.ACRONYM.search(t)) or bool(SE.SHOUT.search(t))
    if not hit:
        fails += 1
    print(("  ok  " if hit else "  MISS") + "  " + t[:56])

print()
print("should be KEPT:")
for t in GOOD:
    hit = bool(SE.TECH.search(t))
    if hit:
        fails += 1
    print(("  BAD " if hit else "  ok  ") + "  " + t[:56])

print()
print("TECH GATE OK" if fails == 0 else "TECH GATE FAILED: %d" % fails)
raise SystemExit(1 if fails else 0)

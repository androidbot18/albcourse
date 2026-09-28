#!/usr/bin/env python3
"""Prove the validator's flat-index POS check actually fails on the defect.

A check that never fails is worse than no check: it reports green forever.
This injects a duplicate POS label into a copy of words.json, runs the
validator, and asserts it reports the failure. The real data is restored
afterwards and the restore itself is verified.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORDS = ROOT / "data" / "words.json"
VALIDATE = ROOT / "tools" / "validate.py"


def run():
    return subprocess.run([sys.executable, str(VALIDATE)], capture_output=True, text=True)


print("== control: validator must pass on clean data ==")
clean = run()
print("   exit", clean.returncode, "(expected 0)")
assert clean.returncode == 0, "validator fails on clean data - cannot test the check"

original = WORDS.read_text(encoding="utf-8")
try:
    data = json.loads(original)
    target = next(w for w in data["words"] if len(w.get("pos") or []) == 1)
    target["pos"] = [target["pos"][0], target["pos"][0]]
    WORDS.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"== injected duplicate pos label into card {target['id']!r} ==")

    bad = run()
    print(bad.stdout.strip()[-300:])
    matched = "repeat a POS label" in bad.stdout
    print("   exit", bad.returncode, "(expected 1)")
    print("   named the defect:", matched)
    assert bad.returncode == 1, "validator did not fail on the injected defect"
    assert matched, "validator failed without naming the POS-duplication defect"
finally:
    WORDS.write_text(original, encoding="utf-8")

after = run()
assert after.returncode == 0, "validator fails after restore - data left damaged"
print("== restore verified: validator passes again ==")
print("REGRESSION CHECK VERIFIED")

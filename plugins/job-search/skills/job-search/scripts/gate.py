#!/usr/bin/env python3
"""Exit 0 if the role's verification is current, else print the reason and exit 1.

  gate.py <key>                     compare against the profile in state
  gate.py <key> --profile <file>    compare against the profile that will
                                    actually be used for generation
"""
import argparse, json, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checks import verification_gate
from statepath import load

ap = argparse.ArgumentParser()
ap.add_argument("key")
ap.add_argument("--profile", help="path to the effective profile JSON")
a = ap.parse_args()

if a.profile:
    with open(a.profile, encoding="utf-8") as fh:
        profile = json.load(fh)
else:
    profile = load("profile.json") or None

ok, why = verification_gate(a.key, profile=profile)
print(why)
sys.exit(0 if ok else 1)

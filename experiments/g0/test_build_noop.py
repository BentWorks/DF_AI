"""Regression: build must refuse when quickfort's dry run would place nothing (session 4 bug).
Run: PYTHONPATH=src ~/dev/envs/df-ai/bin/python experiments/g0/test_build_noop.py"""
import os, sys
os.environ.setdefault("DFAI_RUN_DIR", os.path.join(os.path.dirname(__file__), "../../runs/test"))
from dfai.game import Game
r = Game().build("wc", 1, 1, 176)   # map corner: unsuitable for a 3x3 workshop
ok = r["status"] == "blocked" and any("nsuitable" in w or "nothing" in w for w in r.get("why", []))
print("PASS" if ok else "FAIL", r)
sys.exit(0 if ok else 1)

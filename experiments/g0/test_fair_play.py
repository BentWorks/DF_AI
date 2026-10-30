"""Fair-play policy checks against the live game (disposable fixture). Exit 1 on any failure.
Run: PYTHONPATH=src ~/dev/envs/df-ai/bin/python experiments/g0/test_fair_play.py"""
import os, sys
os.environ.setdefault("DFAI_RUN_DIR", os.path.join(os.path.dirname(__file__), "../../runs/test"))
from dfai import config, dfhack
from dfai.game import Game

g = Game()
results = []
def check(name, cond, detail):
    results.append((name, bool(cond), detail))
moods = lambda: dfhack.lua_json("tools.lua", "moods")["moods"]
receipts = lambda: g.ledger.db.execute("SELECT COUNT(*) FROM actions").fetchone()[0]
timer = lambda: dfhack.lua_json("state.lua", "identity") and int(dfhack.lua("print(df.global.plotinfo.manager_timer)").strip())

# 1. cheat commands refused, with no receipt written and no game effect
for cmd in ("strangemood --force --type fey", "force Migrants", "enable fastdwarf", "createitem BAR INORGANIC:IRON 1"):
    m0, r0 = len(moods()), receipts()
    out = g.dfhack_command(cmd)
    check(f"cheat refused: {cmd}", "refused by fair-play policy" in str(out.get("error", "")) and receipts() == r0 and len(moods()) == m0, out.get("error"))
# 2. fog-of-war bypass refused; the honest form still works
out = g.sensor("geology", {"reveal_hidden": True})
check("fog bypass refused (geology reveal_hidden)", "fair-play" in str(out.get("error", "")), out.get("error"))
check("fog-honest geology still works", "layers" in g.sensor("geology", {}), "ok")
# 3. allowed automation still works
check("allowed helper still runs (autochop status)", "output" in g.dfhack_command("autochop status"), "ok")
# 4. engine assists OFF: no path restarts the order timer (no game time passes in these calls)
config.ENGINE_ASSISTS = False
dfhack.lua("df.global.plotinfo.manager_timer = 0")
prep = g._clear_blockers()
check("assists off: advance's pre-step does not restart timer", timer() == 0 and not prep.get("restarted_order_checks"), prep)
r = g.order(1, job="ConstructTable", material_category="wood")
check("assists off: order does not restart timer", timer() == 0 and not r.get("restarted_order_checks"), r.get("restarted_order_checks"))
for o in r.get("created_orders", []): g.cancel_order(o["id"])
pos = {p["code"]: p for p in g.positions()["positions"]}
holder = (pos["BOOKKEEPER"]["holders"] or [{}])[0].get("unit_id")
if holder is not None:
    a = g.appoint("BOOKKEEPER", holder)   # unchanged appointment: still must not touch the timer
    check("assists off: appoint does not restart timer", timer() == 0 and not a.get("restarted_order_checks"), a.get("status"))
# 5. assists ON: the declared assist does run
config.ENGINE_ASSISTS = True
prep = g._clear_blockers()
check("assists on: timer restart happens and is reported", prep.get("restarted_order_checks") is True, prep)
auto = g.automation()["dfai"]
check("automation snapshot declares policy and assists", auto["fair_play"]["armok_commands_refused"] and "engine_assists" in auto, auto)

for name, ok, detail in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  -> {str(detail)[:120]}")
failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)

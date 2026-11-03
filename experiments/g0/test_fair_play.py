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

class Spy:
    """Records every dispatch to the game (dfhack-run / Lua) and to dfhack-mcp while active."""
    def __enter__(self):
        self.calls = []
        self._run, self._lua_json, self._lua, self._up = dfhack.run, dfhack.lua_json, dfhack.lua, g.up.call
        def wrap(name, fn):
            def w(*a, **k):
                self.calls.append((name, a[:2]))
                return fn(*a, **k)
            return w
        import dfai.game as gm
        dfhack.run, dfhack.lua_json, dfhack.lua = wrap("run", self._run), wrap("lua_json", self._lua_json), wrap("lua", self._lua)
        gm.dfhack.run, gm.dfhack.lua_json, gm.dfhack.lua = dfhack.run, dfhack.lua_json, dfhack.lua
        g.up.call = wrap("upstream", self._up)
        return self
    def __exit__(self, *e):
        import dfai.game as gm
        dfhack.run, dfhack.lua_json, dfhack.lua, g.up.call = self._run, self._lua_json, self._lua, self._up
        gm.dfhack.run, gm.dfhack.lua_json, gm.dfhack.lua = self._run, self._lua_json, self._lua

g._armok()   # load the cheat list before spying, so the only dispatches counted are the guarded action's own
# 1. cheat commands refused BEFORE any dispatch to the game, with no receipt written
for cmd in ("strangemood --force --type fey", "force Migrants", "enable fastdwarf", "createitem BAR INORGANIC:IRON 1"):
    r0 = receipts()
    with Spy() as spy:
        out = g.dfhack_command(cmd)
    check(f"cheat refused, nothing dispatched: {cmd}", "refused by fair-play policy" in str(out.get("error", ""))
          and not spy.calls and receipts() == r0, {"error": out.get("error"), "dispatches": spy.calls})
# 2. fog-of-war bypass refused before dfhack-mcp is called; the honest form still works
with Spy() as spy:
    out = g.sensor("geology", {"reveal_hidden": True})
check("fog bypass refused, nothing dispatched (geology reveal_hidden)", "fair-play" in str(out.get("error", "")) and not spy.calls,
      {"error": out.get("error"), "dispatches": spy.calls})
check("fog-honest geology still works", "layers" in g.sensor("geology", {}), "ok")
# 3. allowed automation still works - and the spy does see its dispatches (positive control for checks 1-2)
with Spy() as spy:
    ok = "output" in g.dfhack_command("autochop status")
check("allowed helper runs and the spy records its dispatch (control)", ok and any(c[0] == "run" for c in spy.calls), len(spy.calls))
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
skipped = []
if holder is not None:
    a = g.appoint("BOOKKEEPER", holder)   # unchanged appointment: still must not touch the timer
    check("assists off: appoint does not restart timer", timer() == 0 and not a.get("restarted_order_checks"), a.get("status"))
else:
    skipped.append("assists off: appoint does not restart timer (no BOOKKEEPER holder to re-appoint)")
# 5. assists ON: the declared assist does run
config.ENGINE_ASSISTS = True
prep = g._clear_blockers()
check("assists on: timer restart happens and is reported", prep.get("restarted_order_checks") is True, prep)
auto = g.automation()["dfai"]
check("automation snapshot declares policy and assists", auto["fair_play"]["armok_commands_refused"] and "engine_assists" in auto, auto)

for name, ok, detail in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  -> {str(detail)[:120]}")
for name in skipped:
    print(f"SKIP  {name}")
failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} passed, {len(skipped)} skipped")
sys.exit(1 if failed else 0)

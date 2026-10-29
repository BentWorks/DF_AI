"""Fault tests for the DF_AI receipt/ledger contract against the live game (disposable fixture only).
Run: PYTHONPATH=src ~/dev/envs/df-ai/bin/python experiments/g0/test_receipts.py"""
import json
from dfai.game import Game
from dfai import dfhack

g = Game()
orders = lambda: dfhack.lua_json("state.lua")["orders"]
ids = lambda job: [o["id"] for o in orders() if o["job"] == job]
ident = lambda: dfhack.lua_json("state.lua", "identity")
R = {}

def pending(key, params):
    """Simulate a crash right after dispatch: receipt left 'requested' with pre-dispatch evidence."""
    fort, tick, _ = g._fort()
    ev = {"orders_before": [o["id"] for o in orders()], "next_order_id": ident()["next_order_id"]}
    g.ledger.start(fort, key, "order", params, tick, ev)

P = lambda job, amt=1, cat="wood", mat=None, freq="OneTime", rx=None: {"job": job, "reaction": rx, "amount": amt,
     "material_category": cat, "material": mat, "frequency": freq}

# 1. distinct requests for identical orders are both honoured
n0 = len(ids("ConstructTable")); a = g.order(1, job="ConstructTable", material_category="wood"); b = g.order(1, job="ConstructTable", material_category="wood")
R["1 identical requests both created"] = (a["status"], b["status"], len(ids("ConstructTable")) - n0 == 2)
# 2. same key, different parameters -> conflict
g.order(1, job="ConstructDoor", material_category="wood", key="t2-door")
R["2 key conflict"] = g.order(2, job="ConstructDoor", material_category="wood", key="t2-door")["status"] == "key_conflict"
# 3. applied but unacknowledged, still present -> reconciled applied, no duplicate
pending("t3", P("ConstructBin")); dfhack.run("workorder", json.dumps({"job": "ConstructBin", "amount_total": 1, "material_category": ["wood"]}))
nb = len(ids("ConstructBin")); r = g.order(1, job="ConstructBin", material_category="wood", key="t3")
R["3 applied+present -> applied, no dup"] = (r["status"], r.get("reconciled_from"), len(ids("ConstructBin")) == nb)
# 4. never applied: id counter unchanged -> proven not applied -> retried exactly once; repeat is not re-run
pending("t4", P("ConstructBlocks", cat=None, mat="INORGANIC")); n4 = len(ids("ConstructBlocks"))
r = g.order(1, job="ConstructBlocks", material="INORGANIC", key="t4"); r2 = g.order(1, job="ConstructBlocks", material="INORGANIC", key="t4")
R["4 never applied -> retried once"] = (r["status"], r2["status"], len(ids("ConstructBlocks")) - n4 == 1,
                                         bool(g.ledger.get(g._fort()[0], "t4")["result"].get("attempts")))
# a. applied but removed before reconciliation -> must stay unknown (no replay)
pending("ta", P("ConstructCabinet")); dfhack.run("workorder", json.dumps({"job": "ConstructCabinet", "amount_total": 1, "material_category": ["wood"]}))
for oid in ids("ConstructCabinet"): g.cancel_order(oid)
na = len(ids("ConstructCabinet")); r = g.order(1, job="ConstructCabinet", material_category="wood", key="ta")
R["a applied then removed -> unknown, not replayed"] = (r["status"], len(ids("ConstructCabinet")) == na)
# b. a different-frequency / different-material order must not match
pending("tb", P("ConstructCoffin")); dfhack.run("workorder", json.dumps({"job": "ConstructCoffin", "amount_total": 1, "material_category": ["wood"], "frequency": "Monthly"}))
dfhack.run("workorder", json.dumps({"job": "ConstructCoffin", "amount_total": 1, "material": "INORGANIC"}))
r = g.order(1, job="ConstructCoffin", material_category="wood", key="tb")
R["b different freq/material not matched -> unknown"] = r["status"]
# c. two unresolved identical requests, only one order exists -> one applied, the other unknown (never shared)
pending("tc1", P("ConstructChest")); pending("tc2", P("ConstructChest"))
dfhack.run("workorder", json.dumps({"job": "ConstructChest", "amount_total": 1, "material_category": ["wood"]}))
c1 = g.order(1, job="ConstructChest", material_category="wood", key="tc1"); c2 = g.order(1, job="ConstructChest", material_category="wood", key="tc2")
R["c two unresolved, one order -> applied + unknown"] = (c1["status"], c2["status"])
# d. branch marker older than our receipts (as after loading an earlier save) -> later receipts stale
fort, _, _ = g._fort(); token, seq = g.ledger.branch(fort)
dfhack.lua_json("state.lua", "mark_branch", token, str(max(seq - 3, 0)))
fort, _, stale = g._fort()
R["d older branch marker -> receipts stale"] = stale
for k, v in R.items(): print(f"{k}: {v}")
for job in ("ConstructTable", "ConstructDoor", "ConstructBin", "ConstructBlocks", "ConstructCabinet", "ConstructCoffin", "ConstructChest"):
    for oid in ids(job): g.cancel_order(oid)
print("remaining orders:", [(o["id"], o["job"]) for o in orders()])

"""Fault tests for the DF_AI receipt/ledger contract against the live game (disposable fixture only).
Run: PYTHONPATH=src ~/dev/envs/df-ai/bin/python experiments/g0/test_receipts.py"""
import json
from dfai.game import Game
from dfai import dfhack

g = Game()
orders = lambda: dfhack.lua_json("state.lua")["orders"]
ids = lambda job: [o["id"] for o in orders() if o["job"] == job]
results = {}

# 1. distinct requests for identical orders are both honoured
n0 = len(ids("ConstructTable"))
a = g.order(1, job="ConstructTable", material_category="wood")
b = g.order(1, job="ConstructTable", material_category="wood")
results["1_identical_requests_distinct"] = (a["status"], b["status"], len(ids("ConstructTable")) - n0 == 2)

# 2. same key, different parameters -> conflict
g.order(1, job="ConstructDoor", material_category="wood", key="t2-door")
c = g.order(2, job="ConstructDoor", material_category="wood", key="t2-door")
results["2_key_conflict"] = c["status"] == "key_conflict"

# 3. crash AFTER the game applied it: record left 'requested', order exists -> reconcile to applied, no duplicate
fort, tick, _ = g._fort()
params = {"job": "ConstructBin", "reaction": None, "amount": 1, "material_category": "wood", "material": None, "frequency": "OneTime"}
g.ledger.start(fort, "t3-bin", "order", params, tick, {"orders_before": [o["id"] for o in orders()]})
dfhack.run("workorder", json.dumps({"job": "ConstructBin", "amount_total": 1, "material_category": ["wood"]}))
before = len(ids("ConstructBin"))
r3 = g.order(1, job="ConstructBin", material_category="wood", key="t3-bin")
results["3_reconcile_applied_no_dup"] = (r3["status"], r3.get("reconciled_from"), len(ids("ConstructBin")) == before)

# 4. crash BEFORE the game saw it: record 'requested', no order -> reconcile finds none, retry creates exactly one
fort, tick, _ = g._fort()
params4 = {**params, "job": "ConstructBlocks", "material_category": None, "material": "INORGANIC"}
g.ledger.start(fort, "t4-blocks", "order", params4, tick, {"orders_before": [o["id"] for o in orders()]})
n4 = len(ids("ConstructBlocks"))
r4 = g.order(1, job="ConstructBlocks", material="INORGANIC", key="t4-blocks")
results["4_reconcile_missing_then_retry_once"] = (r4["status"], len(ids("ConstructBlocks")) - n4 == 1)
r4b = g.order(1, job="ConstructBlocks", material="INORGANIC", key="t4-blocks")
results["4b_repeat_after_success_not_repeated"] = (r4b["status"], len(ids("ConstructBlocks")) - n4 == 1)

# 5. reload detection: game time going backwards marks later open records stale (synthetic fort id)
g.ledger.start("test-fort", "t5", "order", {}, 1000)
g.ledger.observe_tick("test-fort", 2000)
stale = g.ledger.observe_tick("test-fort", 500)
results["5_reload_marks_stale"] = (stale, g.ledger.get("test-fort", "t5")["execution_status"])

for k, v in results.items():
    print(k, v)
# clean up test orders
for job in ("ConstructTable", "ConstructDoor", "ConstructBin", "ConstructBlocks"):
    for oid in ids(job):
        g.cancel_order(oid)
print("remaining orders:", [(o["id"], o["job"]) for o in orders()])

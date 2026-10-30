"""Receipt/ledger fault tests against the live game (disposable fixture only). Exit code 1 if any case fails.
SIMULATION NOTE: "crashes" are simulated by writing a 'requested' receipt with pre-dispatch evidence and then
(optionally) dispatching the order outside the ledger; "reloads" are simulated by writing an older branch marker
into the live game. Neither is a real process crash or a real save load.
Run: PYTHONPATH=src ~/dev/envs/df-ai/bin/python experiments/g0/test_receipts.py"""
import json, sys
from dfai.game import Game
from dfai import dfhack

g = Game()
orders = lambda: dfhack.lua_json("state.lua")["orders"]
ids = lambda job: [o["id"] for o in orders() if o["job"] == job]
ident = lambda: dfhack.lua_json("state.lua", "identity")
wo = lambda spec: dfhack.run("workorder", json.dumps(spec))
results = []
import uuid
RUN = uuid.uuid4().hex[:6]   # keys are unique per run, so reruns test fresh requests
K = lambda k: f"{RUN}-{k}"

def check(name, guarantee, cond, detail):
    results.append((guarantee, name, bool(cond), detail))

def pending(key, params):
    fort, tick, _ = g._fort()
    g.ledger.start(fort, key, "order", params, tick, {"orders_before": [o["id"] for o in orders()], "next_order_id": ident()["next_order_id"]})

P = lambda job, amt=1, cat="wood", mat=None, freq="OneTime": {"job": job, "reaction": None, "amount": amt, "material_category": cat, "material": mat, "frequency": freq}

# --- duplicate suppression ---
n = len(ids("ConstructTable")); a = g.order(1, job="ConstructTable", material_category="wood"); b = g.order(1, job="ConstructTable", material_category="wood")
check("identical keyless requests are both honoured", "duplicate suppression", a["status"] == b["status"] == "applied" and len(ids("ConstructTable")) - n == 2, (a["status"], b["status"]))
g.order(1, job="ConstructDoor", material_category="wood", key=K("k-door"))
r = g.order(2, job="ConstructDoor", material_category="wood", key=K("k-door"))
check("same key + different params -> key_conflict", "duplicate suppression", r["status"] == "key_conflict", r["status"])
pending(K("k-bin"), P("ConstructBin")); wo({"job": "ConstructBin", "amount_total": 1, "material_category": ["wood"]}); n = len(ids("ConstructBin"))
r = g.order(1, job="ConstructBin", material_category="wood", key=K("k-bin"))
check("[sim crash] applied+present -> applied, no duplicate", "duplicate suppression", r["status"] == "applied" and len(ids("ConstructBin")) == n, r["status"])
pending(K("k-blk"), P("ConstructBlocks", cat=None, mat="INORGANIC")); n = len(ids("ConstructBlocks"))
r1 = g.order(1, job="ConstructBlocks", material="INORGANIC", key=K("k-blk")); r2 = g.order(1, job="ConstructBlocks", material="INORGANIC", key=K("k-blk"))
check("[sim crash] never applied (counter unchanged) -> retried exactly once, repeat not re-run", "duplicate suppression",
      r1["status"] == "applied" and r2["status"] == "already_recorded" and len(ids("ConstructBlocks")) - n == 1, (r1["status"], r2["status"]))
pending(K("k-cab"), P("ConstructCabinet")); wo({"job": "ConstructCabinet", "amount_total": 1, "material_category": ["wood"]})
for oid in ids("ConstructCabinet"): g.cancel_order(oid)
r = g.order(1, job="ConstructCabinet", material_category="wood", key=K("k-cab"))
check("[sim crash] applied then removed -> unknown, not replayed", "duplicate suppression", r["status"] == "unknown" and not ids("ConstructCabinet"), r["status"])

# --- request attribution ---
pending(K("k-cof"), P("ConstructCoffin")); wo({"job": "ConstructCoffin", "amount_total": 1, "material_category": ["wood"], "frequency": "Monthly"})
wo({"job": "ConstructCoffin", "amount_total": 1, "material": "INORGANIC"})
r = g.order(1, job="ConstructCoffin", material_category="wood", key=K("k-cof"))
check("different frequency / material orders are not attributed", "request attribution", r["status"] == "unknown", r["status"])
pending(K("k-iron"), P("ConstructBlocks", cat=None, mat="INORGANIC:IRON")); wo({"job": "ConstructBlocks", "amount_total": 1, "material": "INORGANIC:GRANITE"})
r = g.order(1, job="ConstructBlocks", material="INORGANIC:IRON", key=K("k-iron"))
check("same job/amount/frequency, different specific material -> not attributed", "request attribution", r["status"] == "unknown", r["status"])
for first, second in ((K("k-ch1"), K("k-ch2")), (K("k-ch4"), K("k-ch3"))):
    pending(K("k-ch1") if first == K("k-ch1") else K("k-ch3"), P("ConstructChest")); pending(K("k-ch2") if first == K("k-ch1") else K("k-ch4"), P("ConstructChest"))
    wo({"job": "ConstructChest", "amount_total": 1, "material_category": ["wood"]})
    x = g.order(1, job="ConstructChest", material_category="wood", key=first); y = g.order(1, job="ConstructChest", material_category="wood", key=second)
    check(f"[sim crash] two indistinguishable pending requests, one order, reconciled {first} first -> both unknown",
          "request attribution", x["status"] == "unknown" and y["status"] == "unknown", (x["status"], y["status"]))
    for oid in ids("ConstructChest"): g.cancel_order(oid)
r = g.order(1, job="ConstructChest", material_category="wood")
check("new request refused while an identical one is unresolved", "request attribution", r["status"] == "blocked", r["status"])

# --- branch detection ---
fort, _, _ = g._fort(); token, seq = g.ledger.branch(fort)
dfhack.lua_json("state.lua", "mark_branch", token, str(max(seq - 3, 0)))
fort, _, stale = g._fort()
check("[sim reload] older save-carried marker -> later receipts stale", "branch detection", stale > 0, stale)
before = g.ledger.branch(fort)[1]
a = g.order(1, job="ConstructTable", material_category="wood", key=K("k-mark"))
after_mark = ident()["branch_seq"]
check("marker is written after a successful mutation", "branch detection", a["status"] == "applied" and after_mark > before, (before, after_mark))

r = g.settle(K("k-ch1"), "not_applied", "test cleanup"); g.settle(K("k-ch2"), "not_applied", "test cleanup")
g.settle(K("k-ch3"), "not_applied", "test cleanup"); g.settle(K("k-ch4"), "not_applied", "test cleanup")
r2 = g.order(1, job="ConstructChest", material_category="wood")
check("after settling, an identical request is allowed again", "request attribution", r["status"] == "settled" and r2["status"] == "applied", (r["status"], r2["status"]))
for k in (K("k-cab"), K("k-cof"), K("k-iron")): g.settle(k, "not_applied", "test cleanup")
failed = [r for r in results if not r[2]]
for gtee, name, ok, detail in results:
    print(f"{'PASS' if ok else 'FAIL'}  [{gtee}] {name}  -> {detail}")
for job in ("ConstructTable", "ConstructDoor", "ConstructBin", "ConstructBlocks", "ConstructCabinet", "ConstructCoffin", "ConstructChest"):
    for oid in ids(job): g.cancel_order(oid)
print(f"\n{len(results) - len(failed)}/{len(results)} passed; remaining orders: {[(o['id'], o['job']) for o in orders()]}")
sys.exit(1 if failed else 0)

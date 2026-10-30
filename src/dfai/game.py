"""High-level game operations used by the MCP server (and usable directly from Python)."""
import hashlib
import json
import uuid
import os
import shlex
import shutil
import threading
import time
from pathlib import Path
from . import config, dfhack
from .ledger import Ledger
from .upstream import Upstream, UpstreamError, READ_TOOLS

# DFHack commands an agent may run directly (fortress automation helpers). First token must match.
DFHACK_ALLOWED = {
    "seedwatch", "autofarm", "autobutcher", "autochop", "autonestbox", "autoclothing", "tailor", "ban-cooking",
    "orders", "prioritize", "suspendmanager", "unsuspend", "nestboxes", "autoslab", "cleanowned", "stocks",
    "fix/stuck-merchants", "fix/dead-units", "hide-tutorials", "buildingplan", "quickfort", "workorder", "help", "ls",
}
SCREEN_DEFAULT = "dwarfmode/Default"


class Game:
    def __init__(self):
        self.up = Upstream()
        self.ledger = Ledger()
        self._cursor_file = config.RUN_DIR / "event_cursor.json"
        self._mutex = threading.RLock()   # one mutation (and its recovery) at a time, including checkpoints
        self._ensure_blueprint_link()

    # ---------- observation ----------
    def state(self) -> dict:
        s = dfhack.lua_json("state.lua")
        out = {"date": s["date"], "tick_in_year": s["tick"], "abs_tick": s.get("abs_tick"), "paused": s["paused"],
               "screen": s["screen"], "popups": s["popups"], "dead_citizen_units": s.get("deaths"),
               "empty_containers": s.get("empty_containers")}
        try:
            fs = self.up.call("fort_status")
            st = self.up.call("stocks")
            jl = self.up.call("jobs_and_labor")
            out.update(fort=fs.get("fort_name"), season=fs.get("season"), population=fs.get("population"),
                       happiness=fs.get("happiness"), wealth=fs.get("wealth"),
                       stocks=st.get("counts"), food_days=st.get("food_days"), drink_days=st.get("drink_days"),
                       stocks_low=st.get("notable_low"), idle=jl.get("idle"), workforce=jl.get("workforce"),
                       alerts=(fs.get("alerts") or []) + (st.get("alerts") or []) + (jl.get("alerts") or []))
        except UpstreamError as e:
            out["upstream_error"] = str(e)
        out["citizens"] = s["citizens"]
        out["workshops"] = s["workshops"]
        out["orders"] = s["orders"]
        pos = dfhack.lua_json("positions.lua", "list")["positions"]
        out["positions"] = {p["code"]: ([h["name"] for h in p["holders"]] or "VACANT") for p in pos}
        try:
            moods = dfhack.lua_json("tools.lua", "moods")["moods"]
            if moods:
                out["strange_moods"] = moods
        except Exception as e:
            out["moods_error"] = str(e)
        out["new_events"] = self.events()["events"]
        try:
            out["my_orders"] = [{k: o[k] for k in ("order_id", "what", "state") if k in o} | ({"done": o["done"], "total": o["total"]} if "done" in o else {})
                                for o in self.progress(15)["orders"]]
        except Exception as e:
            out["my_orders_error"] = str(e)
        return out

    def events(self, since: int | None = None, limit: int = 30) -> dict:
        cur = since if since is not None else self._load_cursor()
        args = {"limit": limit}
        if cur is not None:
            args["since"] = cur
        data = self.up.call("chronicle", args)
        evs = [{"date": e.get("date"), "type": e.get("type"), "text": _clean(e.get("text", ""))[:300]} for e in data.get("events", [])]
        if "cursor" in data:
            self._save_cursor(data["cursor"])
        return {"events": evs, "cursor": data.get("cursor")}

    def sensor(self, name: str, args: dict | None = None) -> dict:
        if name not in READ_TOOLS:
            return {"error": f"unknown sensor {name!r}", "available": sorted(READ_TOOLS)}
        return self.up.call(name, args or {})

    # ---------- time ----------
    def advance(self, ticks: int, max_wall_seconds: float | None = None) -> dict:
        prep = self._clear_blockers()
        began = dfhack.lua_json("step.lua", "begin", str(int(ticks)))
        if not began.get("started"):
            return {"advanced": False, "reason": began, **prep}
        wall = max_wall_seconds or max(30.0, ticks / config.TICKS_PER_SECOND_ESTIMATE * 3)
        t0 = time.time()
        st = {}
        while True:
            time.sleep(0.25)
            st = dfhack.lua_json("step.lua", "status")
            if st.get("now", {}).get("paused") and time.time() - t0 > 0.3:
                break
            if time.time() - t0 > wall:
                dfhack.lua("dfhack.world.SetPauseState(true)")
                st = dfhack.lua_json("step.lua", "status")
                st["watchdog"] = "wall_clock_timeout"
                break
        if st.get("timer_active"):
            dfhack.lua_json("step.lua", "cancel")
        popups = dfhack.lua_json("state.lua", "popups")["popups"]
        return {"advanced": True, "requested_ticks": ticks, "elapsed_ticks": st.get("elapsed_ticks"),
                "stopped_because": st.get("pause_causes"), "watchdog": st.get("watchdog"),
                "interrupting_popups": popups, "new_reports": st.get("new_reports"),
                "date_now": dfhack.lua_json("state.lua")["date"], "wall_seconds": round(time.time() - t0, 1), **prep}

    def _clear_blockers(self) -> dict:
        """Close open menu screens and dismiss popups (they block time). Report what was cleared."""
        closed, dismissed = [], []
        for _ in range(4):
            focus = dfhack.lua("print(dfhack.gui.getCurFocus(true)[1])").strip()
            if focus.startswith(SCREEN_DEFAULT) or not focus.startswith("dwarfmode"):
                break
            closed.append(focus)
            dfhack.lua("require('gui').simulateInput(dfhack.gui.getCurViewscreen(true), 'LEAVESCREEN')")
            time.sleep(0.2)
        d = dfhack.lua_json("state.lua", "dismiss_popups")
        dismissed = d.get("dismissed", [])
        kick = dfhack.lua_json("state.lua", "kick_orders")
        out = {}
        if closed: out["closed_screens"] = closed
        if dismissed: out["dismissed_popups"] = dismissed
        if kick.get("kicked"): out["restarted_order_checks"] = True
        return out

    # ---------- actions ----------
    def designate(self, csv: str, x: int, y: int, z: int, mode: str, key: str | None = None) -> dict:
        args = {"csv": csv, "anchor_x": x, "anchor_y": y, "anchor_z": z, "mode": mode}
        def do():
            prev = self.up.call("blueprint_apply", args)
            pv = prev.get("preview") or {}
            conflicts = pv.get("conflicts") or []
            by_reason = {}
            for c in conflicts:
                by_reason.setdefault(c.get("reason", "?"), []).append([c.get("x"), c.get("y")])
            summary = {"tiles_affected": pv.get("tiles_affected"), "footprint_cells": pv.get("footprint_cells"),
                       "skipped_tiles": {r: {"count": len(t), "tiles": t[:20]} for r, t in by_reason.items()},
                       "fog_of_war_tiles": pv.get("fog_of_war_tiles"), "out_of_bounds": pv.get("clipped_out_of_bounds")}
            if prev.get("blocked") or "confirm_token" not in prev:
                return "blocked", {"why": prev.get("blocked"), **summary}
            if prev.get("would_be_noop") or not pv.get("tiles_affected"):
                return "blocked", {"why": ["nothing would change at this anchor (every tile was skipped)"], **summary}
            res = self.up.call("blueprint_apply", {**args, "confirm_token": prev["confirm_token"]})
            return ("applied" if res.get("applied") else "unknown"), {**summary, "result": res.get("readback") or res}
        return self._ledgered("designate", args, key, do)

    def build(self, csv: str, x: int, y: int, z: int, key: str | None = None) -> dict:
        """Place #build / #place / #zone / #dig blueprints through quickfort (dry-run first)."""
        first = csv.strip().splitlines()[0].strip().lower() if csv.strip() else ""
        if not first.startswith("#"):
            csv = "#build\n" + csv
        name = "bp_" + hashlib.sha1(csv.encode()).hexdigest()[:10] + ".csv"
        (config.BLUEPRINT_DIR / name).write_text(csv)
        def do():
            dry = dfhack.run("quickfort", "run", f"dfai/{name}", "-c", f"{x},{y},{z}", "--dry-run")
            if "error" in dry.lower() or "fail" in dry.lower():
                return "blocked", {"dry_run": dry}
            real = dfhack.run("quickfort", "run", f"dfai/{name}", "-c", f"{x},{y},{z}")
            return "applied", {"dry_run": _stats(dry), "result": _stats(real)}
        return self._ledgered("build", {"csv": csv, "x": x, "y": y, "z": z}, key, do)

    def order(self, amount: int, job: str | None = None, reaction: str | None = None,
              material_category: str | None = None, material: str | None = None,
              frequency: str = "OneTime", key: str | None = None) -> dict:
        """Queue a manager order through DFHack's `workorder` (supports reactions and material categories)."""
        if not job and not reaction:
            return {"error": "give job (a df.job_type name, e.g. ConstructBed) or reaction (e.g. BREW_DRINK_FROM_PLANT)"}
        params = {"job": job, "reaction": reaction, "amount": amount, "material_category": material_category,
                  "material": material, "frequency": frequency}
        spec = {"job": job or "CustomReaction", "amount_total": amount, "frequency": frequency}
        if reaction: spec["reaction"] = reaction
        if material_category: spec["material_category"] = [m.strip() for m in material_category.split(",")]
        if material: spec["material"] = material
        warning = None
        if job and job.startswith("Construct") and not (material_category or material):
            warning = ("no material given: the game may never start an 'unknown material' order. "
                       "Pass material_category='wood' (or bone, cloth, leather...) or material='INORGANIC' for stone.")
        def evidence():
            ident = dfhack.lua_json("state.lua", "identity")
            return {"orders_before": [o["id"] for o in dfhack.lua_json("state.lua")["orders"]],
                    "next_order_id": ident["next_order_id"]}
        want_cats = set(m.strip() for m in material_category.split(",")) if material_category else set()
        want_mat = None
        if material and material != "INORGANIC":
            want_mat = dfhack.lua_json("tools.lua", "resolve_material", material)
        def matches(o):
            """Return True / False, or None when the comparison is unsupported (caller treats as unknown)."""
            if o["job"] != (job or "CustomReaction") or o["total"] != amount or o.get("frequency") != frequency:
                return False
            if (o.get("reaction") or None) != (reaction or None):
                return False
            if set(o.get("material_category") or []) != want_cats:
                return False
            if material == "INORGANIC":
                return o.get("mat_type") == 0 and o.get("mat_index") == -1
            if material:
                if not want_mat or not want_mat.get("ok"):
                    return None
                return o.get("mat_type") == want_mat["mat_type"] and o.get("mat_index") == want_mat["mat_index"]
            return o.get("mat_type") == -1
        def reconcile(prior, fort):
            ev = prior.get("evidence") or {}
            nid = ev.get("next_order_id")
            dfhack.lua("print(1)")   # RPC is serialized by the game: once this returns, earlier commands have finished
            # requests that cannot be told apart from this one (same params, overlapping evidence window) -> ambiguous
            twins = [r for r in self.ledger.open_with_params(fort, "order", prior["params"]) if r["key"] != prior["key"]]
            claimed = self.ledger.claimed_order_ids(fort)
            cands, unsupported = [], False
            for o in dfhack.lua_json("state.lua")["orders"]:
                if nid is None or o["id"] < nid or o["id"] in claimed:
                    continue
                m = matches(o)
                if m is None:
                    unsupported = True
                elif m:
                    cands.append(o)
            now_nid = dfhack.lua_json("state.lua", "identity")["next_order_id"]
            if unsupported:
                return "unknown", {"evidence": "material comparison unsupported for this order; cannot attribute"}
            if twins and (cands or now_nid != nid):
                return "unknown", {"evidence": f"ambiguous: {len(twins)} other unresolved identical request(s) "
                                               f"({', '.join(t['key'] for t in twins)}) could account for these orders",
                                   "candidate_orders": cands}
            if len(cands) == 1:
                return "applied", {"created_orders": cands}
            if len(cands) > 1:
                return "unknown", {"evidence": "several matching orders; cannot tell which this request created",
                                   "candidate_orders": cands}
            if nid is not None and now_nid == nid:
                if config.TRUST_RPC_BARRIER:
                    return "proven_not_applied", {"evidence": "work-order id counter unchanged since the request"}
                return "unknown", {"evidence": "work-order id counter unchanged since the request, but automatic replay is "
                                               "disabled until DFHack RPC ordering is validated (DFAI_TRUST_RPC_BARRIER). "
                                               "Inspect the game; if you decide to order again, `settle` this receipt first."}
            return "unknown", {"evidence": f"order ids {nid}..{now_nid - 1} were used since the request but none matches "
                                           "an unclaimed current order; it may have been created and already completed or "
                                           "cancelled. Check stocks/observe before ordering again."}
        def do():
            before = {o["id"] for o in dfhack.lua_json("state.lua")["orders"]}
            try:
                out = dfhack.run("workorder", json.dumps(spec))
            except dfhack.DFHackError as e:
                out = f"error: {e}"
            after = [o for o in dfhack.lua_json("state.lua")["orders"] if o["id"] not in before and matches(o)]
            kick = dfhack.lua_json("state.lua", "kick_orders")
            res = {"output": out[-600:], "created_orders": after, "restarted_order_checks": kick.get("kicked")}
            if warning: res["warning"] = warning
            if after:
                return "applied", res
            return ("failed" if ("error" in out.lower() or "invalid" in out.lower() or "unknown" in out.lower()) else "unknown"), res
        return self._ledgered("order", params, key, do, evidence, reconcile)

    def cancel_order(self, order_id: int, key: str | None = None) -> dict:
        return self._ledgered("cancel_order", {"order_id": order_id}, key,
                              lambda: self._preview_apply("work_order_cancel", {"order_id": order_id}))

    def appoint(self, position: str, unit_id: int, replace: bool = False, key: str | None = None) -> dict:
        def do():
            res = dfhack.lua_json("positions.lua", "assign", position, str(unit_id), *(["replace"] if replace else []))
            if res.get("ok") and not res.get("unchanged"):
                res["restarted_order_checks"] = dfhack.lua_json("state.lua", "kick_orders").get("kicked")
            return ("applied" if res.get("ok") else "blocked"), res
        return self._ledgered("appoint", {"position": position, "unit_id": unit_id, "replace": replace}, key, do)

    def positions(self) -> dict:
        return dfhack.lua_json("positions.lua", "list")

    def labor(self, unit_id: int, detail: str, enabled: bool, key: str | None = None) -> dict:
        args = {"unit_id": unit_id, "detail": detail, "enabled": enabled}
        return self._ledgered("labor", args, key, lambda: self._preview_apply("assign_work_detail", args))

    def dfhack_command(self, command: str, key: str | None = None) -> dict:
        parts = shlex.split(command)
        if parts and parts[0] in ("enable", "disable") and len(parts) >= 2:
            bad = [x for x in parts[1:] if x not in DFHACK_ALLOWED]
            if bad:
                return {"error": f"cannot {parts[0]} {bad}", "allowed": sorted(DFHACK_ALLOWED)}
            return self._ledgered("dfhack", {"command": command}, key, lambda: ("applied", {"output": dfhack.run(*parts)[-4000:]}))
        if not parts or parts[0] not in DFHACK_ALLOWED:
            return {"error": f"command not allowed: {parts[0] if parts else ''}", "allowed": sorted(DFHACK_ALLOWED)}
        return self._ledgered("dfhack", {"command": command}, key, lambda: ("applied", {"output": dfhack.run(*parts)[-4000:]}))

    def remove_building(self, building_id: int, key: str | None = None) -> dict:
        return self._ledgered("remove_building", {"building_id": building_id}, key,
                              lambda: dfhack.lua_json("tools.lua", "remove_building", str(building_id)))

    def assign_owner(self, building_id: int, unit_id: int, key: str | None = None) -> dict:
        return self._ledgered("assign_owner", {"building_id": building_id, "unit_id": unit_id}, key,
                              lambda: dfhack.lua_json("tools.lua", "assign_owner", str(building_id), str(unit_id)))

    def find_items(self, query: str) -> dict:
        return dfhack.lua_json("tools.lua", "find_items", query)

    def job_types(self, filter: str = "") -> dict:
        return dfhack.lua_json("tools.lua", "job_types", filter)

    def set_labor(self, unit_id: int, labor: str, enabled: bool, key: str | None = None) -> dict:
        return self._ledgered("set_labor", {"unit_id": unit_id, "labor": labor, "enabled": enabled}, key,
                              lambda: dfhack.lua_json("tools.lua", "set_labor", str(unit_id), labor, "true" if enabled else "false"))

    def buildings(self, zones: bool = False) -> dict:
        return dfhack.lua_json("tools.lua", "buildings", "zones" if zones else "all")

    def checkpoint(self, label: str = "checkpoint", key: str | None = None) -> dict:
        # holds the same mutex as every mutation, so no server-made save can fall between an action and its marker
        return self._ledgered("checkpoint", {"label": label}, key, lambda: self._checkpoint(label))

    def _checkpoint(self, label: str) -> dict:
        before = {p.name: p.stat().st_mtime for p in config.SAVE_DIR.iterdir() if p.is_dir()}
        dfhack.run("quicksave")
        t0 = time.time()
        time.sleep(1.0)
        dfhack.lua("print(1)", timeout=120)               # RPC blocks while the game writes the save
        slot = None
        while time.time() - t0 < 120:
            dirs = {p.name: p.stat().st_mtime for p in config.SAVE_DIR.iterdir() if p.is_dir() and p.name.startswith("autosave")}
            changed = [n for n, m in dirs.items() if m > before.get(n, 0)]
            if changed:
                slot = max(changed, key=lambda n: dirs[n])
                newest = max((f.stat().st_mtime for f in (config.SAVE_DIR / slot).iterdir()), default=0)
                if time.time() - newest > 3:
                    break
            time.sleep(0.5)
        if not slot:
            return "unknown", {"ok": False, "error": "no autosave slot changed within 120s"}
        tick = dfhack.lua_json("state.lua")["tick"]
        dest = config.CHECKPOINT_DIR / f"{_slug(label)}_{tick}"
        shutil.copytree(config.SAVE_DIR / slot, dest, dirs_exist_ok=True)
        return {"ok": True, "slot": slot, "copied_to": str(dest), "seconds": round(time.time() - t0, 1)}

    def progress(self, limit: int = 30) -> dict:
        """Follow every order this server placed. States, by confidence:
        not_started / waiting / in_progress (read from the live order), recurring (live repeating order, current cycle),
        completed_announced (order gone AND a matching game 'has been completed' report after it was placed),
        completion_unconfirmed (order gone, not cancelled by this server, no matching report found), cancelled."""
        fort, _, _ = self._fort()
        current = {o["id"]: o for o in dfhack.lua_json("state.lua")["orders"]}
        quota = dfhack.lua_json("tools.lua", "quota_reports")["reports"]
        used_reports = set()
        cancelled = {}
        for r in self.ledger.db.execute("SELECT params, execution_status FROM actions WHERE fort=? AND kind='cancel_order'", (fort,)):
            if r[1] == "applied":
                cancelled[json.loads(r[0]).get("order_id")] = True
        out = []
        rows = self.ledger.db.execute("SELECT key, params, result, game_tick FROM actions WHERE fort=? AND kind='order' AND "
                                      "execution_status='applied' ORDER BY id ASC", (fort,)).fetchall()[-limit:]
        for key, params, result, tick in rows:
            res, prm = json.loads(result or "{}"), json.loads(params)
            for o in res.get("created_orders", []):
                cur = current.get(o["id"])
                if cur and (cur.get("frequency") or "OneTime") != "OneTime":
                    entry = {"state": "recurring", "frequency": cur.get("frequency"),
                             "this_cycle_done": cur["total"] - cur["left"], "total": cur["total"],
                             "cycles_announced": len([q for q in quota if q["abs_tick"] >= (tick or 0) and _report_matches(q["text"], prm)])}
                elif cur:
                    state = "in_progress" if cur["left"] < cur["total"] else ("waiting" if cur.get("active") else "not_started")
                    entry = {"state": state, "done": cur["total"] - cur["left"], "total": cur["total"], "active": cur.get("active")}
                elif o["id"] in cancelled:
                    entry = {"state": "cancelled"}
                else:
                    hit = next((q for q in quota if q["id"] not in used_reports and q["abs_tick"] >= (tick or 0)
                                and _report_matches(q["text"], prm)), None)
                    if hit:
                        used_reports.add(hit["id"])
                        entry = {"state": "completed_announced", "evidence": hit["text"], "match_basis": "report text and amount (heuristic)"}
                    else:
                        entry = {"state": "completion_unconfirmed",
                                 "evidence": "order no longer listed and not cancelled by this server; no matching completion "
                                             "report found (reports can be pruned, or a person may have removed it)"}
                out.append({"key": key, "order_id": o["id"], "what": prm.get("reaction") or prm.get("job"),
                            "amount": prm.get("amount"), "placed": _date(tick), "placed_abs_tick": tick, **entry})
        out.reverse()
        return {"orders": out}

    def death_history(self) -> dict:
        return dfhack.lua_json("tools.lua", "death_history")

    def moods(self) -> dict:
        return dfhack.lua_json("tools.lua", "moods")

    def farm_plots(self) -> dict:
        return dfhack.lua_json("tools.lua", "farm_plots")

    def set_crops(self, plot_id: int, season: str, plant: str, key: str | None = None) -> dict:
        return self._ledgered("set_crops", {"plot_id": plot_id, "season": season, "plant": plant}, key,
                              lambda: dfhack.lua_json("tools.lua", "set_crops", str(plot_id), season, plant))

    def settle(self, key: str, outcome: str, evidence: str, inspected: list | None = None) -> dict:
        """Record an adjudication of an unresolved receipt after inspecting the game.
        outcome: 'applied' (it happened, even if its result was later removed), 'not_applied' (you have evidence it
        never happened), or 'abandoned' (still uncertain; you accept duplicate risk for any new identical request).
        The current branch marker and game tick are recorded with your evidence."""
        if outcome not in ("applied", "not_applied", "abandoned"):
            return {"error": "outcome must be 'applied', 'not_applied' or 'abandoned'"}
        if not evidence or len(evidence.strip()) < 10:
            return {"error": "describe the evidence you inspected (what you checked and what you saw)"}
        with self._mutex:
            fort, tick, _ = self._fort()
            rec = self.ledger.get(fort, key)
            if not rec:
                return {"error": f"no receipt with key {key!r}"}
            if rec["execution_status"] not in ("requested", "unknown", "stale"):
                return {"error": f"receipt is already {rec['execution_status']}", "record": rec}
            ident = dfhack.lua_json("state.lua", "identity")
            status = {"applied": "applied", "not_applied": "failed", "abandoned": "abandoned"}[outcome]
            self.ledger.finish(fort, key, status, {
                "adjudication": {"outcome": outcome, "evidence": evidence, "inspected": inspected or [],
                                 "game_tick": tick, "branch": [ident.get("branch_token"), ident.get("branch_seq")]},
                "previous": rec["execution_status"], **(rec.get("result") or {})})
            out = {"status": "settled", "key": key, "outcome": outcome}
            if outcome == "abandoned":
                out["warning"] = "uncertainty was not resolved; a new identical request may duplicate the original"
            return out

    def action_log(self, limit: int = 20) -> list:
        fort, _, _ = self._fort()
        return self.ledger.recent(fort, limit)

    # ---------- helpers ----------
    def _preview_apply(self, tool: str, args: dict) -> dict:
        prev = self.up.call(tool, args)
        if prev.get("blocked") or "confirm_token" not in prev:
            return {"status": "blocked", "preview": prev}
        res = self.up.call(tool, {**args, "confirm_token": prev["confirm_token"]})
        return {"status": "applied" if res.get("applied") else "unknown", "preview": prev.get("preview"), "result": res}

    def _fort(self):
        ident = dfhack.lua_json("state.lua", "identity")
        fort = f"{ident['world']}#site{ident['site_id']}"
        stale = self.ledger.observe_tick(fort, ident["abs_tick"])
        token, seq = self.ledger.branch(fort)
        if token and (ident["branch_token"] != token or ident["branch_seq"] < seq):
            # the loaded game state was saved before some of our receipts (or is a different branch)
            stale += self.ledger.mark_after_seq_stale(fort, ident["branch_seq"] if ident["branch_token"] == token else 0)
            self.ledger.set_branch(fort, token, ident["branch_seq"] if ident["branch_token"] == token else 0)
        return fort, ident["abs_tick"], stale

    def _mark(self, fort, record_id):
        token, _ = self.ledger.branch(fort)
        token = token or uuid.uuid4().hex[:12]
        dfhack.lua_json("state.lua", "mark_branch", token, str(record_id))
        self.ledger.set_branch(fort, token, record_id)

    def _ledgered(self, kind, params, key, fn, evidence_fn=None, reconcile_fn=None):
        """Run a mutation under a durable receipt. `key` is the caller's request identity: omit it for a fresh
        request; reuse it to retry the SAME request. Unresolved attempts are reconciled against game evidence and
        replayed only when non-application is proven; otherwise they stay 'unknown'. Mutations are serialized."""
        with self._mutex:
            return self._ledgered_locked(kind, params, key, fn, evidence_fn, reconcile_fn)

    def _ledgered_locked(self, kind, params, key, fn, evidence_fn, reconcile_fn):
        fort, tick, stale = self._fort()
        canon = json.loads(json.dumps(params, sort_keys=True))
        key = key or f"{kind}:{uuid.uuid4().hex[:12]}"
        prior = self.ledger.get(fort, key)
        if prior:
            if prior["params"] != canon:
                return {"status": "key_conflict", "key": key, "error": "this key was already used for a different request",
                        "prior": prior}
            if prior["execution_status"] in ("applied", "blocked", "failed"):
                return {"status": "already_recorded", "key": key, "record": prior}
            if not reconcile_fn:
                return {"status": "unresolved", "key": key, "record": prior,
                        "note": "outcome unknown and this action kind cannot yet be reconciled automatically; "
                                "inspect the game (observe / buildings / positions) before deciding what to do"}
            verdict, info = reconcile_fn(prior, fort)
            if verdict == "applied":
                self.ledger.finish(fort, key, "applied", {"reconciled": True, **info})
                return {"status": "applied", "key": key, "reconciled_from": prior["execution_status"], **info}
            if verdict != "proven_not_applied":
                self.ledger.finish(fort, key, "unknown", {"reconciled": True, **info})
                return {"status": "unknown", "key": key, **info}
        else:
            # never start a new request that could not be told apart from an unresolved identical one
            twins = self.ledger.open_with_params(fort, kind, canon)
            if twins and reconcile_fn:
                return {"status": "blocked", "key": key,
                        "error": "an identical earlier request is still unresolved; retry it with its own key first",
                        "unresolved_keys": [t["key"] for t in twins]}
        evidence = evidence_fn() if evidence_fn else None
        rid = self.ledger.start(fort, key, kind, canon, tick, evidence)
        try:
            out = fn()
            status, result = out if isinstance(out, tuple) else (out.get("status") or ("applied" if out.get("ok", True) else "failed"), out)
        except Exception as e:  # leave a durable trace even on crashes
            status, result = "unknown", {"error": f"{type(e).__name__}: {e}"}
        if status in ("applied", "unknown"):
            # marker AFTER the mutation: a save taken in between can only make this receipt look stale, never falsely applied
            try:
                self._mark(fort, rid)
            except Exception as e:
                result = {**(result if isinstance(result, dict) else {"result": result}), "branch_marker_failed": str(e)}
        self.ledger.finish(fort, key, status, result)
        out = {"status": status, "key": key, **(result if isinstance(result, dict) else {"result": result})}
        if stale:
            out["note_reload_detected"] = f"{stale} receipts marked stale: the loaded game state predates them"
        return out

    def _ensure_blueprint_link(self):
        link = config.DF_DIR / "dfhack-config/blueprints/dfai"
        try:
            if not link.exists():
                link.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(config.BLUEPRINT_DIR, link)
        except OSError:
            pass

    def _load_cursor(self):
        try:
            return json.loads(self._cursor_file.read_text())["cursor"]
        except Exception:
            return None

    def _save_cursor(self, c):
        self._cursor_file.write_text(json.dumps({"cursor": c}))


_MONTHS = ["Granite", "Slate", "Felsite", "Hematite", "Malachite", "Galena", "Limestone", "Sandstone", "Timber",
           "Moonstone", "Opal", "Obsidian"]


def _date(abs_tick):
    if abs_tick is None:
        return None
    year, t = divmod(int(abs_tick), 403200)
    return f"{t % 33600 // 1200 + 1} {_MONTHS[t // 33600]}, year {year}"


_JOB_WORDS = {"ConstructThrone": ["chair", "throne"], "PrepareMeal": ["meal"], "MakeBarrel": ["barrel"]}


def _report_matches(text: str, params: dict) -> bool:
    """Heuristic: a QUOTA_FILLED report like 'Make wooden table (5) has been completed.' for this order."""
    import re
    t = text.lower()
    if f"({params.get('amount')})" not in t:
        return False
    if params.get("reaction"):
        return params["reaction"].split("_")[0].lower() in t
    job = params.get("job") or ""
    words = _JOB_WORDS.get(job) or [w.lower() for w in re.findall(r"[A-Z][a-z]+", job) if w not in ("Construct", "Make", "Prepare")]
    return any(w in t for w in words)


def _clean(s: str) -> str:
    import re
    return re.sub(r"\s+", " ", re.sub(r"\[[A-Z]:?[\d:]*\]", " ", s)).strip()


def _stats(out: str) -> str:
    return "\n".join(l for l in out.splitlines() if l.strip().startswith(("Buildings", "Zone", "Tiles", "Designat", "Stockpile", "Constructions", "Warning", "Error"))) or out[-500:]


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s)[:40] or "checkpoint"

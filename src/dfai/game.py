"""High-level game operations used by the MCP server (and usable directly from Python)."""
import hashlib
import json
import os
import shlex
import shutil
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
        self._ensure_blueprint_link()

    # ---------- observation ----------
    def state(self) -> dict:
        s = dfhack.lua_json("state.lua")
        out = {"date": s["date"], "tick": s["tick"], "paused": s["paused"], "screen": s["screen"], "popups": s["popups"]}
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
        out["new_events"] = self.events()["events"]
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
        return self._ledgered("designate", args, key, lambda: self._preview_apply("blueprint_apply", args))

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
                       "Pass material_category, e.g. 'wood' or 'stone'.")
        def do():
            before = {o["id"] for o in dfhack.lua_json("state.lua")["orders"]}
            try:
                out = dfhack.run("workorder", json.dumps(spec))
            except dfhack.DFHackError as e:
                out = f"error: {e}"
            after = [o for o in dfhack.lua_json("state.lua")["orders"] if o["id"] not in before]   # reconcile from the game
            kick = dfhack.lua_json("state.lua", "kick_orders")
            res = {"output": out[-600:], "created_orders": after, "restarted_order_checks": kick.get("kicked")}
            if warning: res["warning"] = warning
            if after:
                return "applied", res
            return ("failed" if ("error" in out.lower() or "invalid" in out.lower() or "unknown" in out.lower()) else "unknown"), res
        return self._ledgered("order", params, key, do)

    def cancel_order(self, order_id: int) -> dict:
        return self._preview_apply("work_order_cancel", {"order_id": order_id})

    def appoint(self, position: str, unit_id: int, replace: bool = False) -> dict:
        if replace:
            dfhack.lua_json("positions.lua", "vacate", position)
        res = dfhack.lua_json("positions.lua", "assign", position, str(unit_id))
        if res.get("ok"):
            res["restarted_order_checks"] = dfhack.lua_json("state.lua", "kick_orders").get("kicked")
        return res

    def labor(self, unit_id: int, detail: str, enabled: bool) -> dict:
        return self._preview_apply("assign_work_detail", {"unit_id": unit_id, "detail": detail, "enabled": enabled})

    def dfhack_command(self, command: str) -> dict:
        parts = shlex.split(command)
        if not parts or parts[0] not in DFHACK_ALLOWED:
            return {"error": f"command not allowed: {parts[0] if parts else ''}", "allowed": sorted(DFHACK_ALLOWED)}
        return {"output": dfhack.run(*parts)[-4000:]}

    def checkpoint(self, label: str = "checkpoint") -> dict:
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
            return {"ok": False, "error": "no autosave slot changed within 120s"}
        tick = dfhack.lua_json("state.lua")["tick"]
        dest = config.CHECKPOINT_DIR / f"{_slug(label)}_{tick}"
        shutil.copytree(config.SAVE_DIR / slot, dest, dirs_exist_ok=True)
        return {"ok": True, "slot": slot, "copied_to": str(dest), "seconds": round(time.time() - t0, 1)}

    def action_log(self, limit: int = 20) -> list:
        return self.ledger.recent(limit)

    # ---------- helpers ----------
    def _preview_apply(self, tool: str, args: dict) -> dict:
        prev = self.up.call(tool, args)
        if prev.get("blocked") or "confirm_token" not in prev:
            return {"status": "blocked", "preview": prev}
        res = self.up.call(tool, {**args, "confirm_token": prev["confirm_token"]})
        return {"status": "applied" if res.get("applied") else "unknown", "preview": prev.get("preview"), "result": res}

    def _ledgered(self, kind, params, key, fn):
        key = key or kind + ":" + hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]
        prior = self.ledger.get(key)
        if prior and prior["execution_status"] in ("applied", "requested", "unknown"):
            return {"status": "already_done", "note": "same idempotency key seen before; not repeated", "record": prior}
        if not prior:
            self.ledger.start(key, kind, params)
        try:
            out = fn()
            status, result = out if isinstance(out, tuple) else (out.get("status", "applied"), out)
        except Exception as e:  # leave a durable trace even on crashes
            status, result = "unknown", {"error": str(e)}
        self.ledger.finish(key, status, result)
        return {"status": status, "key": key, **(result if isinstance(result, dict) else {"result": result})}

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


def _clean(s: str) -> str:
    import re
    return re.sub(r"\s+", " ", re.sub(r"\[[A-Z]:?[\d:]*\]", " ", s)).strip()


def _stats(out: str) -> str:
    return "\n".join(l for l in out.splitlines() if l.strip().startswith(("Buildings", "Zone", "Tiles", "Designat", "Stockpile", "Constructions", "Warning", "Error"))) or out[-500:]


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s)[:40] or "checkpoint"

"""G0 bounded step driver.  python3 -I step.py <ticks> [--inject-pause-after SECONDS] [--wall-timeout S]"""
import argparse, json, os, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__)); LUA = os.path.join(HERE, "step.lua"); DF = os.path.join(HERE, "df.sh")
def lua(*a):
    out = subprocess.run([DF, "lua", "-f", LUA, *a], capture_output=True, text=True).stdout
    start = out.find("{"); return json.loads(out[start:]) if start >= 0 else {"raw": out}
ap = argparse.ArgumentParser(); ap.add_argument("ticks", type=int); ap.add_argument("--inject-pause-after", type=float)
ap.add_argument("--wall-timeout", type=float); a = ap.parse_args()
wall = a.wall_timeout or max(30.0, a.ticks / 100 * 3)   # ~100 ticks/s at the FPS cap, 3x margin
t0 = time.time(); began = lua("begin", str(a.ticks))
if not began.get("started"): print(json.dumps(began, indent=1)); raise SystemExit(1)
injected = False; st = None
while True:
    time.sleep(0.2); el = time.time() - t0
    if a.inject_pause_after and not injected and el >= a.inject_pause_after:
        subprocess.run([DF, "lua", "dfhack.world.SetPauseState(true)"], capture_output=True); injected = True
    st = lua("status")
    if st.get("now", {}).get("paused") and el > 0.5: break
    if el > wall: st["watchdog"] = "wall_timeout"; break
if st.get("timer_active"): st["cancel"] = lua("cancel").get("cancelled", False)
st["wall_s"] = round(time.time() - t0, 2); st["injected_external_pause"] = injected
st["ticks_per_wall_s"] = round(st["elapsed_ticks"] / st["wall_s"], 1) if st.get("elapsed_ticks") else None
st["overshoot_ticks"] = (st["elapsed_ticks"] - a.ticks) if st.get("timer_fired") else None
print(json.dumps(st, indent=1))

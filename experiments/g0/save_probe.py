"""Q-03 probe: trigger `quicksave` and watch the save folder until files stop changing.
Usage: python3 -I save_probe.py [settle_seconds]"""
import os, subprocess, sys, time, json
HOME = os.path.expanduser("~")
SAVE = os.path.join(HOME, "snap/steam/common/.local/share/Bay 12 Games/Dwarf Fortress/save")
DF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "df.sh")
settle = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
def snap():
    out = {}
    for root, _, files in os.walk(SAVE):
        for f in files:
            p = os.path.join(root, f); st = os.stat(p)
            out[os.path.relpath(p, SAVE)] = (st.st_mtime_ns, st.st_size)
    return out
before = snap(); t0 = time.time()
res = subprocess.run([DF, "quicksave"], capture_output=True, text=True).stdout.strip()
t_cmd = time.time() - t0
first_change = last_change = None; prev = before; changed = set()
while time.time() - t0 < 120:
    time.sleep(0.25); cur = snap(); now = time.time() - t0
    diff = {k for k in set(cur) | set(prev) if cur.get(k) != prev.get(k)}
    if diff:
        changed |= diff; last_change = now
        if first_change is None: first_change = now
    prev = cur
    if last_change is not None and now - last_change > settle: break
dirs = sorted({c.split(os.sep)[0] for c in changed})
print(json.dumps({"quicksave_output": res, "command_returned_s": round(t_cmd, 2),
    "first_change_s": first_change and round(first_change, 2), "last_change_s": last_change and round(last_change, 2),
    "files_changed": len(changed), "dirs_touched": dirs, "dirs_now": sorted(os.listdir(SAVE))}, indent=1))

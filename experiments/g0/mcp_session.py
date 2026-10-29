"""Drive one dfhack-mcp stdio session with a JSON script of calls.
Usage: python3 -I mcp_session.py <server.js> '<json list of [tool, args] or ["KILL_AFTER_SEND", tool, args]>'
Placeholder "$token" in args is replaced by the last confirm_token seen."""
import json, os, subprocess, sys, time
server, script = sys.argv[1], json.loads(sys.argv[2])
p = subprocess.Popen(["node", server], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=os.environ)
n = 0
def send(m): p.stdin.write(json.dumps(m) + "\n"); p.stdin.flush()
def rpc(method, params):
    global n; n += 1; send({"jsonrpc": "2.0", "id": n, "method": method, "params": params})
    while True:
        r = json.loads(p.stdout.readline())
        if r.get("id") == n: return r
rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "dfai-g0", "version": "0"}})
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
token = None
def sub(a): return {k: (token if v == "$token" else v) for k, v in a.items()}
for step in script:
    if step[0] == "KILL_AFTER_SEND":
        global_n = n + 1
        send({"jsonrpc": "2.0", "id": global_n, "method": "tools/call", "params": {"name": step[1], "arguments": sub(step[2])}})
        time.sleep(float(step[3]) if len(step) > 3 else 0.0); p.kill()
        print(f"=== {step[1]} sent, server killed after {step[3] if len(step)>3 else 0}s"); break
    r = rpc("tools/call", {"name": step[0], "arguments": sub(step[1])})
    res = r.get("result") or r.get("error"); text = "".join(c.get("text", "") for c in res.get("content", [])) if "content" in res else json.dumps(res)
    try:
        j = json.loads(text); token = j.get("confirm_token", token) if isinstance(j, dict) else token
    except Exception: pass
    print(f"=== {step[0]} {json.dumps(step[1])}{' (isError)' if res.get('isError') else ''}\n{text[:1500]}")
if p.poll() is None: p.terminate()

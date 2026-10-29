"""Thin bridge to the running game through `dfhack-run` (DFHack remote RPC on localhost:5000)."""
import json
import re
import subprocess
from . import config

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class DFHackError(RuntimeError):
    pass


def run(*args: str, timeout: float = 60) -> str:
    try:
        r = subprocess.run(["./dfhack-run", *args], cwd=config.DFHACK_DIR, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise DFHackError(f"dfhack-run timed out after {timeout}s: {args[:2]}") from e
    out = _ANSI.sub("", r.stdout + r.stderr).strip()
    if "Is DF running" in out or "Could not connect" in out or (r.returncode != 0 and not out):
        raise DFHackError(f"cannot reach DFHack: {out or r.returncode}")
    return out


def lua_json(script: str, *args: str, timeout: float = 60) -> dict:
    """Run one of our Lua modules and parse the JSON object it prints."""
    out = run("lua", "-f", str(config.LUA_DIR / script), *args, timeout=timeout)
    start = out.find("{")
    if start < 0:
        raise DFHackError(f"{script} returned no JSON: {out[:500]}")
    try:
        return json.loads(out[start:])
    except json.JSONDecodeError as e:
        raise DFHackError(f"{script} returned bad JSON: {out[:500]}") from e


def lua(code: str, timeout: float = 60) -> str:
    return run("lua", code, timeout=timeout)

"""Persistent stdio client for the pinned dfhack-mcp server (observations + its actuators)."""
import json
import os
import subprocess
import threading
from . import config

READ_TOOLS = {
    "fort_status", "stocks", "threats", "unmet_needs", "jobs_and_labor", "military", "injuries_and_health",
    "defenses", "burrows", "mechanisms", "moods", "mandates_and_justice", "rooms_and_zones", "trade",
    "environment", "find_unit", "citizen", "site_history", "artifacts_and_engravings", "chronicle",
    "map_overview", "tile_region", "geology", "game_data", "identify", "wiki_search", "wiki_lookup",
    "farming", "fluids", "fort_health", "hauling_routes", "livestock_and_pastures", "nobles_and_administrators",
    "petitions", "stockpiles", "work_details", "work_order_list",
}


class UpstreamError(RuntimeError):
    pass


class Upstream:
    def __init__(self):
        self._p = None
        self._id = 0
        self._lock = threading.Lock()

    def _start(self):
        env = dict(os.environ, DFHACK_MCP_ACTUATORS="1", DFHACK_MCP_QUERY_DIR=str(config.UPSTREAM_QUERY_DIR) + "/")
        self._p = subprocess.Popen([config.NODE, str(config.UPSTREAM_JS)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, text=True, env=env)
        self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": "dfai", "version": "0.1"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, msg):
        self._p.stdin.write(json.dumps(msg) + "\n")
        self._p.stdin.flush()

    def _rpc(self, method, params):
        self._id += 1
        my = self._id
        self._send({"jsonrpc": "2.0", "id": my, "method": method, "params": params})
        while True:
            line = self._p.stdout.readline()
            if not line:
                self._p = None
                raise UpstreamError("dfhack-mcp exited")
            msg = json.loads(line)
            if msg.get("id") == my:
                if "error" in msg:
                    raise UpstreamError(msg["error"].get("message", str(msg["error"])))
                return msg["result"]

    def call(self, tool: str, args: dict | None = None) -> dict:
        """Call a dfhack-mcp tool; returns parsed JSON (or {'text': ...}); raises UpstreamError on tool errors."""
        with self._lock:
            if self._p is None or self._p.poll() is not None:
                self._start()
            res = self._rpc("tools/call", {"name": tool, "arguments": {k: v for k, v in (args or {}).items() if v is not None}})
        text = "".join(c.get("text", "") for c in res.get("content", []))
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {"text": text}
        if res.get("isError"):
            raise UpstreamError(data.get("error", text) if isinstance(data, dict) else text)
        return data

    def close(self):
        if self._p and self._p.poll() is None:
            self._p.terminate()

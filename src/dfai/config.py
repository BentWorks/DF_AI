"""Paths and settings, all overridable with environment variables."""
import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
HOME = Path.home()
_STEAM = HOME / "snap/steam/common/.local/share/Steam/steamapps/common"

DFHACK_DIR = Path(os.environ.get("DFAI_DFHACK_DIR", _STEAM / "DFHack"))
DF_DIR = Path(os.environ.get("DFAI_DF_DIR", _STEAM / "Dwarf Fortress"))
SAVE_DIR = Path(os.environ.get("DFAI_SAVE_DIR", HOME / "snap/steam/common/.local/share/Bay 12 Games/Dwarf Fortress/save"))
LUA_DIR = Path(os.environ.get("DFAI_LUA_DIR", PROJECT / "src/dfai/lua"))       # must be readable by the game process
RUN_DIR = Path(os.environ.get("DFAI_RUN_DIR", PROJECT / "runs/play"))           # ledger, checkpoints, blueprints
BLUEPRINT_DIR = Path(os.environ.get("DFAI_BLUEPRINT_DIR", PROJECT / "runs/blueprints"))   # linked into DF as dfhack-config/blueprints/dfai
CHECKPOINT_DIR = RUN_DIR / "checkpoints"
UPSTREAM_JS = Path(os.environ.get("DFAI_UPSTREAM_JS", PROJECT / "vendor/dfhack-mcp/node_modules/dfhack-mcp/dist/index.js"))
UPSTREAM_QUERY_DIR = Path(os.environ.get("DFAI_UPSTREAM_QUERY_DIR", UPSTREAM_JS.parent / "dfhack-queries"))
NODE = os.environ.get("DFAI_NODE", "node")
TICKS_PER_SECOND_ESTIMATE = 100   # at the default 100 FPS cap

for d in (RUN_DIR, BLUEPRINT_DIR, CHECKPOINT_DIR):
    d.mkdir(parents=True, exist_ok=True)

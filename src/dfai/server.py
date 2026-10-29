"""DF_AI MCP server: lets any MCP-capable AI (Claude, Codex, Gemini, a custom harness) play Dwarf Fortress."""
import json
from mcp.server.mcpserver import MCPServer
from .game import Game

INSTRUCTIONS = """You are playing Dwarf Fortress (fortress mode) through DFHack. The game is PAUSED between your turns;
nothing happens until you call `advance`.

A good turn: `observe` -> decide -> act (dig, build, order, appoint, labor) -> `advance` some ticks -> repeat.
Time: 1 day = 1,200 ticks; 1 month = 33,600; 1 season = 100,800; 1 year = 403,200. About 100 ticks per real second.
Coordinates are x,y,z map tiles; use `sensor('map_overview')` and `sensor('tile_region', {...})` to see the map
('?' = unexplored, '#' = rock, '.' = floor). Blueprints use quickfort CSV syntax (https://docs.dfhack.org/en/stable/docs/guides/quickfort-user-guide.html):
  dig:   "#dig\\nd,d,d\\nd,d,d"   (d=dig, j/u/i=stairs down/up/up-down, h=channel)
  build: "#build\\nwc"            (wc carpenter, wm mason, ws still, wk kitchen, wf farmer, b bed, t table, c chair, d door)
  zones: "#zone\\nm(5x5)"         (m meeting hall, b bedroom, d dining, o office, h hospital, f fishing, w water source)
  stockpiles: "#place\\nf(4x4)"    (f food, w wood, s stone, u furniture, a animals, r refuse, b bar/block, c coins, g goods)
Production uses manager orders (`order`): built-in jobs by name (ConstructBed, ConstructTable, ConstructThrone = chair,
ConstructDoor, ConstructBin, ConstructBlocks, ...) with material_category 'wood' or 'stone' or reactions by name (BREW_DRINK_FROM_PLANT, BREW_DRINK_FROM_PLANT_GROWTH, ...).
Orders need a suitable workshop, materials, and dwarves whose work details allow the labor (`labor`).
Nobles matter: appoint a MANAGER (orders), BROKER (trade), BOOKKEEPER, CHIEF_MEDICAL_DWARF with `appoint`.
Every action is recorded; repeating an action with the same `key` will not duplicate it."""

mcp = MCPServer("dfai", instructions=INSTRUCTIONS)
_game: Game | None = None


def game() -> Game:
    global _game
    if _game is None:
        _game = Game()
    return _game


def _j(x) -> str:
    return json.dumps(x, ensure_ascii=False, indent=1)


@mcp.tool()
def observe() -> str:
    """Compact fortress overview: date, population, stocks (days of food/drink), alerts, idle dwarves, citizens and
    their current jobs, workshops, manager orders, noble positions, any popups, and new events since the last call."""
    return _j(game().state())


@mcp.tool()
def sensor(name: str, args: dict | None = None) -> str:
    """Detailed read-only reports. Names: fort_status, stocks, threats, unmet_needs, jobs_and_labor, military,
    injuries_and_health, defenses, burrows, moods, mandates_and_justice, rooms_and_zones, trade, environment,
    find_unit {query}, citizen {unit_id}, map_overview, tile_region {z,x0,y0,x1,y1}, geology, farming, stockpiles,
    work_details, work_order_list, nobles_and_administrators, livestock_and_pastures, fluids, chronicle, game_data
    {query}, identify {query}, wiki_search {query}, wiki_lookup {title}, and more."""
    return _j(game().sensor(name, args))


@mcp.tool()
def advance(ticks: int, max_wall_seconds: float | None = None) -> str:
    """Unpause and let the game run for `ticks` (1200 = one day), then pause. Stops early if the game pauses itself
    (e.g. a siege or caravan popup) and reports why. Closes open menus and dismisses popups first (their text is returned)."""
    return _j(game().advance(ticks, max_wall_seconds))


@mcp.tool()
def designate(csv: str, x: int, y: int, z: int, mode: str = "dig", key: str | None = None) -> str:
    """Designate digging or zones from a quickfort CSV (mode 'dig' or 'zone'); the CSV's top-left cell goes at x,y,z."""
    return _j(game().designate(csv, x, y, z, mode, key))


@mcp.tool()
def build(csv: str, x: int, y: int, z: int, key: str | None = None) -> str:
    """Place buildings, furniture, stockpiles or zones from a quickfort CSV ('#build', '#place', '#zone' or '#dig'
    modeline; defaults to #build). A multi-tile building's key cell is its CENTER (e.g. 'wc' at x,y fills x-1..x+1).
    Runs a dry run first and refuses if it reports errors."""
    return _j(game().build(csv, x, y, z, key))


@mcp.tool()
def order(amount: int, job: str | None = None, reaction: str | None = None, material_category: str | None = None,
          material: str | None = None, frequency: str = "OneTime", key: str | None = None) -> str:
    """Queue a manager work order: a built-in `job` (e.g. ConstructBed, ConstructTable, ConstructThrone = chair,
    ConstructDoor, ConstructBin, ConstructBlocks) or a `reaction` (e.g. BREW_DRINK_FROM_PLANT). For furniture give
    material_category ('wood', 'stone', 'metal', ...) or the game never starts it. frequency: OneTime, Daily,
    Monthly, Seasonally, Yearly. Verifies the order exists in-game and records it (same `key` = no duplicate)."""
    return _j(game().order(amount, job, reaction, material_category, material, frequency, key))


@mcp.tool()
def cancel_order(order_id: int) -> str:
    """Cancel a manager work order by id (see observe -> orders)."""
    return _j(game().cancel_order(order_id))


@mcp.tool()
def appoint(position: str, unit_id: int, replace: bool = False) -> str:
    """Appoint a citizen to a noble/administrator position (MANAGER, BROKER, BOOKKEEPER, CHIEF_MEDICAL_DWARF,
    MILITIA_COMMANDER, SHERIFF, ...). One dwarf may hold several. Set replace=true to replace the current holder."""
    return _j(game().appoint(position, unit_id, replace))


@mcp.tool()
def labor(unit_id: int, detail: str, enabled: bool = True) -> str:
    """Add (enabled=true) or remove a citizen from a work detail (e.g. 'Woodworkers', 'Miners', 'Stoneworkers',
    'Farmers', 'Haulers'). See sensor('work_details') for the fort's details and members."""
    return _j(game().labor(unit_id, detail, enabled))


@mcp.tool()
def dfhack(command: str) -> str:
    """Run an allowed DFHack automation command, e.g. 'seedwatch all 30', 'autofarm default 30',
    'enable autobutcher', 'orders import library/basic', 'prioritize -a', 'enable autochop'."""
    return _j(game().dfhack_command(command))


@mcp.tool()
def checkpoint(label: str = "checkpoint") -> str:
    """Save the game (quicksave) and copy the save to the controller's checkpoint store. Takes ~10 seconds."""
    return _j(game().checkpoint(label))


@mcp.tool()
def action_log(limit: int = 20) -> str:
    """Recent actions this controller took and their recorded outcomes."""
    return _j(game().action_log(limit))


def main():
    mcp.run("stdio")


if __name__ == "__main__":
    main()

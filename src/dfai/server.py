"""DF_AI MCP server: lets any MCP-capable AI (Claude, Codex, Gemini, a custom harness) play Dwarf Fortress."""
import json
from mcp.server.mcpserver import MCPServer
from .game import Game

INSTRUCTIONS = """You are playing Dwarf Fortress (fortress mode) through DFHack. The game is PAUSED between your turns;
nothing happens until you call `advance`.

A good turn: `observe` -> decide -> act (dig, build, order, appoint, labor) -> `advance` some ticks -> repeat.
Time: 1 day = 1,200 ticks; 1 month = 33,600; 1 season = 100,800; 1 year = 403,200. About 100 ticks per real second.
Coordinates are x,y,z map tiles; use `sensor('map_overview')` and `sensor('tile_region', {...})` to see the map
('?' = unexplored, '#' = rock, '.' = floor). Blueprints use quickfort CSV (https://docs.dfhack.org/en/stable/docs/guides/quickfort-user-guide.html).
Multi-tile buildings are placed CENTERED on their key cell.
  dig (`designate`, mode dig): d dig, h channel, u/j/i up/down/up-down stair, r ramp, t chop tree. e.g. "#dig\nd,d,d\nd,d,d"
  workshops (`build`): wc carpenter, wm mason, wl still, wz kitchen, ww farmer's, wh fishery, wu butcher, wn tanner,
    we leather works, wk clothier, wo loom, wr craftsdwarf, wq quern, wj jeweler, wt mechanic, wb bowyer, wd dyer,
    wy ashery, wp screw press, wf metalsmith's forge, ws siege workshop. Furnaces: ew wood furnace, es smelter,
    eg glass furnace, ek kiln. Trade depot: D.
  furniture (`build`): b bed, c chair, t table, d door, h chest, f cabinet, r weapon rack, n coffin, s statue, l well,
    v restraint, x floodgate.  Farm plot: p.
  zones (`build` with "#zone"): m meeting area, b bedroom, D dormitory, h dining hall, o office, B barracks,
    n pen/pasture, p pit/pond, w water source, f fishing, d garbage dump, T tomb, g gather fruit, a archery range,
    s sand, c clay, j dungeon, t animal training. (Hospitals/temples/taverns are locations attached to a meeting
    area in-game; not yet supported by these tools.)
  stockpiles (`build` with "#place"): f food, w wood, s stone, u furniture, r refuse, y corpses, a animals,
    b bars/blocks, e gems, g finished goods, h cloth, l leather, S sheets, n coins, p weapons, d armor, z ammo.
    Size with (WxH), e.g. "#place\nf(5x4)".
Production uses manager orders (`order`). Look up exact job names with `job_types` (furniture is Construct*:
ConstructBed, ConstructTable, ConstructThrone = chair, ConstructDoor, ConstructBin, ConstructBlocks; barrels are
MakeBarrel; many crafts are Make*). Reactions by name: BREW_DRINK_FROM_PLANT, BREW_DRINK_FROM_PLANT_GROWTH, ...
Give a material: material_category='wood' (also bone, cloth, leather, silk, yarn...) or material='INORGANIC' for stone.
Orders need a suitable workshop, materials, and dwarves allowed to do the labor (`labor` for work details,
`set_labor` for other labors). Use `find_items` to count tools and materials (e.g. 'pick', 'barrel', 'log').
Nobles matter: appoint MANAGER (orders), BROKER (trade), BOOKKEEPER, CHIEF_MEDICAL_DWARF with `appoint`.
Rooms: build a bed, make a bedroom zone around it, then `assign_owner(zone_id, unit_id)`; same for offices.
Every mutating tool returns a receipt (status + key) recorded in `action_log`. For anything you might need to retry,
CHOOSE a `key` yourself before calling (e.g. 'beds-1'), so you can retry after a lost response. Retrying with the
same key makes the server check the game first; it only repeats the action if it can prove it never happened, and
otherwise answers 'unknown' - then inspect the game before acting again.
A status of 'applied' means the game accepted the change, not that the work is finished: check `observe` later."""

mcp = MCPServer("dfai", instructions=INSTRUCTIONS)
_game: Game | None = None


def game() -> Game:
    global _game
    if _game is None:
        _game = Game()
    return _game


def _j(x) -> str:
    return json.dumps(x, ensure_ascii=False, indent=1)


def _safe(fn):
    """Return errors as JSON the model can read, instead of an opaque tool failure."""
    import functools
    @functools.wraps(fn)
    def wrapper(*a, **k):
        try:
            return fn(*a, **k)
        except Exception as e:
            return _j({"error": f"{type(e).__name__}: {e}"})
    return wrapper


@mcp.tool()
@_safe
def observe() -> str:
    """Compact fortress overview: date, population, stocks (days of food/drink), alerts, idle dwarves, citizens and
    their current jobs, workshops, manager orders, noble positions, any popups, and new events since the last call."""
    return _j(game().state())


@mcp.tool()
@_safe
def sensor(name: str, args: dict | None = None) -> str:
    """Detailed read-only reports. Names: fort_status, stocks, threats, unmet_needs, jobs_and_labor, military,
    injuries_and_health, defenses, burrows, moods, mandates_and_justice, rooms_and_zones, trade, environment,
    find_unit {query}, citizen {unit_id}, map_overview, tile_region {z,x0,y0,x1,y1}, geology, farming, stockpiles,
    work_details, work_order_list, nobles_and_administrators, livestock_and_pastures, fluids, chronicle, game_data
    {query}, identify {query}, wiki_search {query}, wiki_lookup {title}, and more."""
    return _j(game().sensor(name, args))


@mcp.tool()
@_safe
def advance(ticks: int, max_wall_seconds: float | None = None) -> str:
    """Unpause and let the game run for `ticks` (1200 = one day), then pause. Stops early if the game pauses itself
    (e.g. a siege or caravan popup) and reports why. Closes open menus and dismisses popups first (their text is returned)."""
    return _j(game().advance(ticks, max_wall_seconds))


@mcp.tool()
@_safe
def designate(csv: str, x: int, y: int, z: int, mode: str = "dig", key: str | None = None) -> str:
    """Designate digging or zones from a quickfort CSV (mode 'dig' or 'zone'); the CSV's top-left cell goes at x,y,z."""
    return _j(game().designate(csv, x, y, z, mode, key))


@mcp.tool()
@_safe
def build(csv: str, x: int, y: int, z: int, key: str | None = None) -> str:
    """Place buildings, furniture, stockpiles or zones from a quickfort CSV ('#build', '#place', '#zone' or '#dig'
    modeline; defaults to #build). A multi-tile building's key cell is its CENTER (e.g. 'wc' at x,y fills x-1..x+1).
    Runs a dry run first and refuses if it reports errors."""
    return _j(game().build(csv, x, y, z, key))


@mcp.tool()
@_safe
def order(amount: int, job: str | None = None, reaction: str | None = None, material_category: str | None = None,
          material: str | None = None, frequency: str = "OneTime", key: str | None = None) -> str:
    """Queue a manager work order: a built-in `job` (e.g. ConstructBed, ConstructTable, ConstructThrone = chair,
    ConstructDoor, ConstructBin, ConstructBlocks) or a `reaction` (e.g. BREW_DRINK_FROM_PLANT). For furniture give
    material_category ('wood', 'stone', 'metal', ...) or the game never starts it. frequency: OneTime, Daily,
    Monthly, Seasonally, Yearly. Verifies the order exists in-game and records it (same `key` = no duplicate)."""
    return _j(game().order(amount, job, reaction, material_category, material, frequency, key))


@mcp.tool()
@_safe
def cancel_order(order_id: int, key: str | None = None) -> str:
    """Cancel a manager work order by id (see observe -> orders)."""
    return _j(game().cancel_order(order_id, key))


@mcp.tool()
@_safe
def appoint(position: str, unit_id: int, replace: bool = False, key: str | None = None) -> str:
    """Appoint a living adult citizen to a noble/administrator position (MANAGER, BROKER, BOOKKEEPER,
    CHIEF_MEDICAL_DWARF, MILITIA_COMMANDER, SHERIFF, HAMMERER...). Follows the game's rules: elected and not-yet-
    available positions are refused (see `positions`). One dwarf may hold several. replace=true replaces the
    current holder only after the new candidate is validated; the old holder is kept if anything fails."""
    return _j(game().appoint(position, unit_id, replace, key))


@mcp.tool()
@_safe
def positions() -> str:
    """Noble/administrator positions: holders, vacancies, and whether each can be appointed now (and why not)."""
    return _j(game().positions())


@mcp.tool()
@_safe
def labor(unit_id: int, detail: str, enabled: bool = True, key: str | None = None) -> str:
    """Add (enabled=true) or remove a citizen from a work detail (e.g. 'Woodworkers', 'Miners', 'Stoneworkers',
    'Farmers', 'Haulers'). See sensor('work_details') for the fort's details and members."""
    return _j(game().labor(unit_id, detail, enabled, key))


@mcp.tool()
@_safe
def dfhack(command: str, key: str | None = None) -> str:
    """Run an allowed DFHack automation command, e.g. 'enable autochop', 'enable seedwatch', 'seedwatch all 30',
    'enable autofarm', 'autofarm default 30', 'enable autobutcher', 'orders import library/basic'."""
    return _j(game().dfhack_command(command, key))


@mcp.tool()
@_safe
def checkpoint(label: str = "checkpoint", key: str | None = None) -> str:
    """Save the game (quicksave) and copy the save to the controller's checkpoint store. Takes ~10 seconds."""
    return _j(game().checkpoint(label, key))


@mcp.tool()
@_safe
def action_log(limit: int = 20) -> str:
    """Recent actions this controller took and their recorded outcomes."""
    return _j(game().action_log(limit))


@mcp.tool()
@_safe
def remove_building(building_id: int, key: str | None = None) -> str:
    """Mark a building (workshop, furniture) for deconstruction, or remove a zone/stockpile. Ids from `buildings`."""
    return _j(game().remove_building(building_id, key))


@mcp.tool()
@_safe
def buildings(zones: bool = False) -> str:
    """List buildings (zones=false) or zones (zones=true) with ids, kinds, extents, built state and owners."""
    return _j(game().buildings(zones))


@mcp.tool()
@_safe
def assign_owner(building_id: int, unit_id: int, key: str | None = None) -> str:
    """Assign a bedroom/office/tomb zone (or a bed) to a citizen; unit_id -1 clears the owner."""
    return _j(game().assign_owner(building_id, unit_id, key))


@mcp.tool()
@_safe
def find_items(query: str) -> str:
    """Count items whose name or type matches `query` (e.g. 'pick', 'axe', 'barrel', 'log', 'seed', 'bed')."""
    return _j(game().find_items(query))


@mcp.tool()
@_safe
def job_types(filter: str = "") -> str:
    """List valid job type names for `order`, optionally filtered by substring (e.g. 'Construct', 'barrel')."""
    return _j(game().job_types(filter))


@mcp.tool()
@_safe
def set_labor(unit_id: int, labor: str, enabled: bool = True, key: str | None = None) -> str:
    """Enable/disable one labor for one dwarf (e.g. MINE, CARPENTER, MASON, BREWER, COOK, PLANT, CUTWOOD).
    Labors that belong to a work detail are governed by the detail; use `labor` for those."""
    return _j(game().set_labor(unit_id, labor, enabled, key))


def main():
    mcp.run("stdio")


if __name__ == "__main__":
    main()

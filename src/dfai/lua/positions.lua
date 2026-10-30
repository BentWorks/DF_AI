-- DF_AI: fort positions (nobles/administrators).  Usage:
--   lua -f positions.lua list
--   lua -f positions.lua assign <POSITION_CODE> <unit_id> [replace]
--   lua -f positions.lua vacate <POSITION_CODE>
-- Assignment follows the game's own rules: not ELECTED, ACTIVE (population/market requirements met),
-- not military-screen-only, and appointable by a position that currently has a holder. Candidates must be
-- living adult citizens. With `replace`, the new candidate is fully validated before the old holder is removed,
-- and the old holder is restored if the write cannot be verified.
local json = require('json')
local args = {...}
local entity = df.historical_entity.find(df.global.plotinfo.group_id)
local function pos_by_code(code) for _, p in ipairs(entity.positions.own) do if p.code == code then return p end end end
local function pos_by_id(id) for _, p in ipairs(entity.positions.own) do if p.id == id then return p end end end
local function slots(p) local o = {} for _, a in ipairs(entity.positions.assignments) do if a.position_id == p.id then table.insert(o, a) end end return o end
local function holders(p) local o = {} for _, a in ipairs(slots(p)) do if a.histfig ~= -1 then table.insert(o, a) end end return o end
local function unit_for_hf(hfid) for _, u in ipairs(dfhack.units.getCitizens()) do if u.hist_figure_id == hfid then return u end end end
local function uname(u) return u and dfhack.df2utf(dfhack.units.getReadableName(u)) or nil end

local function assignable(p)
  if p.flags.ELECTED then return false, 'elected position (chosen by the dwarves, not appointed)' end
  if p.flags.MILITARY_SCREEN_ONLY then return false, 'assigned through squads/military screen' end
  if not p.flags.ACTIVE then return false, 'not yet available (population or other requirement not met)' end
  if #p.appointed_by == 0 then return false, 'not appointable by the player' end
  for _, by in ipairs(p.appointed_by) do
    local ap = pos_by_id(by)
    if ap and #holders(ap) > 0 then return true, 'appointable by ' .. ap.code end
  end
  return false, 'no current holder of an appointing position'
end

local function unlink(hf, slot)
  for i = #hf.entity_links - 1, 0, -1 do
    local l = hf.entity_links[i]
    if df.histfig_entity_link_positionst:is_instance(l) and l.entity_id == entity.id and l.assignment_id == slot.id then hf.entity_links:erase(i); l:delete() end
  end
end
local function link(hf, slot)
  slot.histfig = hf.id; slot.histfig2 = hf.id
  local l = df.histfig_entity_link_positionst:new()
  l.entity_id = entity.id; l.link_strength = 100; l.assignment_id = slot.id; l.start_year = df.global.cur_year
  hf.entity_links:insert('#', l)
end
local function vacate(slot)
  local hf = df.historical_figure.find(slot.histfig)
  if hf then unlink(hf, slot) end
  slot.histfig = -1; slot.histfig2 = -1
end
local function holds(u, code)
  for _, n in ipairs(dfhack.units.getNoblePositions(u) or {}) do if n.position.code == code then return true end end
  return false
end

local cmd = args[1]
local res
if cmd == 'list' then
  local out = {}
  for _, p in ipairs(entity.positions.own) do
    local hs = {}
    for _, a in ipairs(holders(p)) do local u = unit_for_hf(a.histfig); table.insert(hs, {unit_id = u and u.id or nil, name = uname(u)}) end
    local ok, why = assignable(p)
    table.insert(out, {code = p.code, name = dfhack.df2utf(p.name[0] or p.code), holders = hs, vacant = #hs == 0,
      slots = #slots(p), assignable = ok, why = why})
  end
  res = {positions = out}
elseif cmd == 'vacate' then
  local p = pos_by_code(args[2] or '')
  if not p then res = {ok = false, error = 'unknown position code: ' .. tostring(args[2])}
  else
    local hs = holders(p)
    if #hs == 0 then res = {ok = false, error = p.code .. ' is already vacant'}
    else local prev = uname(unit_for_hf(hs[1].histfig)); vacate(hs[1]); res = {ok = true, vacated = p.code, previous_holder = prev} end
  end
elseif cmd == 'assign' then
  local p = pos_by_code(args[2] or '')
  local u = df.unit.find(tonumber(args[3] or '') or -1)
  local replace = args[4] == 'replace'
  local ok, why = false, nil
  if not p then res = {ok = false, error = 'unknown position code: ' .. tostring(args[2])}
  else ok, why = assignable(p) end
  if p and not ok then res = {ok = false, position = p.code, error = 'not assignable: ' .. why}
  elseif p and (not u or not dfhack.units.isCitizen(u) or not dfhack.units.isAlive(u)) then res = {ok = false, error = 'candidate is not a living citizen: ' .. tostring(args[3])}
  elseif p and not dfhack.units.isAdult(u) then res = {ok = false, error = 'candidate is not an adult'}
  elseif p and holds(u, p.code) then res = {ok = true, unchanged = true, position = p.code, holder = uname(u)}
  elseif p then
    local hf = df.historical_figure.find(u.hist_figure_id)
    local slot, prev_slot, prev_hf
    for _, a in ipairs(slots(p)) do if a.histfig == -1 then slot = a; break end end
    if not slot and replace then prev_slot = holders(p)[1]; prev_hf = prev_slot and df.historical_figure.find(prev_slot.histfig) end
    if not slot and not prev_slot then res = {ok = false, error = p.code .. ' has no vacant slot (pass replace=true to replace the holder)'}
    elseif not hf then res = {ok = false, error = 'candidate has no historical figure record'}
    else
      local target = slot or prev_slot
      local prev_name = prev_hf and uname(unit_for_hf(prev_hf.id))
      if prev_slot then vacate(prev_slot) end
      link(hf, target)
      if holds(u, p.code) then
        res = {ok = true, position = p.code, holder = uname(u), unit_id = u.id, replaced = prev_name}
      else  -- roll back to the previous state
        unlink(hf, target); target.histfig = -1; target.histfig2 = -1
        if prev_hf then link(prev_hf, target) end
        res = {ok = false, error = 'assignment could not be verified; previous state restored', restored = prev_name}
      end
    end
  end
else res = {ok = false, error = 'usage: list | assign <CODE> <unit_id> [replace] | vacate <CODE>'} end
print(json.encode(res))

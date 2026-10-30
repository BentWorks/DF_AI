-- DF_AI extra game actions/queries.  Usage: lua -f tools.lua <cmd> [args...]
--   remove_building <id> | assign_owner <building_id> <unit_id|-1> | find_items <query> | job_types [filter]
--   set_labor <unit_id> <LABOR> <true|false> | buildings [zones]
local json = require('json')
local args = {...}
local cmd = args[1]
local res
local function bname(b)
  local t = df.building_type[b:getType()]
  local ok, sub = pcall(function()
    if b:getType() == df.building_type.Workshop then return df.workshop_type[b:getSubtype()] end
    if b:getType() == df.building_type.Furnace then return df.furnace_type[b:getSubtype()] end
    if b:getType() == df.building_type.Civzone then return df.civzone_type[b.type] end
  end)
  return (ok and sub) and (t .. ':' .. sub) or t
end
if cmd == 'remove_building' then
  local b = df.building.find(tonumber(args[2] or ''))
  if not b then res = {ok = false, error = 'no building with id ' .. tostring(args[2])}
  else
    local name = bname(b)
    local ok, err = pcall(function() dfhack.buildings.deconstruct(b) end)
    res = {ok = ok, building = name, note = ok and 'marked for removal (a dwarf will deconstruct it; zones/stockpiles vanish at once)' or tostring(err)}
  end
elseif cmd == 'assign_owner' then
  local b = df.building.find(tonumber(args[2] or ''))
  local uid = tonumber(args[3] or '')
  local u = (uid and uid >= 0) and df.unit.find(uid) or nil
  if not b then res = {ok = false, error = 'no building/zone with id ' .. tostring(args[2])}
  elseif uid and uid >= 0 and not u then res = {ok = false, error = 'no unit ' .. tostring(args[3])}
  else
    local ok = dfhack.buildings.setOwner(b, u)
    res = {ok = ok and true or false, building = bname(b), owner = u and dfhack.df2utf(dfhack.units.getReadableName(u)) or 'none'}
  end
elseif cmd == 'find_items' then
  local q = (args[2] or ''):lower()
  local counts, total = {}, 0
  for _, it in ipairs(df.global.world.items.other.IN_PLAY) do
    local desc = dfhack.df2utf(dfhack.items.getDescription(it, 0, true)):lower()
    local ty = df.item_type[it:getType()]:lower()
    if q == '' or desc:find(q, 1, true) or ty:find(q, 1, true) then
      local key = dfhack.df2utf(dfhack.items.getDescription(it, 0, true))
      local c = counts[key] or {count = 0, in_use = 0, forbidden = 0}
      c.count = c.count + (it.stack_size or 1)
      if it.flags.in_job or it.flags.in_inventory then c.in_use = c.in_use + 1 end
      if it.flags.forbid then c.forbidden = c.forbidden + 1 end
      counts[key] = c; total = total + 1
    end
  end
  local list = {}
  for k, v in pairs(counts) do table.insert(list, {item = k, count = v.count, carried_or_in_job = v.in_use, forbidden = v.forbidden}) end
  table.sort(list, function(a, b) return a.count > b.count end)
  while #list > 40 do table.remove(list) end
  res = {query = q, distinct = #list, matches = list}
elseif cmd == 'resolve_material' then
  local mi = dfhack.matinfo.find(args[2] or '')
  res = mi and {ok = true, mat_type = mi.type, mat_index = mi.index, token = mi:getToken()} or {ok = false, error = 'unknown material ' .. tostring(args[2])}
elseif cmd == 'job_types' then
  local f = (args[2] or ''):lower()
  local out = {}
  for i = df.job_type._first_item, df.job_type._last_item do
    local n = df.job_type[i]
    if n and (f == '' or n:lower():find(f, 1, true)) then table.insert(out, n) end
  end
  res = {job_types = out}
elseif cmd == 'set_labor' then
  local u = df.unit.find(tonumber(args[2] or ''))
  local lab = df.unit_labor[args[3] or '']
  if not u then res = {ok = false, error = 'no unit ' .. tostring(args[2])}
  elseif not lab then res = {ok = false, error = 'unknown labor ' .. tostring(args[3])}
  else
    local on = (args[4] ~= 'false')
    u.status.labors[lab] = on
    res = {ok = true, unit = dfhack.df2utf(dfhack.units.getReadableName(u)), labor = args[3], enabled = on,
      note = 'labors covered by a work detail are controlled by that detail; use labor() for those'}
  end
elseif cmd == 'buildings' then
  local zones = args[2] == 'zones'
  local out = {}
  for _, b in ipairs(df.global.world.buildings.all) do
    local isz = b:getType() == df.building_type.Civzone
    if zones == isz then
      local owner
      pcall(function() local o = dfhack.buildings.getOwner(b); owner = o and dfhack.df2utf(dfhack.units.getReadableName(o)) end)
      table.insert(out, {id = b.id, kind = bname(b), x1 = b.x1, y1 = b.y1, x2 = b.x2, y2 = b.y2, z = b.z,
        built = (not isz) and (b:getBuildStage() >= b:getMaxBuildStage()) or nil, owner = owner})
    end
  end
  res = {buildings = out}
else
  res = {ok = false, error = 'unknown command'}
end
print(json.encode(res))

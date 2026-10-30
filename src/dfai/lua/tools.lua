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
elseif cmd == 'farm_plots' or cmd == 'set_crops' then
  local SEASONS = {'spring', 'summer', 'autumn', 'winter'}
  local SFLAG = {spring = 'SPRING', summer = 'SUMMER', autumn = 'AUTUMN', winter = 'WINTER'}
  local function seeds_by_plant()
    local c = {}
    for _, it in ipairs(df.global.world.items.other.SEEDS) do
      if not it.flags.forbid and not it.flags.rotten then
        local mi = dfhack.matinfo.decode(it)
        if mi and mi.plant then c[mi.plant.id] = (c[mi.plant.id] or 0) + it.stack_size end
      end
    end
    return c
  end
  local function underground(b) return dfhack.maps.getTileFlags(b.x1, b.y1, b.z).subterranean end
  local function grows_here(pl, under)
    local sub = pl.flags.BIOME_SUBTERRANEAN_WATER or pl.flags.BIOME_SUBTERRANEAN_CHASM or pl.flags.BIOME_SUBTERRANEAN_LAVA
    if under then return sub and true or false end
    for k, v in pairs(pl.flags) do if v == true and tostring(k):find('^BIOME_') and not tostring(k):find('SUBTERRANEAN') then return true end end
    return false
  end
  local seeds = seeds_by_plant()
  if cmd == 'farm_plots' then
    local out = {}
    for _, b in ipairs(df.global.world.buildings.other.FARM_PLOT) do
      local crops = {}
      for i = 0, 3 do local id = b.plant_id[i]; crops[SEASONS[i + 1]] = id >= 0 and df.global.world.raws.plants.all[id].id or 'fallow' end
      table.insert(out, {id = b.id, x1 = b.x1, y1 = b.y1, x2 = b.x2, y2 = b.y2, z = b.z, underground = underground(b),
        built = b:getBuildStage() >= b:getMaxBuildStage(), crops = crops})
    end
    local plantable = {}
    for _, pl in ipairs(df.global.world.raws.plants.all) do
      if pl.flags.SEED and (seeds[pl.id] or 0) > 0 then
        local ss = {}
        for _, s in ipairs(SEASONS) do if pl.flags[SFLAG[s]] then table.insert(ss, s) end end
        table.insert(plantable, {plant = pl.id, name = pl.name, seeds = seeds[pl.id], seasons = ss,
          underground = grows_here(pl, true), surface = grows_here(pl, false), brewable = pl.flags.DRINK or false})
      end
    end
    res = {season_now = SEASONS[df.global.cur_season + 1], plots = out, plants_with_seeds = plantable}
  else
    local b = df.building.find(tonumber(args[2] or ''))
    local season, token = (args[3] or ''):lower(), args[4] or ''
    local pl
    for _, p in ipairs(df.global.world.raws.plants.all) do if p.id == token then pl = p end end
    if not b or b:getType() ~= df.building_type.FarmPlot then res = {ok = false, error = 'no farm plot with id ' .. tostring(args[2])}
    elseif token ~= 'fallow' and not pl then res = {ok = false, error = 'unknown plant ' .. token}
    elseif token ~= 'fallow' and not pl.flags.SEED then res = {ok = false, error = token .. ' cannot be farmed (no seeds)'}
    elseif token ~= 'fallow' and not grows_here(pl, underground(b)) then
      res = {ok = false, error = token .. ' does not grow ' .. (underground(b) and 'underground' or 'on the surface')}
    else
      local targets = (season == 'all') and SEASONS or {season}
      local set, skipped = {}, {}
      for _, s in ipairs(targets) do
        local idx
        for i, n in ipairs(SEASONS) do if n == s then idx = i - 1 end end
        if idx == nil then skipped[#skipped + 1] = s .. ' (not a season)'
        elseif token ~= 'fallow' and not pl.flags[SFLAG[s]] then skipped[#skipped + 1] = s .. ' (does not grow then)'
        else b.plant_id[idx] = (token == 'fallow') and -1 or pl.index; set[#set + 1] = s end
      end
      res = {ok = #set > 0, plot = b.id, plant = token, seasons_set = set, skipped = skipped, seeds_available = pl and (seeds[pl.id] or 0) or nil,
        note = (pl and (seeds[pl.id] or 0) == 0) and 'no seeds in stock: nothing will be planted until seeds arrive' or nil}
    end
  end
elseif cmd == 'moods' then
  local out = {}
  for _, u in ipairs(dfhack.units.getCitizens()) do
    if u.mood ~= -1 then
      local j = u.job.current_job
      local demands, ws = {}, nil
      if j then
        local jitems = j.job_items
        local okel, el = pcall(function() return jitems.elements end)   -- DFHack 53.x wraps the vector in a struct
        if okel and el then jitems = el end
        for _, ji in ipairs(jitems) do
          local flags = {}
          for _, fs in ipairs({ji.flags1, ji.flags2, ji.flags3}) do
            for k, v in pairs(fs) do if v == true then table.insert(flags, tostring(k)) end end
          end
          local mat = (ji.mat_type ~= -1) and dfhack.matinfo.decode(ji.mat_type, ji.mat_index) or nil
          table.insert(demands, {item_type = ji.item_type ~= -1 and df.item_type[ji.item_type] or 'any',
            material = mat and mat:getToken() or nil, quantity = ji.quantity, material_flags = flags,
            reaction_class = (ji.reaction_class ~= '' and ji.reaction_class or nil)})
        end
        local b = dfhack.job.getHolder(j)
        if b then ws = {id = b.id, kind = df.building_type[b:getType()]} end
      end
      table.insert(out, {unit_id = u.id, name = dfhack.df2utf(dfhack.units.getReadableName(u)),
        mood = df.mood_type[u.mood], job = j and df.job_type[j.job_type] or nil, workshop = ws,
        items_collected = j and #j.items or 0, demands = demands,
        note = 'gather these materials into stockpiles the dwarf can reach; an unmet mood can end in madness or death'})
    end
  end
  res = {moods = out}
elseif cmd == 'death_history' then
  -- Source: world history HIST_FIGURE_DIED events (persistent; every citizen is a historical figure).
  local site, gid = df.global.plotinfo.site_id, df.global.plotinfo.group_id
  local founded_year, founded_tick
  for _, e in ipairs(df.global.world.history.events) do
    if df.history_event_created_sitest:is_instance(e) and e.site == site then founded_year, founded_tick = e.year, e.seconds end
  end
  local deaths, by_cause = {}, {}
  local ev = df.global.world.history.events
  for i = #ev - 1, 0, -1 do
    local e = ev[i]
    if founded_year and e.year < founded_year then break end
    if df.history_event_hist_figure_diedst:is_instance(e) and (not founded_year or e.year > founded_year or e.seconds >= (founded_tick or 0)) then
      local hf = df.historical_figure.find(e.victim_hf)
      local member = false
      if hf then for _, l in ipairs(hf.entity_links) do if l.entity_id == gid then member = true end end end
      if member or e.site == site then
        local cause = df.death_type[e.death_cause] or tostring(e.death_cause)
        by_cause[cause] = (by_cause[cause] or 0) + 1
        table.insert(deaths, {name = hf and dfhack.df2utf(dfhack.translation.translateName(hf.name, false)) or '?', member = member,
          at_this_site = e.site == site, cause = cause, year = e.year, tick = e.seconds})
      end
    end
  end
  res = {source = 'world history HIST_FIGURE_DIED events', coverage_from = founded_year and {year = founded_year, tick = founded_tick} or 'unknown (no site-founding event found)',
    deaths = deaths, by_cause = by_cause,
    starvation_or_dehydration = (by_cause.HUNGER or 0) + (by_cause.THIRST or 0),
    gaps = 'non-historical units are not covered; members are dwarves ever linked to this fort government'}
elseif cmd == 'quota_reports' then
  local out = {}
  for _, r in ipairs(df.global.world.status.reports) do
    if r.type == df.announcement_type.QUOTA_FILLED then
      table.insert(out, {id = r.id, abs_tick = r.year * 403200 + r.time, text = dfhack.df2utf(r.text)})
    end
  end
  res = {reports = out, note = 'from the rolling report window; old reports can be pruned'}
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

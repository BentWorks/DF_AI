-- DF_AI compact state that dfhack-mcp does not provide.  Usage: lua -f state.lua [popups|dismiss_popups|kick_orders]
local json = require('json')
local args = {...}
local cmd = args[1] or 'state'
local function clean(s) return (dfhack.df2utf(s or ''):gsub('%[[A-Z]:?[%d:]*%]', ' '):gsub('%s+', ' ')) end
local function popups()
  local out = {}
  for _, p in ipairs(df.global.world.status.popups) do table.insert(out, clean(p.text):sub(1, 400)) end
  return out
end
if cmd == 'popups' then print(json.encode({popups = popups()})) return end
if cmd == 'dismiss_popups' then
  local texts = popups()
  local v = df.global.world.status.popups
  while #v > 0 do local p = v[0]; v:erase(0); p:delete() end
  print(json.encode({dismissed = texts})) return
end
if cmd == 'identity' then
  local wd = df.global.world.world_data
  local wname = wd and dfhack.df2utf(dfhack.translation.translateName(wd.name, true)) or '?'
  local mark = dfhack.persistent.getSiteData('dfai_branch', {})
  print(json.encode({world = wname, site_id = df.global.plotinfo.site_id, civ_id = df.global.plotinfo.civ_id,
    abs_tick = df.global.cur_year * 403200 + df.global.cur_year_tick,
    next_order_id = df.global.world.manager_orders.manager_order_next_id,
    branch_token = mark.token or '', branch_seq = mark.seq or 0}))
  return
end
if cmd == 'mark_branch' then
  -- stored in the save itself, so a reloaded save carries the marker from its own point in history
  dfhack.persistent.saveSiteData('dfai_branch', {token = args[2], seq = tonumber(args[3])})
  print(json.encode({ok = true})) return
end
if cmd == 'kick_orders' then
  local before = df.global.plotinfo.manager_timer
  if before == 0 then df.global.plotinfo.manager_timer = 1 end
  print(json.encode({timer_before = before, kicked = before == 0})) return
end
-- default: compact state
local months = {'Granite','Slate','Felsite','Hematite','Malachite','Galena','Limestone','Sandstone','Timber','Moonstone','Opal','Obsidian'}
local t = df.global.cur_year_tick
local month = math.floor(t / 33600)
local day = math.floor((t % 33600) / 1200) + 1
local citizens = {}
for _, u in ipairs(dfhack.units.getCitizens()) do
  local j = u.job.current_job
  table.insert(citizens, {id = u.id, name = clean(dfhack.units.getReadableName(u)), profession = dfhack.units.getProfessionName(u),
    job = j and df.job_type[j.job_type] or 'idle', x = u.pos.x, y = u.pos.y, z = u.pos.z})
end
local workshops = {}
for _, b in ipairs(df.global.world.buildings.all) do
  local bt = b:getType()
  if bt == df.building_type.Workshop or bt == df.building_type.Furnace then
    local sub = (bt == df.building_type.Workshop) and df.workshop_type[b:getSubtype()] or df.furnace_type[b:getSubtype()]
    local jobs = {}
    for _, j in ipairs(b.jobs) do table.insert(jobs, df.job_type[j.job_type]) end
    table.insert(workshops, {id = b.id, kind = sub, x = b.centerx, y = b.centery, z = b.z,
      built = b:getBuildStage() >= b:getMaxBuildStage(), jobs = jobs})
  end
end
local orders = {}
for _, o in ipairs(df.global.world.manager_orders.all) do
  local cats = {}
  for k, v in pairs(o.material_category) do if v == true then table.insert(cats, k) end end
  table.insert(orders, {id = o.id, job = df.job_type[o.job_type], reaction = (o.reaction_name ~= '' and o.reaction_name or nil),
    total = o.amount_total, left = o.amount_left, validated = o.status.validated, active = o.status.active,
    frequency = df.workquota_frequency_type[o.frequency], mat_type = o.mat_type, mat_index = o.mat_index,
    material_category = cats})
end
local deaths = {}
for _, u in ipairs(df.global.world.units.all) do
  local member = false
  if dfhack.units.isDead(u) and dfhack.units.isOwnCiv(u) then
    local hf = df.historical_figure.find(u.hist_figure_id)
    if hf then for _, l in ipairs(hf.entity_links) do if l.entity_id == df.global.plotinfo.group_id then member = true end end end
  end
  if member then
    local cause, when = nil, nil
    pcall(function()
      local inc = df.incident.find(u.counters.death_id)
      if inc then cause = df.death_type[inc.death_cause]; when = string.format('year %d tick %d', inc.event_year, inc.event_time) end
    end)
    table.insert(deaths, {unit_id = u.id, name = clean(dfhack.units.getReadableName(u)), cause = cause, when = when})
  end
end
local function empty(it) return not it.flags.in_job and not it.flags.forbid and not it.flags.rotten and #dfhack.items.getContainedItems(it) == 0 end
local containers = {barrels = 0, large_pots = 0, bins = 0, bags = 0}
for _, it in ipairs(df.global.world.items.other.BARREL) do if empty(it) then containers.barrels = containers.barrels + 1 end end
for _, it in ipairs(df.global.world.items.other.BIN) do if empty(it) then containers.bins = containers.bins + 1 end end
for _, it in ipairs(df.global.world.items.other.BOX) do if empty(it) then containers.bags = containers.bags + 1 end end
for _, it in ipairs(df.global.world.items.other.TOOL) do
  local ok, sub = pcall(function() return it.subtype.id end)
  if ok and sub == 'ITEM_TOOL_LARGE_POT' and empty(it) then containers.large_pots = containers.large_pots + 1 end
end
print(json.encode({
  deaths = deaths, empty_containers = containers,
  abs_tick = df.global.cur_year * 403200 + t,
  date = string.format('%d %s, year %d', day, months[month + 1] or '?', df.global.cur_year),
  year = df.global.cur_year, tick = t, paused = dfhack.world.ReadPauseState(),
  screen = dfhack.gui.getCurFocus(true)[1], popups = popups(),
  order_check_timer = df.global.plotinfo.manager_timer,
  citizens = citizens, workshops = workshops, orders = orders,
}))

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
  table.insert(orders, {id = o.id, job = df.job_type[o.job_type], reaction = (o.reaction_name ~= '' and o.reaction_name or nil),
    total = o.amount_total, left = o.amount_left, validated = o.status.validated, active = o.status.active})
end
print(json.encode({
  date = string.format('%d %s, year %d', day, months[month + 1] or '?', df.global.cur_year),
  year = df.global.cur_year, tick = t, paused = dfhack.world.ReadPauseState(),
  screen = dfhack.gui.getCurFocus(true)[1], popups = popups(),
  order_check_timer = df.global.plotinfo.manager_timer,
  citizens = citizens, workshops = workshops, orders = orders,
}))

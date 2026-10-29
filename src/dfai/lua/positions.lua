-- DF_AI: fort positions (nobles/administrators).  Usage:
--   lua -f positions.lua list
--   lua -f positions.lua assign <POSITION_CODE> <unit_id>
--   lua -f positions.lua vacate <POSITION_CODE>
local json = require('json')
local args = {...}
local entity = df.historical_entity.find(df.global.plotinfo.group_id)
local function pos_by_code(code)
  for _, p in ipairs(entity.positions.own) do if p.code == code then return p end end
end
local function assignments_for(p)
  local out = {}
  for _, a in ipairs(entity.positions.assignments) do if a.position_id == p.id then table.insert(out, a) end end
  return out
end
local function unit_for_hf(hfid)
  for _, u in ipairs(dfhack.units.getCitizens()) do if u.hist_figure_id == hfid then return u end end
end
local function unit_name(u) return u and dfhack.df2utf(dfhack.units.getReadableName(u)) or nil end
local function list()
  local out = {}
  for _, p in ipairs(entity.positions.own) do
    local holders = {}
    for _, a in ipairs(assignments_for(p)) do
      if a.histfig ~= -1 then local u = unit_for_hf(a.histfig); table.insert(holders, {unit_id = u and u.id or nil, name = unit_name(u), hf = a.histfig}) end
    end
    table.insert(out, {code = p.code, name = dfhack.df2utf(p.name[0] or p.code), holders = holders,
      vacant = (#holders == 0), slots = #assignments_for(p)})
  end
  return out
end
local cmd = args[1]
local res
if cmd == 'list' then res = {positions = list()}
elseif cmd == 'assign' or cmd == 'vacate' then
  local p = pos_by_code(args[2] or '')
  if not p then res = {ok = false, error = 'unknown position code: ' .. tostring(args[2])}
  else
    local slot
    for _, a in ipairs(assignments_for(p)) do if (cmd == 'assign' and a.histfig == -1) or (cmd == 'vacate' and a.histfig ~= -1) then slot = a; break end end
    if not slot then res = {ok = false, error = (cmd == 'assign') and 'no vacant slot for ' .. p.code or (p.code .. ' is already vacant')}
    elseif cmd == 'vacate' then
      local hf = df.historical_figure.find(slot.histfig)
      if hf then
        for i = #hf.entity_links - 1, 0, -1 do
          local l = hf.entity_links[i]
          if df.histfig_entity_link_positionst:is_instance(l) and l.entity_id == entity.id and l.assignment_id == slot.id then hf.entity_links:erase(i); l:delete() end
        end
      end
      slot.histfig = -1; slot.histfig2 = -1
      res = {ok = true, vacated = p.code}
    else
      local u = df.unit.find(tonumber(args[3] or ''))
      if not u or not dfhack.units.isCitizen(u) then res = {ok = false, error = 'unit is not a citizen: ' .. tostring(args[3])}
      else
        local hf = df.historical_figure.find(u.hist_figure_id)
        slot.histfig = hf.id; slot.histfig2 = hf.id
        local link = df.histfig_entity_link_positionst:new()
        link.entity_id = entity.id; link.link_strength = 100; link.assignment_id = slot.id
        link.start_year = df.global.cur_year
        hf.entity_links:insert('#', link)
        res = {ok = true, assigned = p.code, unit_id = u.id, name = unit_name(u)}
      end
    end
  end
else res = {ok = false, error = 'usage: list | assign <CODE> <unit_id> | vacate <CODE>'} end
print(json.encode(res))

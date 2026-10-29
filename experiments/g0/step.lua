-- DF_AI G0 bounded-step probe (runs inside DFHack).  Usage via dfhack-run:
--   lua -f step.lua begin <ticks> | status | cancel
local json = require('json')
local args = {...}
_G.dfai = _G.dfai or {}
local S = _G.dfai
local function abs_tick() return df.global.cur_year * 403200 + df.global.cur_year_tick end
local function popups() local ok, v = pcall(function() return #df.global.world.status.popups end) return ok and v or -1 end
local function last_report_id() local r = df.global.world.status.reports; return #r > 0 and r[#r-1].id or -1 end
local function snapshot()
  local h = df.global.game.main_interface.help
  return { abs_tick = abs_tick(), year = df.global.cur_year, tick = df.global.cur_year_tick,
    paused = dfhack.world.ReadPauseState(), popups = popups(), help_open = h.open,
    focus = dfhack.gui.getCurFocus(true)[1] }
end
local cmd = args[1]
local out = {}
local cancelled = nil
if cmd == 'begin' then
  local n = tonumber(args[2])
  if S.timer and dfhack.timeout_active(S.timer) then out.error = 'step already active'; print(json.encode(out)) return end
  local pv = df.global.world.status.popups
  if #pv > 0 then
    out = { started = false, blocked = 'popup_open', popups = #pv, popup_text = dfhack.df2utf(pv[0].text):sub(1, 300) }
    print(json.encode(out)) return
  end
  S.start = snapshot(); S.requested = n; S.fired = false; S.fired_at = nil
  S.start_report = last_report_id(); S.start_popups = S.start.popups
  S.timer = dfhack.timeout(n, 'ticks', function() S.fired = true; S.fired_at = abs_tick(); dfhack.world.SetPauseState(true) end)
  dfhack.world.SetPauseState(false)
  out = { started = true, timer = S.timer, start = S.start, requested = n }
elseif cmd == 'status' or cmd == 'cancel' then
  local cur = snapshot()
  local active = S.timer and dfhack.timeout_active(S.timer) and true or false
  if cmd == 'cancel' and active then dfhack.timeout_active(S.timer, nil); active = (dfhack.timeout_active(S.timer) and true or false); cancelled = not active end
  local new_reports, pausing = {}, {}
  local flags = df.global.d_init.announcements.flags
  for _, r in ipairs(df.global.world.status.reports) do
    if r.id > (S.start_report or -1) then
      local t = df.announcement_type[r.type] or tostring(r.type)
      table.insert(new_reports, t)
      if flags[r.type] and (flags[r.type].DO_MEGA or flags[r.type].PAUSE) then table.insert(pausing, t) end
    end
  end
  local causes = {}
  if S.fired then table.insert(causes, 'controller_timer') end
  if cur.popups > (S.start_popups or 0) then table.insert(causes, 'popup_opened') end
  if #pausing > 0 then table.insert(causes, 'pausing_announcement') end
  if cur.help_open then table.insert(causes, 'help_open') end
  if cur.paused and #causes == 0 then table.insert(causes, 'unknown') end
  out = { cancelled = cancelled, now = cur, start = S.start, requested = S.requested,
    elapsed_ticks = S.start and (cur.abs_tick - S.start.abs_tick) or nil,
    timer_active = active, timer_fired = S.fired, fired_at = S.fired_at,
    pause_causes = causes, new_reports = new_reports, pausing_reports = pausing }
else
  out.error = 'usage: begin <ticks> | status | cancel'
end
print(json.encode(out))

// Simulates the 7-day check-in with the game's own DailyCheckin copy and its checkin-config.json and checks the rules
// (references/skin-bonus-and-checkin.md, user 2026-10-22). Run by audit_checkin.py with TZ=UTC; prints one JSON object.
//   node checkin_harness.mjs <DailyCheckin.mjs> <checkin-config.json>
import fs from 'fs';
import { pathToFileURL } from 'url';

const [modPath, cfgPath] = process.argv.slice(2);
const C = await import(pathToFileURL(modPath).href);
const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
const checks = [];
const add = (id, passed, detail) => checks.push({ id, passed: !!passed, detail });
const HOUR = 3600000, DAY = 24 * HOUR;
const T0 = Date.UTC(2026, 9, 19, 9);
const errs = C.validateCheckin(cfg);
add('config_valid', errs.length === 0, errs.length ? errs.join('; ') : '7 days, growing coins, big day 7, skins with fallback coins');
if (errs.length) { console.log(JSON.stringify({ checks })); process.exit(0); }

// once per day, seven days in order, then a new cycle
{
  let st = C.createCheckin(cfg, T0);
  const got = [], problems = [];
  for (let d = 0; d < 9; d++) {
    const now = T0 + d * DAY;
    const v = C.checkinStatus(st, cfg, now);
    if (!v.can_claim) problems.push('day ' + (d + 1) + ': cannot claim');
    const r = C.claimCheckin(st, cfg, now, []);
    st = r.state; got.push(r.claimed_day);
    const again = C.claimCheckin(st, cfg, now + 2 * HOUR, []);
    if (again.rewards.length || again.claimed_day) problems.push('day ' + (d + 1) + ': claimed twice');
    if (C.checkinStatus(st, cfg, now + HOUR).can_claim) problems.push('day ' + (d + 1) + ': still claimable after claiming');
  }
  const order = got.join(',') === '1,2,3,4,5,6,7,1,2';
  add('once_per_day_in_order', problems.length === 0 && order, problems.length ? problems.slice(0, 3).join('; ') : 'claims ' + got.join(','));
}
// day 7 is the big one and pays everything it lists
{
  let st = C.createCheckin(cfg, T0), r;
  for (let d = 0; d < 7; d++) r = C.claimCheckin(st = (r ? r.state : st), cfg, T0 + d * DAY, []);
  const ok = r.big === true && r.rewards.length === cfg.days[6].rewards.length && C.checkinStatus(r.state, cfg, T0 + 6 * DAY + HOUR).progress === '7/7';
  add('day7_big_bundle', ok, 'day 7 pays ' + r.rewards.map((x) => x.type + (x.amount ? ' ' + x.amount : ' ' + x.id)).join(', '));
}
// owned skin -> fallback coins
{
  let st = C.createCheckin(cfg, T0), r;
  const skinDay = cfg.days.findIndex((d) => d.rewards.some((x) => x.type === 'skin'));
  const skin = cfg.days[skinDay].rewards.find((x) => x.type === 'skin');
  for (let d = 0; d <= skinDay; d++) { r = C.claimCheckin(st, cfg, T0 + d * DAY, [skin.id]); st = r.state; }
  const paid = r.rewards.find((x) => x.instead_of === skin.id);
  add('owned_skin_pays_coins', paid && paid.type === 'coins' && paid.amount === skin.fallback_coins,
    paid ? skin.id + ' already owned -> ' + paid.amount + ' coins' : 'owned skin was given again');
}
// clock moved back, missed days, reset hour, save/load
{
  let st = C.createCheckin(cfg, T0);
  st = C.claimCheckin(st, cfg, T0, []).state;
  const back = C.claimCheckin(st, cfg, T0 - 2 * DAY, []);
  let miss = C.claimCheckin(st, cfg, T0 + 4 * DAY, []);
  const cumulativeOk = cfg.mode === 'cumulative' ? miss.claimed_day === 2 : miss.claimed_day === 1;
  const json = JSON.parse(JSON.stringify(st));
  const same = JSON.stringify(C.claimCheckin(json, cfg, T0 + DAY, [])) === JSON.stringify(C.claimCheckin(st, cfg, T0 + DAY, []));
  const h = cfg.reset_hour || 0;
  const beforeReset = Date.UTC(2026, 9, 20, h) - 60000, afterReset = Date.UTC(2026, 9, 20, h) + 60000;
  let s2 = C.claimCheckin(C.createCheckin(cfg, beforeReset - DAY), cfg, beforeReset - 2 * HOUR, []).state;
  const resetOk = !C.checkinStatus(s2, cfg, beforeReset).can_claim && C.checkinStatus(s2, cfg, afterReset).can_claim;
  add('clock_missed_days_reload', back.rewards.length === 0 && cumulativeOk && same && resetOk,
    'clock back: nothing; missed 3 days -> next card day ' + miss.claimed_day + ' (' + cfg.mode + '); save/load same; new day at ' + h + ':00');
}
console.log(JSON.stringify({ checks }));

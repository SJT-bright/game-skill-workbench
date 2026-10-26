// @ts-nocheck
// DailyCheckin.ts — 7-day check-in reward (both boards, optional; references/skin-bonus-and-checkin.md, user 2026-10-22).
// COPY THIS FILE UNCHANGED into the game (audit_checkin.py compares its SHA-256 with the skill's copy).
// Tune the rewards in checkin-config.json only. Plain JavaScript inside a .ts file: runs in Cocos 2.4 / 3.x and Node.
// Pure functions, no engine calls, no Date.now(): pass nowMs in; save the returned state yourself.
//
// Game glue:
//   start / onShow: v = checkinStatus(state || createCheckin(cfg, now), cfg, now); if (v.can_claim) open the popup
//                   (red dot on the calendar icon while can_claim)
//   Claim button:   r = claimCheckin(state, cfg, now, ownedSkinIds); grant r.rewards; save wallet + r.state together
//   popup cards:    v.days -> [{day, rewards, big, state: claimed | today | future}], v.progress "3/7", v.next_at

export const CHECKIN_VERSION = 1;
const DAY = 86400000;
const TYPES = ['coins', 'energy', 'stars', 'item', 'skin'];

function copy(x) { return JSON.parse(JSON.stringify(x)); }
function isInt(v) { return typeof v === 'number' && Math.floor(v) === v; }

export function localDay(cfg, nowMs) {
  const d = new Date(nowMs - (cfg.reset_hour || 0) * 3600000);
  return Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / DAY);
}

export function nextResetAt(cfg, nowMs) {
  const u = new Date((localDay(cfg, nowMs) + 1) * DAY);
  return new Date(u.getUTCFullYear(), u.getUTCMonth(), u.getUTCDate(), cfg.reset_hour || 0).getTime();
}

function coinsOf(day) {
  return day.rewards.reduce((n, r) => n + (r.type === 'coins' ? r.amount : 0), 0);
}

// audit_checkin.py runs this too
export function validateCheckin(cfg) {
  const e = [];
  const need = (ok, msg) => { if (!ok) e.push(msg); };
  if (!cfg || typeof cfg !== 'object') return ['config must be an object'];
  need(cfg.schema === 'checkin_config.v1', 'schema must be checkin_config.v1');
  need(cfg.mode === 'cumulative' || cfg.mode === 'consecutive', 'mode cumulative (missed days do not reset, default) | consecutive');
  need(isInt(cfg.reset_hour || 0) && (cfg.reset_hour || 0) >= 0 && (cfg.reset_hour || 0) <= 23, 'reset_hour 0..23');
  need(isInt(cfg.R) && cfg.R > 0, 'R = coins of a medium level (same as coins_per_ad in unlock_table.json)');
  const days = cfg.days;
  need(Array.isArray(days) && days.length === 7, 'days: exactly 7');
  if (!Array.isArray(days) || days.length !== 7) return e;
  days.forEach((d, i) => {
    need(d && d.day === i + 1 && Array.isArray(d.rewards) && d.rewards.length >= 1, 'days[' + i + ']: day ' + (i + 1) + ' with rewards');
    (d && Array.isArray(d.rewards) ? d.rewards : []).forEach((r, k) => {
      need(r && TYPES.indexOf(r.type) >= 0, 'day ' + (i + 1) + ' reward ' + k + ': type ' + TYPES.join('|'));
      if (r && r.type === 'skin') need(typeof r.id === 'string' && r.id && isInt(r.fallback_coins) && r.fallback_coins > 0,
        'day ' + (i + 1) + ': skin reward needs id and fallback_coins (paid when the skin is already owned)');
      else if (r) need(isInt(r.amount) && r.amount > 0, 'day ' + (i + 1) + ' reward ' + k + ': whole amount > 0');
      if (r && r.type === 'item') need(typeof r.id === 'string' && r.id, 'day ' + (i + 1) + ': item reward needs an id');
    });
  });
  const ok7 = days.every((d) => d && Array.isArray(d.rewards));
  if (!ok7) return e;
  const coinDays = days.slice(0, 6).filter((d) => coinsOf(d) > 0);
  need(coinDays.length >= 2, 'days 1-6: at least two coin days');
  for (let i = 1; i < coinDays.length; i++) need(coinsOf(coinDays[i]) > coinsOf(coinDays[i - 1]), 'coin days must grow (day ' + coinDays[i].day + ')');
  need(coinDays.length === 0 || coinsOf(coinDays[0]) >= cfg.R, 'day 1 coins >= R (one medium level)');
  need(days.slice(0, 6).some((d) => d.rewards.some((r) => r.type !== 'coins')), 'days 1-6: at least one non-coin reward (energy/stars/item/skin)');
  const last = days[6];
  need(last.big === true && typeof last.title === 'string' && last.title, 'day 7: big: true and a title (e.g. "Mystery Gift"), drawn as the large card');
  need(last.rewards.length >= 3 && new Set(last.rewards.map((r) => r.type)).size >= 2, 'day 7: a big bundle of >= 3 rewards of >= 2 kinds');
  const before = days.slice(0, 6).reduce((n, d) => n + coinsOf(d), 0);
  need(coinsOf(last) >= Math.max(...days.slice(0, 6).map(coinsOf)) * 2 && coinsOf(last) >= before * 0.5,
    'day 7 coins >= 2x the biggest earlier day and >= half of days 1-6 together (the final reward is the big one)');
  const skins = days.reduce((a, d) => a.concat(d.rewards.filter((r) => r.type === 'skin').map((r) => r.id)), []);
  need(skins.length >= 1, 'at least one check-in skin in the 7 days (user: coins, skins and stars)');
  need(new Set(skins).size === skins.length, 'check-in skins are all different');
  need(days.slice(0, 6).every((d) => !d.big), 'only day 7 is big');
  return e;
}

export function createCheckin(cfg, nowMs) {
  return { v: 1, claimed: 0, cycle: 0, last_day: null, total: 0, created: localDay(cfg, nowMs) };
}

function canClaim(cfg, st, nowMs) {
  return st.last_day === null || localDay(cfg, nowMs) > st.last_day;
}

function position(cfg, st, nowMs) {
  // index (0..6) of the card the player claims next, after a consecutive-mode reset
  const today = localDay(cfg, nowMs);
  if (cfg.mode === 'consecutive' && st.last_day !== null && today > st.last_day + 1) return 0;
  return st.claimed;
}

export function checkinStatus(state, cfg, nowMs) {
  const st = state;
  const can = canClaim(cfg, st, nowMs);
  const pos = can ? position(cfg, st, nowMs) : st.claimed;
  const shownClaimed = can ? pos : (st.claimed === 0 && st.last_day !== null ? 7 : st.claimed);   // just finished a cycle today
  const days = cfg.days.map((d, i) => ({ day: d.day, rewards: d.rewards, big: !!d.big, title: d.title || '',
    state: i < shownClaimed ? 'claimed' : (can && i === pos ? 'today' : 'future') }));
  return { can_claim: can, today_index: can ? pos : -1, days, progress: shownClaimed + '/7', next_at: nextResetAt(cfg, nowMs),
    cycle: st.cycle };
}

export function claimCheckin(state, cfg, nowMs, owned) {
  const st = copy(state);
  if (!canClaim(cfg, st, nowMs)) return { state: st, rewards: [], claimed_day: 0 };     // once per day; clock back: nothing
  const pos = position(cfg, st, nowMs);
  const have = (owned || []).slice();
  const rewards = cfg.days[pos].rewards.map((r) => {
    if (r.type === 'skin' && have.indexOf(r.id) >= 0) return { type: 'coins', amount: r.fallback_coins, instead_of: r.id };
    return copy(r);
  });
  st.claimed = pos + 1;
  st.last_day = localDay(cfg, nowMs);
  st.total += 1;
  if (st.claimed === 7) { st.claimed = 0; st.cycle += 1; }
  return { state: st, rewards, claimed_day: pos + 1, big: !!cfg.days[pos].big };
}

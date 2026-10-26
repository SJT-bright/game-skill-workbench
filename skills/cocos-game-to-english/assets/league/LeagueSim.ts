// @ts-nocheck
// LeagueSim.ts — Weekly League with simulated rivals (重塑 only; references/ranking-league.md, user 2026-10-21).
// COPY THIS FILE UNCHANGED into the game (audit_league.py compares its SHA-256 with the skill's copy).
// Tune the numbers in league-config.json only. Plain JavaScript inside a .ts file, so the same file runs in
// Cocos Creator 2.4 / 3.x and in Node for the audit. No engine calls and no Date.now(): pass nowMs in.
// Every function is pure: it returns a new state and never changes the one passed in.
//
// Game glue (written per game, outside this file):
//   start / onShow:  r = openLeague(state || createState(cfg, randomSeed, now), cfg, now); save(r.state); show r.pending
//   round end:       r = recordRound(state, cfg, {win, stars, score}, now); save(r.state); show r.result on the result page
//   league page:     v = leaderboard(state, cfg, now)  -> rows, countdown, gap to the rival above
//   claim button:    r = claimSettlement(state); grant r.rewards (coins/skins) and save the wallet + r.state together

export const LEAGUE_SIM_VERSION = 1;

const ADJ = ['Sunny', 'Mochi', 'Lucky', 'Fizzy', 'Jolly', 'Peachy', 'Bouncy', 'Cozy', 'Zippy', 'Sparkly', 'Happy', 'Minty',
  'Cocoa', 'Bubbly', 'Snappy', 'Giggly', 'Breezy', 'Honey', 'Candy', 'Pixel', 'Tiny', 'Wiggly', 'Rosy', 'Sugar',
  'Comet', 'Maple', 'Jelly', 'Puffy', 'Twinkle', 'Cloudy'];
const NOUN = ['Fox', 'Panda', 'Bunny', 'Kitty', 'Otter', 'Duck', 'Bear', 'Koala', 'Puffin', 'Mango', 'Berry', 'Cookie',
  'Muffin', 'Star', 'Bean', 'Pebble', 'Chick', 'Frog', 'Tiger', 'Penguin', 'Hamster', 'Llama', 'Lemon', 'Donut',
  'Waffle', 'Seal', 'Owl', 'Cub', 'Sprout', 'Dino'];

function hash32(text) {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) { h ^= text.charCodeAt(i); h = Math.imul(h, 0x01000193); }
  return h >>> 0;
}

// Same key -> same number in [0, 1): the league looks the same after closing and reopening the game.
export function rand(seed, a, b, c) {
  let t = (hash32(String(seed) + '|' + a + '|' + b + '|' + c) + 0x6d2b79f5) >>> 0;
  let r = Math.imul(t ^ (t >>> 15), 1 | t);
  r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
  return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
}

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
function copy(state) { return JSON.parse(JSON.stringify(state)); }
function isInt(v) { return typeof v === 'number' && Math.floor(v) === v; }
function num(v) { return typeof v === 'number' && isFinite(v); }

// ---------------------------------------------------------------- config check (audit_league.py runs it too)
export function validateConfig(cfg) {
  const e = [];
  const need = (ok, msg) => { if (!ok) e.push(msg); };
  if (!cfg || typeof cfg !== 'object') return ['config must be an object'];
  need(cfg.schema === 'league_config.v1', 'schema must be league_config.v1');
  need(isInt(cfg.pool_size) && cfg.pool_size >= 1000 && cfg.pool_size <= 10000000, 'pool_size: whole number 1000..10000000');
  need(isInt(cfg.start_rank) && cfg.start_rank >= cfg.pool_size * 0.5 && cfg.start_rank <= cfg.pool_size,
    'start_rank: whole number between half of pool_size and pool_size');
  need(isInt(cfg.best_rank) && cfg.best_rank >= 2 && cfg.best_rank <= 10, 'best_rank: 2..10 (the player is never #1)');
  const c = cfg.curve || {};
  need(num(c.half_points) && c.half_points > 0, 'curve.half_points > 0');
  need(num(c.power) && c.power >= 0.8 && c.power <= 3, 'curve.power 0.8..3');
  const o = cfg.others || {};
  need(num(o.beta) && o.beta > 0 && o.beta < 1, 'others.beta between 0 and 1');
  need(num(o.beta) && num(c.power) && o.beta * c.power < 0.8, 'others.beta x curve.power must stay below 0.8 (rivals above must keep rising)');
  need(num(o.jitter) && o.jitter >= 0 && o.jitter <= 0.2, 'others.jitter 0..0.2');
  const d = cfg.drop || {};
  need(num(d.chance) && d.chance >= 0.05 && d.chance <= 0.06, 'drop.chance 0.05..0.06 (user rule: 5-6% of rounds)');
  need(num(d.min_pct) && num(d.max_pct) && d.min_pct >= 0 && d.min_pct <= d.max_pct && d.max_pct <= 0.05, 'drop: 0 <= min_pct <= max_pct <= 0.05');
  need(isInt(d.min) && isInt(d.max) && d.min >= 1 && d.max >= d.min, 'drop: whole numbers 1 <= min <= max');
  need(isInt(d.grace_rounds) && d.grace_rounds >= 0 && d.grace_rounds <= 10, 'drop.grace_rounds 0..10');
  need(isInt(cfg.min_step_above_rank) && cfg.min_step_above_rank >= cfg.best_rank, 'min_step_above_rank >= best_rank');
  const g = cfg.gain || {};
  need(['level', 'score', 'time'].indexOf(g.mode) >= 0, 'gain.mode level | score | time');
  need(num(g.win) && g.win > 0, 'gain.win > 0');
  need(num(g.lose_factor) && g.lose_factor > 0 && g.lose_factor <= 1, 'gain.lose_factor 0..1 (a lost round still moves a little)');
  need(g.mode === 'level' || (num(g.score_ref) && g.score_ref > 0 && num(g.score_min) && num(g.score_max) && g.score_min > 0 && g.score_max >= g.score_min),
    'score/time mode needs score_ref > 0 and 0 < score_min <= score_max');
  const a = cfg.absence || {};
  need(num(a.after_hours) && a.after_hours >= 1 && num(a.per_hour_pct) && a.per_hour_pct >= 0 && num(a.max_pct) && a.max_pct >= 0 && a.max_pct <= 0.2,
    'absence: after_hours >= 1, per_hour_pct >= 0, max_pct 0..0.2');
  const w = cfg.week || {};
  need(isInt(w.reset_weekday) && w.reset_weekday >= 1 && w.reset_weekday <= 7 && isInt(w.reset_hour) && w.reset_hour >= 0 && w.reset_hour <= 23,
    'week.reset_weekday 1..7 (1 = Monday), week.reset_hour 0..23');
  const t = cfg.tiers;
  need(Array.isArray(t) && t.length >= 3, 'tiers: at least 3');
  if (Array.isArray(t)) t.forEach((x, i) => {
    need(x && typeof x.id === 'string' && typeof x.name === 'string' && num(x.hardness) && x.hardness >= 1, 'tiers[' + i + ']: id, name, hardness >= 1');
    if (i) need(x && t[i - 1] && x.hardness >= t[i - 1].hardness, 'tiers: hardness never goes down');
  });
  need(isInt(cfg.promote_top_rank) && isInt(cfg.demote_from_rank) && cfg.promote_top_rank > cfg.best_rank &&
    cfg.promote_top_rank < cfg.demote_from_rank && cfg.demote_from_rank <= cfg.pool_size, 'best_rank < promote_top_rank < demote_from_rank <= pool_size');
  const r = cfg.rewards;
  need(Array.isArray(r) && r.length >= 2, 'rewards: at least 2 brackets');
  if (Array.isArray(r)) {
    r.forEach((x, i) => {
      need(x && isInt(x.max_rank) && isInt(x.coins) && x.coins > 0, 'rewards[' + i + ']: whole max_rank and coins > 0');
      if (i && x && r[i - 1]) {
        need(x.max_rank > r[i - 1].max_rank, 'rewards: max_rank goes up');
        need(x.coins <= r[i - 1].coins, 'rewards: a better rank never gets fewer coins');
      }
    });
    need(r.length && r[r.length - 1] && r[r.length - 1].max_rank >= cfg.pool_size, 'rewards: last bracket covers the whole pool');
    need(r.some((x) => x && x.skin === true), 'rewards: at least one bracket gives a league skin');
  }
  const s = cfg.league_skins;
  need(Array.isArray(s) && s.length === 10 && new Set(s).size === 10 && s.every((x) => typeof x === 'string' && x),
    'league_skins: exactly 10 different skin ids (user rule: 10 league-only skins, then coins only)');
  need(isInt(cfg.skin_fallback_coins) && cfg.skin_fallback_coins > 0, 'skin_fallback_coins > 0 (paid instead of a skin once all 10 are owned)');
  const v = cfg.view || {};
  need(isInt(v.above) && isInt(v.below) && isInt(v.top) && v.above >= 3 && v.below >= 2 && v.top >= 3, 'view: above >= 3, below >= 2, top >= 3');
  need(isInt(cfg.avatars) && cfg.avatars >= 6, 'avatars: at least 6 avatar pictures');
  return e;
}

// ---------------------------------------------------------------- time
const DAY = 86400000;
function localDay(nowMs, hour) {
  const d = new Date(nowMs - hour * 3600000);
  return Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / DAY);
}
export function weekIndex(cfg, nowMs) {
  // 1970-01-01 was a Thursday; +3 makes Monday the first day, then shift to the configured reset day.
  return Math.floor((localDay(nowMs, cfg.week.reset_hour) + 3 - (cfg.week.reset_weekday - 1)) / 7);
}
export function weekEndsAt(cfg, week) {
  const days = (week + 1) * 7 - 3 + (cfg.week.reset_weekday - 1);
  const u = new Date(days * DAY);
  return new Date(u.getUTCFullYear(), u.getUTCMonth(), u.getUTCDate(), cfg.week.reset_hour).getTime();
}

// ---------------------------------------------------------------- state
function weekStartRank(cfg, seed, week) {
  const u = rand(seed, 'start', week, 0);
  return clamp(Math.round(cfg.start_rank * (0.97 + 0.06 * u)), cfg.min_step_above_rank + 1, cfg.pool_size);
}

export function createState(cfg, seed, nowMs) {
  const week = weekIndex(cfg, nowMs);
  const start = weekStartRank(cfg, seed, week);
  return { v: 1, seed: String(seed), week, tier: 0, points: 0, rounds: 0, rank: start, start_rank: start,
    best_rank_week: start, last_ts: nowMs, skins: [], pending: [], total_rounds: 0, drops: 0 };
}

function tierOf(cfg, st) { return cfg.tiers[clamp(st.tier, 0, cfg.tiers.length - 1)]; }

export function curveRank(cfg, st, points) {
  const h = cfg.curve.half_points * tierOf(cfg, st).hardness;
  return cfg.best_rank + (st.start_rank - cfg.best_rank) * Math.pow(1 + points / h, -cfg.curve.power);
}

function skinsTaken(st) {
  const taken = st.skins.slice();
  st.pending.forEach((p) => { if (p.skin) taken.push(p.skin); });
  return taken;
}

function settle(cfg, st) {
  if (st.rounds <= 0) return null;                        // did not play that week: no reward, tier stays
  const rank = st.rank;
  const last = cfg.tiers.length - 1;
  const tierAfter = rank <= cfg.promote_top_rank ? Math.min(st.tier + 1, last)
    : rank >= cfg.demote_from_rank ? Math.max(st.tier - 1, 0) : st.tier;
  const bracket = cfg.rewards.find((b) => rank <= b.max_rank) || cfg.rewards[cfg.rewards.length - 1];
  let coins = bracket.coins, skin = null;
  if (bracket.skin) {
    const taken = skinsTaken(st);
    skin = cfg.league_skins.find((id) => taken.indexOf(id) < 0) || null;
    if (!skin) coins += cfg.skin_fallback_coins;           // all 10 league skins owned: coins only from now on
  }
  return { week: st.week, rank, points: st.points, tier_before: st.tier, tier_after: tierAfter, coins, skin };
}

function rollWeek(cfg, st, nowMs) {
  const week = weekIndex(cfg, nowMs);
  if (week <= st.week) return null;                       // same week, or the clock went back: change nothing
  const s = settle(cfg, st);
  if (s) { st.pending.push(s); st.tier = s.tier_after; }
  st.week = week;
  st.points = 0; st.rounds = 0;
  st.start_rank = weekStartRank(cfg, st.seed, week);
  st.rank = st.start_rank; st.best_rank_week = st.start_rank;
  return s;
}

// Call on game start and every time the game comes back to the front.
export function openLeague(state, cfg, nowMs) {
  const st = copy(state);
  const settled = rollWeek(cfg, st, nowMs);
  let drift = 0;
  const hours = (nowMs - st.last_ts) / 3600000;
  if (!settled && st.rounds > 0 && hours >= cfg.absence.after_hours) {
    const pct = Math.min(cfg.absence.max_pct, cfg.absence.per_hour_pct * hours);
    drift = Math.min(cfg.pool_size, st.rank + Math.max(1, Math.round(st.rank * pct))) - st.rank;
    st.rank += drift;
  }
  st.last_ts = Math.max(st.last_ts, nowMs);
  return { state: st, settled, drift, pending: st.pending.slice() };
}

export function roundGain(cfg, res) {
  const g = cfg.gain;
  let gain;
  if (g.mode === 'level') {
    gain = g.win + (num(res.stars) ? Math.max(0, res.stars) : 0) * (g.stars_bonus || 0);
  } else {
    const s = num(res.score) && res.score > 0 ? res.score : 0;
    const ratio = s ? (g.mode === 'time' ? g.score_ref / s : s / g.score_ref) : g.score_min;
    gain = g.win * clamp(ratio, g.score_min, g.score_max);
  }
  if (!res.win) gain *= g.lose_factor;
  return Math.max(1, Math.round(gain));
}

// Call once per finished round (win or lose). result: {before, after, change, event: rise|drop|same, gain, passed}
export function recordRound(state, cfg, res, nowMs) {
  const st = copy(state);
  const settled = rollWeek(cfg, st, nowMs);
  const gain = roundGain(cfg, res || {});
  const before = st.rank;
  st.points += gain; st.rounds += 1; st.total_rounds += 1;
  let after, event;
  if (st.rounds > cfg.drop.grace_rounds && rand(st.seed, 'drop', st.week, st.rounds) < cfg.drop.chance) {
    const pct = cfg.drop.min_pct + (cfg.drop.max_pct - cfg.drop.min_pct) * rand(st.seed, 'dropsize', st.week, st.rounds);
    after = Math.min(cfg.pool_size, before + clamp(Math.round(before * pct), cfg.drop.min, cfg.drop.max));
    event = 'drop'; st.drops += 1;
  } else {
    after = Math.min(before, Math.round(curveRank(cfg, st, st.points)));
    if (after >= before && before > cfg.min_step_above_rank) after = before - 1;   // far from the top every round moves up
    after = Math.max(after, cfg.best_rank);
    event = after < before ? 'rise' : 'same';
  }
  st.rank = after;
  st.best_rank_week = Math.min(st.best_rank_week, after);
  st.last_ts = Math.max(st.last_ts, nowMs);
  const passed = [];
  if (event === 'rise') for (let j = after; j < Math.min(before, after + 3); j++) passed.push(rival(cfg, st, j).name);
  if (event === 'drop') for (let j = before; j < Math.min(after, before + 3); j++) passed.push(rival(cfg, st, j).name);
  return { state: st, settled, result: { before, after, change: before - after, event, gain, points: st.points, passed } };
}

// The game grants these rewards and saves its wallet together with the returned state (one save).
export function claimSettlement(state) {
  const st = copy(state);
  const rewards = st.pending;
  rewards.forEach((p) => { if (p.skin && st.skins.indexOf(p.skin) < 0) st.skins.push(p.skin); });
  st.pending = [];
  return { state: st, rewards };
}

// ---------------------------------------------------------------- rivals and the visible board
// Rival j is the j-th computer player of this week (j = 1 is always above the player, who is never #1).
export function rival(cfg, st, j) {
  const adj = (cfg.names && cfg.names.adjectives) || ADJ;
  const noun = (cfg.names && cfg.names.nouns) || NOUN;
  const u = (k) => rand(st.seed, 'rival' + k, st.week, j);
  const digits = u(3) < 0.65 ? String(10 + Math.floor(u(4) * 90)) : '';
  return { name: adj[Math.floor(u(1) * adj.length)] + noun[Math.floor(u(2) * noun.length)] + digits,
    avatar: Math.floor(u(5) * cfg.avatars), mult: 1 + cfg.others.jitter * (u(6) - 0.5) };
}

// Rivals' points follow the player's: when the player's points grow, everyone's grow in proportion.
// Uses the smooth curve rank of the player's points (not the shown rank), so a drop or a catch-up round does not
// make the leaders' points jump around; the shown order is then kept by the two passes in leaderboard().
function rivalScore(cfg, st, j, anchor, curve) {
  return Math.round(anchor * Math.pow((curve - 0.5) / j, cfg.others.beta) * rival(cfg, st, j).mult);
}

export function leaderboard(state, cfg, nowMs) {
  const st = state;
  const joined = st.rounds > 0;
  const r = st.rank;
  const P = st.points;
  const anchor = Math.max(P, cfg.gain.win);
  const curve = Math.max(cfg.best_rank, curveRank(cfg, st, P));
  const ranks = [];
  for (let k = 1; k <= Math.min(cfg.view.top, r - 1); k++) ranks.push(k);
  for (let k = Math.max(1, r - cfg.view.above); k <= Math.min(cfg.pool_size, r + cfg.view.below); k++) if (ranks.indexOf(k) < 0) ranks.push(k);
  const rows = ranks.map((k) => {
    if (k === r) return { rank: k, name: 'You', avatar: -1, score: P, is_player: true };
    const j = k < r ? k : k - 1;
    const b = rival(cfg, st, j);
    return { rank: k, name: b.name, avatar: b.avatar, score: rivalScore(cfg, st, j, anchor, curve), is_player: false };
  });
  const at = rows.findIndex((x) => x.is_player);
  for (let i = at - 1; i >= 0; i--) rows[i].score = Math.max(rows[i].score, rows[i + 1].score + 1);   // above: more points
  for (let i = at + 1; i < rows.length; i++) rows[i].score = Math.max(0, Math.min(rows[i].score, rows[i - 1].score));
  const above = at > 0 ? rows[at - 1] : null;
  return { joined, rank: r, pool_size: cfg.pool_size, points: P, tier: tierOf(cfg, st), tier_index: st.tier,
    title: cfg.title, rows, gap_to_next: above ? above.score - P + 1 : 0, next_name: above ? above.name : '',
    ends_at: weekEndsAt(cfg, st.week), best_rank_week: st.best_rank_week, skins_owned: st.skins.length,
    next_skin: cfg.league_skins.find((id) => skinsTaken(st).indexOf(id) < 0) || null,
    pending: st.pending.slice() };
}

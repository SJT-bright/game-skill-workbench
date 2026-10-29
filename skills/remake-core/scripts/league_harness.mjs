// Simulates thousands of rounds with the game's own LeagueSim copy and its league-config.json, and checks the
// user's rules (remake-core/references/ranking-league.md, 2026-10-21). Run by audit_league.py; prints one JSON object.
//   node league_harness.mjs <LeagueSim.mjs> <league-config.json>
// TZ is set to UTC by the caller so week boundaries are the same on every machine.
import fs from 'fs';
import { pathToFileURL } from 'url';

const [modPath, cfgPath] = process.argv.slice(2);
const L = await import(pathToFileURL(modPath).href);
const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
const checks = [];
const add = (id, passed, detail) => checks.push({ id, passed: !!passed, detail });
const HOUR = 3600000, DAY = 24 * HOUR;
const T0 = Date.UTC(2026, 9, 19, 9);               // a Monday morning
const errs = L.validateConfig(cfg);
add('config_valid', errs.length === 0, errs.length ? errs.join('; ') : 'all parameters inside the allowed ranges');
if (errs.length) { console.log(JSON.stringify({ checks })); process.exit(0); }

const win = (seed, i) => L.rand('harness' + seed, 'win', i, 0) < 0.8;
const play = (st, seed, i, now) => L.recordRound(st, cfg, { win: win(seed, i), stars: win(seed, i) ? 3 : 0 }, now);

// --- one long week per player: rank path, drop rate, rise each round, rivals follow, board consistency
let rounds = 0, eligible = 0, drops = 0, minRank = Infinity, firstSeen = 0, noRise = [], notUp = [], boardBad = [], followBad = [];
const early = [], mid = [], late = [];
const players = 40, perWeek = [300, 300, 300, 3000];
for (let s = 0; s < players; s++) {
  const n = perWeek[s % perWeek.length];
  let st = L.createState(cfg, 'p' + s, T0);
  let prevTop = null;
  for (let i = 0; i < n; i++) {
    const now = T0 + Math.floor(i * (5 * DAY) / n);
    const r = play(st, s, i, now);
    const res = r.result;
    rounds++;
    if (r.state.rounds > cfg.drop.grace_rounds) eligible++;
    if (res.event === 'drop') drops++;
    if (r.state.points <= st.points) notUp.push('p' + s + ' round ' + (i + 1));
    if (res.event !== 'drop' && res.before > cfg.min_step_above_rank && res.after >= res.before) noRise.push('p' + s + ' round ' + (i + 1));
    if (res.event !== 'drop' && n === 300) {
      const up = res.before - res.after;
      if (i < 10) early.push(up); else if (i >= 40 && i < 50) mid.push(up); else if (i >= 190 && i < 200) late.push(up);
    }
    minRank = Math.min(minRank, r.state.rank);
    st = r.state;
    if (i % 7 === 0 || i === n - 1) {
      const b = L.leaderboard(st, cfg, now);
      const rows = b.rows;
      const me = rows.filter((x) => x.is_player);
      const ok = me.length === 1 && me[0].rank === st.rank && rows[0].rank === 1 && !rows[0].is_player &&
        rows.every((x, k) => k === 0 || (x.rank > rows[k - 1].rank && x.score <= rows[k - 1].score)) &&
        rows.every((x) => x.is_player || (x.rank < st.rank ? x.score > st.points : x.score <= st.points)) &&
        rows.some((x) => x.rank === st.rank - 1) && b.gap_to_next >= 1;
      if (!ok && boardBad.length < 5) boardBad.push('p' + s + ' round ' + (i + 1) + ' rank ' + st.rank);
      if (rows.some((x) => x.is_player && x.rank === 1)) firstSeen++;
      if (prevTop !== null && rows[0].score <= prevTop && followBad.length < 5)
        followBad.push('p' + s + ' round ' + (i + 1) + ': #1 went ' + prevTop + ' -> ' + rows[0].score);
      prevTop = rows[0].score;
    }
  }
}
add('never_first', minRank >= cfg.best_rank && firstSeen === 0,
  'best rank reached ' + minRank + ' (limit #' + cfg.best_rank + ') over ' + rounds + ' rounds, up to 3000 rounds in one week');
const rate = drops / Math.max(1, eligible);
add('drop_rate', rate >= 0.05 && rate <= 0.06, 'rank went down in ' + (rate * 100).toFixed(2) + '% of rounds (' + drops + ' of ' + eligible + '); must be 5-6%');
add('rise_each_round', noRise.length === 0 && notUp.length === 0,
  noRise.length || notUp.length ? 'no rise: ' + noRise.slice(0, 3).join(', ') + ' points not up: ' + notUp.slice(0, 3).join(', ')
    : 'every round adds points; every round without a drop moves up while rank > ' + cfg.min_step_above_rank);
const avg = (a) => a.reduce((x, y) => x + y, 0) / Math.max(1, a.length);
const e = avg(early), m = avg(mid), l = avg(late);
add('fast_then_slow', e > m && m > l && e >= 5 * l, 'average places gained per round: rounds 1-10 ' + e.toFixed(1) +
  ', rounds 41-50 ' + m.toFixed(1) + ', rounds 191-200 ' + l.toFixed(1));
add('board_consistent', boardBad.length === 0, boardBad.length ? 'bad board at ' + boardBad.join(', ')
  : 'rows sorted, player row matches the rank, rivals above have more points and rivals below not more');
add('rivals_follow', followBad.length === 0, followBad.length ? followBad.join('; ') : 'the leaders\' points rise every time the player\'s points rise');

// --- same inputs, same league; saving and loading after every round changes nothing
const run = (reload) => {
  let st = L.createState(cfg, 'same', T0);
  const log = [];
  for (let i = 0; i < 120; i++) {
    if (reload) st = JSON.parse(JSON.stringify(st));
    const r = play(st, 'same', i, T0 + i * HOUR);
    st = r.state; log.push(r.result);
  }
  return JSON.stringify([log, L.leaderboard(st, cfg, T0 + 200 * HOUR)]);
};
add('deterministic_after_reload', run(false) === run(true), 'same results with and without save/load between rounds');

// --- weekly reset, rewards: 10 league skins in order, then coins only; claim once; unplayed weeks give nothing
{
  let st = L.createState(cfg, 'weekly', T0);
  const got = [], problems = [];
  let coinsAfterTen = 0, weeksWithReward = 0, tierPath = [];
  for (let w = 0; w < 40; w++) {
    const weekStart = T0 + w * 7 * DAY;
    if (w === 5) continue;                                 // a week the player skips
    let o = L.openLeague(st, cfg, weekStart);
    st = o.state;
    if (w > 0 && w !== 6 && o.pending.length !== 1) problems.push('week ' + w + ': expected one settlement, got ' + o.pending.length);
    if (w === 6 && o.pending.length !== 1) problems.push('skipped week must not add a settlement');
    if (o.pending.length) {
      const c = L.claimSettlement(st);
      st = c.state;
      const again = L.claimSettlement(st);
      if (again.rewards.length) problems.push('week ' + w + ': second claim paid again');
      c.rewards.forEach((p) => {
        weeksWithReward++;
        if (p.skin) got.push(p.skin);
        const bracket = cfg.rewards.find((b) => p.rank <= b.max_rank);
        if (bracket && bracket.skin && !p.skin) { coinsAfterTen++; if (got.length < 10) problems.push('week ' + w + ': skin bracket paid no skin before all 10 were owned'); }
        if (p.skin && p.coins !== bracket.coins) problems.push('week ' + w + ': coins differ from the bracket');
        if (!p.skin && bracket && bracket.skin && p.coins !== bracket.coins + cfg.skin_fallback_coins) problems.push('week ' + w + ': fallback coins missing');
        tierPath.push(p.tier_after);
      });
    }
    for (let i = 0; i < 260; i++) st = play(st, 'weekly', w * 1000 + i, weekStart + HOUR + i * 20 * 60000).state;
  }
  const order = got.every((id, k) => id === cfg.league_skins[k]);
  add('weekly_rewards', problems.length === 0 && got.length === 10 && new Set(got).size === 10 && order && coinsAfterTen > 0,
    problems.length ? problems.slice(0, 4).join('; ') : 'league skins awarded ' + got.length + '/10 in order, then coins only (' + coinsAfterTen +
      ' weeks); claim pays once; skipped week pays nothing; tiers ' + Math.min(...tierPath) + '..' + Math.max(...tierPath));
}

// --- clock moved back, and coming back after a long break
{
  let st = L.createState(cfg, 'clock', T0);
  for (let i = 0; i < 30; i++) st = play(st, 'clock', i, T0 + i * 60000).state;
  const back = L.openLeague(st, cfg, T0 - 3 * DAY).state;
  const sameWeek = back.week === st.week && back.rank === st.rank && back.points === st.points;
  const away = L.openLeague(st, cfg, T0 + 72 * HOUR);
  const limit = Math.max(1, Math.round(st.rank * cfg.absence.max_pct));
  const okAway = away.drift >= 0 && away.drift <= limit && away.state.rank >= st.rank;
  const again = L.openLeague(away.state, cfg, T0 + 72 * HOUR + 60000);
  add('clock_and_absence', sameWeek && okAway && again.drift === 0,
    'clock back: no change; 3 days away: rank ' + st.rank + ' -> ' + away.state.rank + ' (max ' + limit + ' places), applied once');
}

// --- pending settlements from two weeks without opening the claim popup get different skins
{
  let st = L.createState(cfg, 'twopending', T0);
  for (let i = 0; i < 400; i++) st = play(st, 'tp', i, T0 + HOUR + i * 60000).state;
  st = L.openLeague(st, cfg, T0 + 7 * DAY + HOUR).state;
  for (let i = 0; i < 600; i++) st = play(st, 'tp2', i, T0 + 7 * DAY + 2 * HOUR + i * 60000).state;
  st = L.openLeague(st, cfg, T0 + 14 * DAY + HOUR).state;
  const skins = st.pending.map((p) => p.skin).filter(Boolean);
  add('unclaimed_weeks', st.pending.length === 2 && new Set(skins).size === skins.length,
    st.pending.length + ' unclaimed weeks kept, skins ' + (skins.join(', ') || 'none'));
}

// --- calibration from the config: how far a casual / regular / heavy player gets in the first week
{
  const cal = cfg.calibration || {};
  const out = [];
  let ok = Object.keys(cal).length >= 3;
  for (const [name, c] of Object.entries(cal)) {
    const finals = [];
    for (let s = 0; s < 31; s++) {
      let st = L.createState(cfg, name + s, T0);
      for (let i = 0; i < c.rounds_per_week; i++) st = play(st, name + s, i, T0 + HOUR + Math.floor(i * 6 * DAY / c.rounds_per_week)).state;
      finals.push(st.rank);
    }
    finals.sort((a, b) => a - b);
    const med = finals[15];
    let good = true;
    if (typeof c.rank_at_least === 'number') good = good && med >= c.rank_at_least;
    if (typeof c.rank_at_most === 'number') good = good && med <= c.rank_at_most;
    if (Array.isArray(c.rank_between)) good = good && med >= c.rank_between[0] && med <= c.rank_between[1];
    ok = ok && good;
    out.push(name + ' ' + c.rounds_per_week + ' rounds -> #' + med + (good ? '' : ' (outside target)'));
  }
  add('calibration', ok, out.length ? out.join('; ') : 'config.calibration needs casual, regular and heavy players');
}

console.log(JSON.stringify({ checks }));

// @ts-nocheck
// AdRewards.ts — the universal ad mechanism module (both boards; references/game-modules.md, user 2026-10-23).
// COPY THIS FILE UNCHANGED into the game (audit_game_modules.py compares its SHA-256 with the skill's copy).
// Plain JavaScript inside a .ts file: runs in Cocos 2.4 / 3.x and Node. Pure functions, no engine calls.
// The numbers of every game come from two files only: unlock_table.json (R = coins_per_ad, skin prices and bonuses)
// and level_plan.json (coins of each level; bonus levels already pay 3x there).
//
// Game glue:
//   result page:  r = resultReward(levelCoins, bonusPct(table, equippedIds)); show r.total and the "x2" ad button
//                 (pays r.doubled instead of r.total; "No thanks" pays r.total). Every level end / every endless run end.
//   home gift:    if (giftAvailable(gift)) show the 10-frame gift box; tap -> ad -> r = claimGift(gift, R, table, owned, cleared)
//                 -> grant r.coins, save r.state. After every level end / run end: gift = onRoundEnd(gift).
//   ad buttons:   g = createAdGate(); on tap: token = adGateStart(g); if (!token) return; play the ad; on any callback:
//                 if (adGateFinish(g, token, completed)) pay the reward once.

export const AD_REWARDS_VERSION = 2;
export const RESULT_AD_MULTIPLIER = 2;      // every level end / run end: watch an ad -> double
export const BONUS_LEVEL_MULTIPLIER = 3;    // bonus level coins in level_plan.json = 3x a normal level (x2 with the ad = 6x)
export const PRICE_STEPS = [1, 4, 10, 20];  // price gap to the previous skin, in R: common, rare, epic, legendary
export const FIRST_PRICE_R = 2;             // legacy-2r only: first skin for sale costs 2R
export const GIFT_SHARE = 0.1;              // home gift box: 10% of the next skin price ...
export const GIFT_PER_10_LEVELS = 0.5;      // ... plus 0.5R for every 10 levels cleared (endless: 10 runs)

function isNum(v) { return typeof v === 'number' && isFinite(v); }
export function round5(x) { return Math.max(5, Math.round(x / 5) * 5); }

function itemsOf(table) { return table && Array.isArray(table.items) ? table.items : (Array.isArray(table) ? table : []); }

// skin + background bonus of what is equipped (one of each), in percent
export function bonusPct(table, equippedIds) {
  const on = {};
  (equippedIds || []).forEach((id) => { on[id] = true; });
  let pct = 0;
  const seen = {};
  itemsOf(table).forEach((it) => {
    if (!on[it.id] || seen[it.group] || !it.bonus || it.bonus.type !== 'coins' || !isNum(it.bonus.pct)) return;
    seen[it.group] = true;
    pct += it.bonus.pct;
  });
  return pct;
}

// coins of one level end (or run end): bonus applied once, the ad doubles the total
export function resultReward(levelCoins, pct) {
  const base = Math.max(0, Math.round(levelCoins || 0));
  const total = Math.round(base * (1 + (pct || 0) / 100));
  return { base: base, skin_bonus: total - base, total: total, doubled: total * RESULT_AD_MULTIPLIER };
}

// the cheapest skin/background still for sale (coins), or the most expensive one when everything is owned
export function nextPrice(table, ownedIds) {
  const own = {};
  (ownedIds || []).forEach((id) => { own[id] = true; });
  const priced = itemsOf(table).filter((it) => it.unlock === 'coins' && isNum(it.coins) && it.coins > 0);
  if (!priced.length) return 0;
  const left = priced.filter((it) => !own[it.id]).map((it) => it.coins);
  return left.length ? Math.min.apply(null, left) : Math.max.apply(null, priced.map((it) => it.coins));
}

export function giftReward(R, table, ownedIds, cleared) {
  const p = nextPrice(table, ownedIds);
  return round5(Math.max(R, GIFT_SHARE * p) + GIFT_PER_10_LEVELS * R * Math.floor(Math.max(0, cleared || 0) / 10));
}

// one charge: full at the start, used by a claim, refilled after every level end / run end (never more than one)
export function createGift() { return { charges: 1 }; }
export function giftAvailable(state) { return !!state && state.charges > 0; }
export function onRoundEnd(state) { return { charges: 1 }; }
export function claimGift(state, R, table, ownedIds, cleared) {
  if (!giftAvailable(state)) return { coins: 0, state: { charges: 0 } };
  return { coins: giftReward(R, table, ownedIds, cleared), state: { charges: 0 } };
}

// one ad at a time, one reward per ad: double taps and repeated callbacks do nothing
export function createAdGate() { return { busy: false, paid: 0, sequence: 0, active: null }; }
export function adGateStart(g) {
  if (g.busy) return false;
  const token = Object.freeze({ request: ++g.sequence });
  g.busy = true;
  g.active = token;
  return token;
}
export function adGateFinish(g, token, completed) {
  if (!g.busy || !token || g.active !== token) return false;
  g.active = null;
  g.busy = false;
  if (completed !== true) return false;
  g.paid += 1;
  return true;
}

// New calls default to ordinary-levels. Pass the whole table to preserve its policy;
// an existing table without price_profile keeps legacy-2r. R remains the ad unit.
export function curvePrices(R, rarities, pricing = 'ordinary-levels') {
  const config = typeof pricing === 'string' ? { price_profile: pricing } : (pricing || {});
  const profile = config.price_profile || 'legacy-2r';
  if (profile !== 'ordinary-levels' && profile !== 'legacy-2r') throw new Error('unknown price_profile: ' + profile);
  if (profile === 'ordinary-levels') {
    const targets = config.price_level_targets || { common: 10, rare: 15, epic: 20, legendary: 25 };
    const base = config.normal_level_coins === undefined ? (config.coins_per_level === undefined ? R : config.coins_per_level) : config.normal_level_coins;
    const values = ['common', 'rare', 'epic', 'legendary'].map(r => targets[r]);
    if (!Number.isFinite(base) || base <= 0 || values.some((n, i) => !Number.isFinite(n) || n <= 0 || (i > 0 && n <= values[i - 1])))
      throw new Error('positive ordinary income and increasing tier targets required');
    return rarities.map(r => {
      if (targets[r] === undefined) throw new Error('unknown rarity: ' + r);
      return Math.max(1, Math.round(base * targets[r]));
    });
  }
  const rank = { common: 0, rare: 1, epic: 2, legendary: 3 };
  const out = [];
  rarities.forEach((r, i) => {
    out.push(i === 0 ? FIRST_PRICE_R * R : out[i - 1] + PRICE_STEPS[rank[r]] * R);
  });
  return out;
}

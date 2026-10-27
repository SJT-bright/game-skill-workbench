// @ts-nocheck
// AdRewards.ts — the universal ad mechanism module (both boards; references/game-modules.md, user 2026-10-23).
// COPY THIS FILE UNCHANGED into the game (audit_game_modules.py compares its SHA-256 with the skill's copy).
// Plain JavaScript inside a .ts file: runs in Cocos 2.4 / 3.x and Node. Pure functions, no engine calls.
// The numbers of every game come from two files only: unlock_table.json (B = normal_level_coins; coins_per_ad is already 5B; prices and bonuses)
// and level_plan.json (coins of each level; bonus levels already pay 3x there).
//
// Game glue:
//   result page:  r = resultReward(levelCoins, bonusPct(table, equippedIds)); show r.total and the "x2" ad button
//                 (pays r.doubled instead of r.total; "No thanks" pays r.total). Every level end / every endless run end.
//   home gift:    if (giftAvailable(gift)) show the 10-frame gift box; tap -> ad -> r = claimGift(gift, table.normal_level_coins, table, owned, cleared)
//                 -> grant r.coins, save r.state. Persist wallet + nextClaimAt atomically after completion; display giftRemainingMs. Rounds do not refill gifts.
//   ad buttons:   g = createAdGate(); on tap: token = adGateStart(g); if (!token) return; play the ad; on any callback:
//                 if (adGateFinish(g, token, completed)) pay the reward once.

export const AD_REWARDS_VERSION = 3;
export const RESULT_AD_MULTIPLIER = 2;      // every level end / run end: watch an ad -> double
export const BONUS_LEVEL_MULTIPLIER = 3;    // bonus level coins in level_plan.json = 3x a normal level (x2 with the ad = 6x)
export const PRICE_STEPS = [1, 4, 10, 20];  // price gap to the previous skin, in R: common, rare, epic, legendary
export const FIRST_PRICE_R = 2;             // legacy-2r only: first skin for sale costs 2R
export const GIFT_COOLDOWN_MS = 30 * 60 * 1000;
export const CURRENCY_AD_MULTIPLIER = 5;
export const GIFT_MULTIPLIER = 5;

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

// B is ordinary base income, never the already-multiplied coins_per_ad.
function baseCurrency(B) {
  if (!Number.isSafeInteger(B) || B <= 0 || !Number.isSafeInteger(50 * B)) throw new Error('positive safe integer ordinary base income required');
  return B;
}
export function currencyAdReward(B) { return CURRENCY_AD_MULTIPLIER * baseCurrency(B); }
export function giftReward(B) { return GIFT_MULTIPLIER * baseCurrency(B); }
function clock(now) { if (!Number.isSafeInteger(now) || now < 0) throw new Error('nonnegative millisecond clock required'); return now; }
function validGift(state) {
  return state && state.version === 3 && Number.isSafeInteger(state.nextClaimAt) && state.nextClaimAt >= 0 &&
    Number.isSafeInteger(state.lastClaimAt) && state.lastClaimAt >= 0 &&
    ((state.nextClaimAt === 0 && state.lastClaimAt === 0) || state.nextClaimAt === state.lastClaimAt + GIFT_COOLDOWN_MS);
}
export function createGift(now = Date.now()) { clock(now); return { version: 3, nextClaimAt: 0, lastClaimAt: 0 }; }
// Persist once on load. A spent legacy charge must not turn into a fresh claim.
export function migrateGift(state, now = Date.now()) {
  clock(now);
  if (validGift(state)) return { ...state };
  if (state && state.version === undefined && state.charges === 1) return createGift(now);
  return { version: 3, nextClaimAt: clock(now + GIFT_COOLDOWN_MS), lastClaimAt: now };
}
export function giftRemainingMs(state, now = Date.now()) {
  clock(now);
  return validGift(state) ? Math.max(0, state.nextClaimAt - Math.max(now, state.lastClaimAt)) : GIFT_COOLDOWN_MS;
}
export function giftAvailable(state, now = Date.now()) { return validGift(state) && giftRemainingMs(state, now) === 0; }
export function onRoundEnd(state) { return { ...state }; } // winning does not reset the 30-minute deadline
export function claimGift(state, B, table, ownedIds, cleared, now = Date.now()) {
  clock(now);
  if (!giftAvailable(state, now)) return { coins: 0, state: { ...state } };
  return { coins: giftReward(B), state: { version: 3, nextClaimAt: clock(now + GIFT_COOLDOWN_MS), lastClaimAt: now } };
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
// an existing table without price_profile keeps legacy-2r. Pass the saved table: its B is distinct from coins_per_ad.
export function curvePrices(R, rarities, pricing = 'ordinary-levels') {
  const config = typeof pricing === 'string' ? { price_profile: pricing } : (pricing || {});
  const profile = config.price_profile || 'legacy-2r';
  if (profile !== 'ordinary-levels' && profile !== 'legacy-2r') throw new Error('unknown price_profile: ' + profile);
  if (profile === 'ordinary-levels') {
    const targets = config.price_level_targets || { common: 10, rare: 20, epic: 30, legendary: 40, limited: 50 };
    const base = config.normal_level_coins === undefined ? (config.coins_per_level === undefined ? R : config.coins_per_level) : config.normal_level_coins;
    const values = ['common', 'rare', 'epic', 'legendary'].map(r => targets[r]);
    if (targets.limited !== undefined) values.push(targets.limited);
    if (config.economy_policy === 'normal-10-50.v1' && ['common','rare','epic','legendary','limited'].some((r,i)=>targets[r]!==10*(i+1))) throw new Error('current economy requires 10/20/30/40/50');
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

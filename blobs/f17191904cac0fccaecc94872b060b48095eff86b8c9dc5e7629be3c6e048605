// Simulates the universal ad mechanism with the game's own AdRewards copy and its unlock_table.json
// (references/game-modules.md, user 2026-10-23). Run by audit_game_modules.py; prints one JSON object.
//   node modules_harness.mjs <AdRewards.mjs> <unlock_table.json | -> <R>
import fs from 'fs';
import { pathToFileURL } from 'url';

const [modPath, tablePath, rArg] = process.argv.slice(2);
const M = await import(pathToFileURL(modPath).href);
const table = tablePath && tablePath !== '-' ? JSON.parse(fs.readFileSync(tablePath, 'utf8')) : { items: [] };
const R = Number(rArg) || 50;
const checks = [];
const add = (id, passed, detail) => checks.push({ id, passed: !!passed, detail });

{ // every level end / run end: the ad doubles everything once, the skin bonus is counted once
  const a = M.resultReward(R, 0), b = M.resultReward(R, 18), c = M.resultReward(0, 30);
  const ok = a.doubled === 2 * R && a.total === R && b.total === Math.round(R * 1.18) && b.doubled === 2 * b.total && c.doubled === 0;
  add('result_double', ok, 'level ' + R + ' -> ' + a.total + ' / x2 ' + a.doubled + '; +18% -> ' + b.total + ' / x2 ' + b.doubled);
}
{ // bonus level: 3x a normal level, the ad doubles again -> 6x
  const r = M.resultReward(M.BONUS_LEVEL_MULTIPLIER * R, 0);
  add('bonus_level_6x', M.BONUS_LEVEL_MULTIPLIER === 3 && r.doubled === 6 * R, 'bonus level ' + r.total + ', with the ad ' + r.doubled + ' (6R = ' + 6 * R + ')');
}
{ // skin + background bonus: one of each group
  const items = (table.items || []).filter((it) => it.bonus && it.bonus.type === 'coins');
  const bySkin = items.filter((it) => it.group === 'skin'), byBg = items.filter((it) => it.group === 'background');
  let ok = true, detail = 'no skins';
  if (bySkin.length) {
    const two = bySkin.slice(0, 2).map((it) => it.id);
    const pct = M.bonusPct(table, two.concat(byBg.slice(0, 1).map((it) => it.id)));
    const want = bySkin[0].bonus.pct + (byBg.length ? byBg[0].bonus.pct : 0);
    ok = pct === want;
    detail = 'two skins + one background equipped -> +' + pct + '% (one skin counts: ' + want + '%)';
  }
  add('bonus_once_per_group', ok, detail);
}
{ // home gift box grows with levels cleared and with skins bought, never below R
  const priced = (table.items || []).filter((it) => it.unlock === 'coins' && it.coins > 0).sort((a, b) => a.coins - b.coins);
  const byLevel = [0, 9, 10, 20, 35, 70].map((n) => M.giftReward(R, table, [], n));
  const lvOk = byLevel.every((v, i) => i === 0 || v >= byLevel[i - 1]) && byLevel[5] > byLevel[0] && byLevel[0] >= R;
  add('gift_grows_with_levels', lvOk, 'gift at 0/9/10/20/35/70 levels: ' + byLevel.join('/'));
  if (priced.length) {
    const owned = [], seq = [M.giftReward(R, table, owned, 0)];
    priced.forEach((it) => { owned.push(it.id); seq.push(M.giftReward(R, table, owned, 0)); });
    const ok = seq.every((v, i) => i === 0 || v >= seq[i - 1]) && seq[seq.length - 1] > seq[0];
    add('gift_grows_with_skins', ok, 'gift after buying 0..' + priced.length + ' skins: ' + seq.filter((v, i) => i % 4 === 0 || i === seq.length - 1).join('/'));
    const top = M.nextPrice(table, priced.map((it) => it.id));
    add('next_price_all_owned', top === priced[priced.length - 1].coins, 'everything owned -> next price ' + top);
  }
}
{ // one charge, used by a claim, refilled after a level end, never stacked
  let g = M.createGift();
  const a = M.claimGift(g, R, table, [], 0); g = a.state;
  const b = M.claimGift(g, R, table, [], 0);
  g = M.onRoundEnd(M.onRoundEnd(g));
  const c = M.claimGift(g, R, table, [], 1); g = c.state;
  const d = M.claimGift(g, R, table, [], 1);
  const ok = a.coins >= R && b.coins === 0 && c.coins > 0 && d.coins === 0;
  add('gift_once_per_round', ok, 'claim ' + a.coins + ', again ' + b.coins + ', after two level ends ' + c.coins + ' then ' + d.coins);
}
{ // ad buttons: a double tap plays one ad, repeated callbacks pay once, cancel pays nothing
  const g = M.createAdGate();
  const first = M.adGateStart(g), second = M.adGateStart(g);
  const pay1 = M.adGateFinish(g, first, true), pay2 = M.adGateFinish(g, first, true);
  const again = M.adGateStart(g), cancel = M.adGateFinish(g, again, false);
  const ok = first && !second && pay1 && !pay2 && again && !cancel && g.paid === 1;
  add('ad_gate_single_fire', ok, 'tap ' + first + ', double tap ' + second + ', paid ' + pay1 + '/' + pay2 + ', cancel pays ' + cancel);
}
{ // Late and forged callbacks cannot close or pay a newer request, including after cancellation.
  const g = M.createAdGate(), h = M.createAdGate();
  const old = M.adGateStart(g);
  M.adGateFinish(g, old, false);
  const current = M.adGateStart(g), foreign = M.adGateStart(h);
  const stale = M.adGateFinish(g, old, true);
  const forged = M.adGateFinish(g, { request: current.request }, true);
  const wrongGate = M.adGateFinish(g, foreign, true);
  const remainedBusy = g.busy && !M.adGateStart(g);
  const paid = M.adGateFinish(g, current, true);
  const duplicate = M.adGateFinish(g, current, true);
  add('ad_gate_stale_callbacks', !stale && !forged && !wrongGate && remainedBusy && paid && !duplicate && g.paid === 1,
      'stale/cross-gate/forged callbacks ignored; only current identity pays once and releases gate');
}
{ // the price curve the table must follow
  const p = M.curvePrices(R, ['common', 'common', 'rare', 'rare', 'epic', 'legendary'], 'legacy-2r');
  add('price_curve', p.join(',') === [2, 3, 7, 11, 21, 41].map((k) => k * R).join(','), 'curve for R=' + R + ': ' + p.join(', '));
}
{
  const tiers = ['common', 'rare', 'epic', 'legendary'];
  const p = M.curvePrices(R, tiers);
  add('ordinary_price_profile', p.join(',') === [10, 15, 20, 25].map(n => n * R).join(','), 'default ordinary-level targets');
  const custom = M.curvePrices(R, tiers, {price_profile: 'ordinary-levels', normal_level_coins: 30, price_level_targets: {common: 8, rare: 12, epic: 16, legendary: 20}});
  add('ordinary_price_parameters', custom.join(',') === '240,360,480,600', 'ordinary income independent of ad unit');
  add('unmarked_price_compatibility', M.curvePrices(R, tiers, {}).join(',') === M.curvePrices(R, tiers, 'legacy-2r').join(','), 'unmarked old tables retain legacy');
}
console.log(JSON.stringify({ checks }));

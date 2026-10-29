// Simulates the universal ad mechanism with the game's own AdRewards copy and its unlock_table.json
// (remake-core/references/game-modules.md, user 2026-10-23). Run by audit_game_modules.py; prints one JSON object.
//   node modules_harness.mjs <AdRewards.mjs> <unlock_table.json | -> <R>
import fs from 'fs';
import { pathToFileURL } from 'url';

const [modPath, tablePath, rArg] = process.argv.slice(2);
const M = await import(pathToFileURL(modPath).href);
const table = tablePath && tablePath !== '-' ? JSON.parse(fs.readFileSync(tablePath, 'utf8')) : { items: [] };
const INPUT_R = Number(rArg) || 50;
const B = table.normal_level_coins || table.coins_per_level || INPUT_R;
const R = B;
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
{ // Gifts and separate currency ads each grant 5B; no progress/price inflation.
  const values = [0,10,70,1000].map(n=>M.giftReward(B,table,[],n));
  add('gift_fixed_5x',values.every(v=>v===5*B) && M.giftReward(B,{items:[]},[],0)===5*B,'fixed 5 ordinary rewards regardless of price/progress');
  add('currency_ad_5x',M.currencyAdReward(B)===5*B,'independent coin ad is not the result multiplier');
  const now=1_000_000, cooldown=1_800_000;
  const a=M.claimGift(M.createGift(now),B,table,[],0,now), state=a.state;
  const repeat=M.claimGift(state,B,table,[],0,now);
  const before=M.claimGift(state,B,table,[],70,now+cooldown-1);
  const next=M.claimGift(state,B,table,[],70,now+cooldown);
  add('gift_cooldown_boundary',M.GIFT_COOLDOWN_MS===cooldown && a.coins===5*B && repeat.coins===0 && before.coins===0 && next.coins===5*B,'ready at exactly 30 minutes after successful claim');
  add('gift_round_cannot_reset',JSON.stringify(M.onRoundEnd(M.onRoundEnd(state)))===JSON.stringify(state),'winning does not refill gift');
  add('gift_corrupt_deadline_refused',!M.giftAvailable({...state,nextClaimAt:0},now) && !M.giftAvailable({...state,nextClaimAt:state.nextClaimAt-1},now),'bad persisted deadlines cannot grant a fresh gift');
  const loaded=JSON.parse(JSON.stringify(state));
  add('gift_reload_countdown',M.giftRemainingMs(loaded,now+600_000)===1_200_000 && !M.giftAvailable(loaded,now-60_000),'persisted deadline survives reload/clock rollback');
  const late=M.claimGift(loaded,B,table,[],100,now+10*cooldown);
  add('gift_no_accumulation',late.coins===5*B && !M.giftAvailable(late.state,now+10*cooldown),'long absence grants one gift, no stack');
  add('gift_legacy_migration',!M.giftAvailable(M.migrateGift({charges:0},now),now) && M.giftAvailable(M.migrateGift({charges:1},now),now),'spent old state cannot become a free claim');
  const cancelled=M.createAdGate(), token=M.adGateStart(cancelled);
  const allowed=M.adGateFinish(cancelled,token,false);
  add('gift_cancel_keeps_eligibility',!allowed && M.giftAvailable(M.createGift(now),now),'cancel/failure must not call claimGift or start its clock');
  const top=M.nextPrice(table, (table.items||[]).map(x=>x.id));
  add('next_price_all_owned',top>=0,'price helper remains usable independently of fixed gifts');
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
  const tiers = ['common', 'rare', 'epic', 'legendary','limited'];
  const p = M.curvePrices(R, tiers);
  add('ordinary_price_profile', p.join(',') === [10,20,30,40,50].map(n => n * R).join(','), 'default ordinary-level targets');
  const custom = M.curvePrices(R, tiers, {price_profile: 'ordinary-levels', normal_level_coins: 30, price_level_targets: {common: 10, rare: 20, epic: 30, legendary: 40,limited:50}});
  add('ordinary_price_parameters', custom.join(',') === '300,600,900,1200,1500', 'ordinary income independent of ad unit');
  add('unmarked_price_compatibility', M.curvePrices(R, tiers.slice(0,4), {}).join(',') === M.curvePrices(R, tiers.slice(0,4), 'legacy-2r').join(','), 'unmarked old tables retain legacy');
}
console.log(JSON.stringify({ checks }));

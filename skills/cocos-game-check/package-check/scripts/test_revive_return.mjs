import assert from 'node:assert/strict';
import test from 'node:test';
import {checkReviveReturn, reviveContractProblem} from './runtime_regression/revive_return.mjs';

const spec = {
  run_id_js: 'return run.id', reward_js: 'return run.remaining',
  cancel_js: 'return run.failed', after_js: 'return game.visible',
  after_visible: ['world controls'],
};
const action = {probe: {tap: 'tile'}, state_js: 'return board.remaining'};
test('revive needs observations and a non-optional real action', () => {
  assert.equal(reviveContractProblem(spec, action), null);
  for (const key of Object.keys(spec)) {
    assert.ok(reviveContractProblem({...spec, [key]: null}, action), key);
  }
  for (const probe of [{js: 'return true'}, {tap: 'tile', optional: true}, {drag_js: []}]) {
    assert.ok(reviveContractProblem(spec, {...action, probe}));
  }
});
const io = {
  runId: () => 3, restored: () => true, visible: () => true,
  shot: label => label + '.png', play: () => ({ok: true, state: [54, 53]}),
};
for (const [scenario, changes] of [
  ['new game loaded', {runId: () => 4}],
  ['only phase restored; world still covered', {restored: () => false}],
  ['HUD missing, covered or off screen', {visible: () => false}],
  ['no actionable tile', {play: () => ({ok: false})}],
  ['tap has no effect', {play: () => ({ok: true, state: [54, 54]})}],
  ['game reading throws after input', {play: () => ({ok: true, state: [54, {adapterError: 'invalid'}]})}],
  ['restored screenshot missing', {shot: () => null}],
  ['next-action screenshot missing', {shot: label => label === 'restored' ? 'a.png' : null}],
]) {
  test(scenario, async () => assert.equal((await checkReviveReturn(spec, 3, {...io, ...changes})).ok, false));
}
test('restoration is observed before input; both frames remain available to review', async () => {
  const history = [];
  const wrap = Object.fromEntries(Object.entries(io).map(([name, fn]) => [name, (...args) => {
    history.push(name === 'shot' ? args[0] : name);
    return fn(...args);
  }]));
  const row = await checkReviveReturn(spec, 3, wrap);
  assert.equal(row.ok, true);
  assert.deepEqual(history, ['runId', 'restored', 'restored', 'visible', 'play', 'next-action']);
  assert.ok(row.review);
});

import assert from 'node:assert/strict';
import test from 'node:test';
import {isManualRevive} from './runtime_regression/layout_rules.mjs';

test('only rewarded revive routes are excluded from generic button discovery', () => {
  const adapter = {_manual_revive_paths: ['*/Defeat/BtnVideo']};
  assert.equal(isManualRevive('Canvas/Defeat/BtnVideo#1', 'Video', adapter), true);
  assert.equal(isManualRevive('Canvas/Overlay/Btn', 'WATCH AD TO REVIVE', {}), true);
  assert.equal(isManualRevive('Canvas/RevivePopup/WatchAd', 'Watch', {}), true);
  assert.equal(isManualRevive('Canvas/RevivePopup/FreeRetry', 'Retry', {}), false);
  assert.equal(isManualRevive('Canvas/Revive', 'REVIVE', {}), false);
  assert.equal(isManualRevive('Canvas/Revive', 'WATCH VIDEO TO REVIVE', {}), true);
  assert.equal(isManualRevive('Canvas/Gift/BtnVideo', 'WATCH AD', adapter), false);
  assert.equal(isManualRevive('Canvas/Result/DoubleReward', 'WATCH AD X2', adapter), false);
});

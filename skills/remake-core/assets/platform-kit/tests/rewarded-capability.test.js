'use strict';
// Service-level capability contract. No game, browser, timers matrix or reward-UI replay.
// Default: current 2.4 source and generated 3.x plugin. Optional argument: one module/plugin file.
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const crypto = require('crypto');
const assert = require('assert/strict');

const kit = path.resolve(__dirname, '..');
const files = process.argv[2] ? [path.resolve(process.argv[2])] : [
  path.join(kit, 'assets/tiktok-platform/RewardedService.js'),
  path.join(kit, 'plugins-3x/RewardedService.plugin.js')
];

const scenarios = [
  {id: 'TTMinis_callable_receiver', expected: 'primary', setup(w) { w.context.TTMinis = {game: w.sdk('primary', true)}; }},
  {id: 'tt_only', expected: 'tt', setup(w) { w.context.tt = w.sdk('tt', true); }},
  {id: 'wx_compatibility_only', expected: 'wx', setup(w) { w.context.wx = w.sdk('wx', true); }},
  {id: 'TTMinis_null_then_tt', expected: 'tt', setup(w) { w.context.TTMinis = null; w.context.tt = w.sdk('tt', true); }},
  {id: 'empty_first_then_tt', expected: 'tt', setup(w) { w.context.TTMinis = {game: {}}; w.context.tt = w.sdk('tt', true); }},
  {id: 'unrelated_method_first_then_tt', expected: 'tt', setup(w) { w.context.TTMinis = {game: {getSystemInfoSync() { return {}; }}}; w.context.tt = w.sdk('tt', true); }},
  {id: 'canIUse_missing', expected: 'primary', setup(w) { w.context.TTMinis = {game: w.sdk('primary', 'missing')}; }},
  {id: 'canIUse_undefined', expected: 'primary', setup(w) { w.context.TTMinis = {game: w.sdk('primary', undefined)}; }},
  {id: 'explicit_false_no_factory_call', expected: null, setup(w) { w.context.TTMinis = {game: w.sdk('primary', false)}; }},
  {id: 'explicit_false_then_tt', expected: 'tt', setup(w) { w.context.TTMinis = {game: w.sdk('primary', false)}; w.context.tt = w.sdk('tt', true); }},
  {id: 'canIUse_throw_no_factory_call', expected: null, setup(w) { w.context.TTMinis = {game: w.sdk('primary', 'throw')}; }},
  {id: 'canIUse_throw_then_tt', expected: 'tt', setup(w) { w.context.TTMinis = {game: w.sdk('primary', 'throw')}; w.context.tt = w.sdk('tt', true); }},
  {id: 'all_candidates_missing_method', expected: null, setup(w) { Object.assign(w.context, {TTMinis: {game: {}}, tt: {}, wx: {}}); }},
  {id: 'no_sdk_globals', expected: null, setup() {}},
  {id: 'injected_sdk_still_checks_false', expected: null, setup(w) { w.inject = w.sdk('injected', false); }},
  {id: 'injected_sdk_accepts_undefined', expected: 'injected', setup(w) { w.inject = w.sdk('injected', undefined); }},
  {id: 'one_cancel_representative', expected: 'primary', completed: false, setup(w) { w.context.TTMinis = {game: w.sdk('primary', undefined)}; }}
];

function world() {
  const w = {created: [], instances: [], injectedMethods: [], context: {Promise}};
  w.sdk = function (name, capability) {
    const sdk = {
      createRewardedVideoAd(options) {
        assert.equal(this, sdk, 'native factory receiver must be preserved');
        assert.equal(options.adUnitId, 'capability-fixture-unit');
        w.created.push(name);
        let close = null, error = null;
        const instance = {
          onClose(fn) { close = fn; }, offClose(fn) { if (close === fn) close = null; },
          onError(fn) { error = fn; }, offError(fn) { if (error === fn) error = null; },
          show() { return Promise.resolve(); }
        };
        w.instances.push({close(ended) { if (close) close({isEnded: ended}); }, bound() { return !!(close || error); }});
        return instance;
      }
    };
    if (capability !== 'missing') sdk.canIUse = function (method) {
      assert.equal(this, sdk, 'capability receiver must be preserved');
      assert.equal(method, 'createRewardedVideoAd');
      if (capability === 'throw') throw new Error('fixture unsupported capability query');
      return capability;
    };
    return sdk;
  };
  return w;
}

function load(source, file, w) {
  const config = {getAdUnitId() { return 'capability-fixture-unit'; }};
  if (file.endsWith('.plugin.js')) {
    w.context.TikTokKit = {PlatformConfig: config};
    vm.runInNewContext(source, w.context, {filename: file});
    return w.context.TikTokKit.RewardedService;
  }
  w.context.module = {exports: {}};
  w.context.require = function (id) { assert.equal(id, './PlatformConfig'); return config; };
  vm.runInNewContext(source, w.context, {filename: file});
  return w.context.module.exports;
}

async function contract(source, file) {
  const results = [];
  for (const row of scenarios) {
    const w = world();
    let service;
    try {
      row.setup(w);
      const Service = load(source, file, w);
      const options = {autoPoll: false};
      if (w.inject) options.getSDK = function (method) { w.injectedMethods.push(method); return w.inject; };
      service = new Service(options);
      const pending = service.request({placementKey: 'energy'});
      await Promise.resolve();
      if (w.instances[0]) w.instances[0].close(row.completed !== false);
      let timer;
      const timeout = new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('capability fixture did not settle')), 500); });
      let result;
      try { result = await Promise.race([pending, timeout]); } finally { clearTimeout(timer); }
      assert.deepEqual(w.created, row.expected === null ? [] : [row.expected], 'selected callable namespace');
      assert.equal(result.status, row.expected === null ? 'unsupported' : row.completed === false ? 'cancelled' : 'completed');
      assert.equal(result.rewarded, row.expected !== null && row.completed !== false);
      assert(w.instances.every(ad => !ad.bound()), 'terminal result must release listeners');
      if (w.inject) assert.deepEqual(w.injectedMethods, ['createRewardedVideoAd']);
      results.push({id: row.id, passed: true});
    } catch (error) {
      results.push({id: row.id, passed: false, error: String(error.message || error)});
    } finally {
      if (service) service.dispose();
    }
  }
  return results;
}

function mutate(source, kind) {
  if (kind === 'single_namespace') {
    const matcher = /function rootSDK\(method\) \{[\s\S]*?\n\}/;
    assert(matcher.test(source), 'negative control needs actual default resolver');
    return source.replace(matcher, "function rootSDK(method) {\n  return typeof TTMinis !== 'undefined' && TTMinis && TTMinis.game ? TTMinis.game : null;\n}");
  }
  const changed = source.replace(/candidate\.canIUse\(method\) === false/g, 'candidate.canIUse(method) !== true')
    .replace(/sdk\.canIUse\('createRewardedVideoAd'\) === false/g, "sdk.canIUse('createRewardedVideoAd') !== true");
  assert.notEqual(changed, source, 'negative control needs actual non-strict capability predicate');
  return changed;
}

(async function () {
  const targets = [];
  for (const file of files) {
    const source = fs.readFileSync(file, 'utf8');
    const results = await contract(source, file);
    const controls = [];
    for (const [kind, mustFail] of [['single_namespace', 'tt_only'], ['strict_true', 'canIUse_undefined']]) {
      try {
        const negative = await contract(mutate(source, kind), file);
        const failures = negative.filter(row => !row.passed);
        controls.push({id: kind, detected: failures.some(row => row.id === mustFail), failures});
      } catch (error) {
        controls.push({id: kind, detected: false, error: String(error.message || error)});
      }
    }
    targets.push({file, source_sha256: crypto.createHash('sha256').update(source).digest('hex'),
      cases: results, negative_controls: controls,
      passed: results.every(row => row.passed) && controls.every(row => row.detected)});
  }
  const passed = targets.every(row => row.passed);
  console.log(JSON.stringify({schema: 'rewarded-capability-contract.v1', passed,
    scope: 'Current service default SDK resolver and two independent negative controls; no game/browser replay.', targets}, null, 2));
  if (!passed) process.exitCode = 1;
})().catch(error => { console.error(error); process.exitCode = 1; });

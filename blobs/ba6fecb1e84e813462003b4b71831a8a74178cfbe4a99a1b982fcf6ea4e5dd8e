// No browser or filesystem writes. The same phone has the same CSS size and DPR in CDP and both SDK hosts.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
globalThis.CFG = {lib: new URL('./runtime_regression/lib.mjs', import.meta.url).href};
const {DEVICES, setViewport} = await import('./runtime_regression/gates.mjs');
const expected = {iphone14: {width: 390, height: 844, dpr: 3}, se: {width: 375, height: 667, dpr: 2}};
const hosts = ['./ad_regression/host.js', './runtime_regression/host3x/host.js'].map(relative => {
  const source = fs.readFileSync(new URL(relative, import.meta.url), 'utf8');
  const match = source.match(/(?:var|const)\s+DEVS\s*=\s*(\{[\s\S]*?\n\s*\});/);
  assert(match, relative + ' must expose the actual phone profiles');
  return {relative, profiles: vm.runInNewContext('(' + match[1] + ')')};
});
const results = [];
for (const [name, want] of Object.entries(expected)) {
  const calls = [];
  await setViewport({cdp: async (method, params) => {calls.push({method, params});}}, name);
  assert.deepEqual(calls, [
    {method: 'Emulation.setDeviceMetricsOverride', params: {width: want.width, height: want.height, deviceScaleFactor: want.dpr, mobile: false}},
    {method: 'Emulation.setTouchEmulationEnabled', params: {enabled: false}},
  ], name + ' must preserve CSS dimensions and mouse input while matching the physical DPR');
  assert.equal(DEVICES[name].dpr, want.dpr);
  for (const {relative, profiles} of hosts) {
    const sdk = profiles[name];
    assert.deepEqual({width: sdk.W, height: sdk.H, dpr: sdk.pr}, want, name + ' / ' + relative);
    assert.notEqual(1, sdk.pr, 'negative control: the former fixed CDP1 mismatches this SDK profile');
  }
  results.push({name, passed: true, css: [want.width, want.height], dpr: want.dpr});
}
console.log(JSON.stringify({passed: true, profiles: results, sdk_hosts_checked: hosts.length}));

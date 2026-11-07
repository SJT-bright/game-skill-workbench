'use strict';
const assert = require('node:assert/strict');
const MissionFlow = require('../assets/tiktok-platform/MissionFlow');
const SaveStore = require('../assets/tiktok-platform/SaveStore');

const settle = () => new Promise(resolve => setImmediate(resolve));
const apis = {profile: 'getEntranceMissionReward', shortcut: 'getShortcutMissionReward'};

function setUp(launch, current = launch, storage = new Map()) {
  const calls = [];
  const events = new Set();
  const shown = [];
  const saved = new SaveStore({coins: 0}, {key: 'entry', login: false,
    storage: {getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value)}});
  assert(saved.load().ok);
  const sdk = {getLaunchOptionsSync: () => ({scene: launch}), getEnterOptionsSync: () => ({scene: current}),
    onShow: fn => events.add(fn), offShow: fn => events.delete(fn), canIUse: () => undefined};
  for (const api of [...Object.values(apis), 'startEntranceMission', 'addShortcut']) {
    sdk[api] = opts => calls.push({api, opts});
  }
  global.TTMinis = {game: sdk};
  const create = () => new MissionFlow({store: saved, reward: (_kind, data) => { data.coins += 50; },
    render: state => { if (state.message) shown.push(state.message); }});
  const flow = create();
  return {flow, calls, shown, saved, events, storage, create, show: (scene) => {
    current = scene || current;
    for (const callback of events) callback(scene ? {scene} : {});
  }};
}
function callsFor(t) {
  return t.calls.map(row => row.api);
}
function dispose(t) {
  t.flow.dispose();
  delete global.TTMinis;
}

(async () => {
  for (const [scene, kind] of [['center', 'profile'], ['desktop_shortcut', 'shortcut']]) {
    const t = setUp(scene);
    try {
      const first = t.flow.startEntryTracking();
      t.flow.startEntryTracking();
      await settle();
      assert.deepEqual(callsFor(t), [apis[kind]]);
      t.calls[0].opts.success({canReceiveReward: true});
      t.calls[0].opts.success({canReceiveReward: true});
      await first;
      assert(t.saved.isClaimed(kind));
      assert.equal(t.saved.get().coins, 50);
      assert.deepEqual(t.shown, []);
      t.show(scene);
      assert.equal(t.calls.length, 1);
    } finally { dispose(t); }
    assert.equal(t.events.size, 0);
    const restarted = setUp(scene, scene, t.storage);
    try {
      await restarted.flow.startEntryTracking();
      assert(restarted.saved.isClaimed(kind));
      assert.equal(restarted.saved.get().coins, 50);
      assert.equal(restarted.calls.length, 0);
    } finally { dispose(restarted); }
  }

  const t = setUp('scan_qrcode');
  try {
    await t.flow.startEntryTracking();
    t.flow.open('profile', {navigate: true});
    assert.deepEqual(callsFor(t), ['startEntranceMission']);
    t.calls[0].opts.success({});
    await settle();
    for (const scene of ['search', 'ads', 'minis_link', null]) t.show(scene);
    t.flow.onShow();
    assert.deepEqual(callsFor(t), ['startEntranceMission']);
    const before = t.shown.length;
    t.show('center');
    t.show('center');
    assert.deepEqual(callsFor(t), ['startEntranceMission', apis.profile, apis.profile]);
    t.calls[1].opts.success({canReceiveReward: true});
    t.calls[2].opts.success({canReceiveReward: false});
    await settle();
    assert.equal(t.saved.get().coins, 0);
    assert(!t.saved.isClaimed('profile'));
    assert.equal(t.shown.length, before);
    t.show(null);
    t.flow.onShow();
    assert.equal(t.calls.length, 3, 'an incomplete payload must not reuse a stale center');
    t.show('center');
    t.calls[3].opts.success({canReceiveReward: true});
    await settle();
    assert.equal(t.saved.get().coins, 50);
    assert(t.saved.isClaimed('profile'));
    assert.equal(t.shown.length, before);
  } finally { dispose(t); }

  const early = setUp('scan_qrcode', 'center');
  try {
    early.flow.startEntryTracking();
    await settle();
    assert.deepEqual(callsFor(early), [apis.profile], 'entry while the first scene was loading');
    early.calls[0].opts.success({canReceiveReward: false});
    await settle();
    early.flow.dispose();
    const recreated = early.create();
    try {
      await recreated.startEntryTracking();
      assert.equal(early.calls.length, 1, 'a rebuilt home does not replay the startup entry');
    } finally { recreated.dispose(); }
  } finally { dispose(early); }
  console.log('PASS cold entries, restarts, ordinary foreground, late response, startup re-entry, and listener ownership');
})().catch(error => { console.error(error); process.exitCode = 1; });

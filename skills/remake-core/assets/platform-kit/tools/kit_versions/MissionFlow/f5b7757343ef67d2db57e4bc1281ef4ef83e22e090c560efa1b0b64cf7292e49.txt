'use strict';
// TikTok Platform Kit v1 - logic of the two home entries (Add to Home Screen, Profile Revisit). Copy unchanged.
// It draws nothing. The game owns the art and calls render(view) output into its own panel.
//
//   var flow = new MissionFlow({
//     store: save,                                   // SaveStore of this game (coins live in the same save)
//     reward: function (kind, draft) { draft.coins += 25; },   // edit the draft only; v7.7: omit it to pay
//                                                    // PlatformConfig.growthReward() (5B) into draft.coins
//     rewardText: {shortcut: '+25 Coins', profile: '+25 Coins'},
//     render: function (view) { ...update the panel from view... },
//     onGranted: function (kind, data) { ...refresh the top bar from data... }
//   });
//   home icon tap        -> flow.open('shortcut' | 'profile')
//   panel main button    -> view.action === 'start' ? flow.start() : flow.check()
//   panel close (X)      -> flow.close()
//   when the wallet is ready -> flow.startEntryTracking() (once, before waiting for any entry button)
//   every frame          -> flow.tick()
//   home scene destroyed -> flow.dispose()
//
// Guarantees (each one is a real bug from an earlier game):
//  - Only a confirmed sidebar or shortcut entry starts a background check. A late superseded answer is dropped.
//  - Taps during a manual check are merged; failures in a player-opened reward panel keep a visible result.
//  - Automatic entry checks update the wallet without opening a panel or displaying a notice.
//  - A navigation answer never overwrites a newer check result.
//  - Reward + "claimed" flag are saved in ONE write; a failed save pays nothing and can be retried.
//  - Only canReceiveReward === true pays, once per entry per save.
var TikTokMissionService = require('./TikTokMissionService');

var TEXT = {
  intro_shortcut: 'Add this game to your home screen, open it from the new icon, then come back for your reward.',
  intro_profile: 'Open your TikTok Profile, open this game from the sidebar, then come back for your reward.',
  opening: 'Opening TikTok...',
  navigated: 'Now open the game from that entry, then tap CHECK REWARD.',
  checking: 'Checking your reward...',
  wait: 'Please wait for the current request.',
  granted: 'Reward received: ',
  claimed: 'Reward already collected.',
  saveFailed: 'Could not save your reward. Please try again.',
  notReady: 'Your reward is not ready yet.',
  preview: 'Available in TikTok.'
};
var KINDS = {shortcut: true, profile: true};

// Same lookup order as TikTokMissionService.js (TTMinis.game, then tt, then wx). v1.2: a runtime that
// only exposes tt (Mabel's Meadow r7/r8) used to show the LOCAL PREVIEW text inside TikTok.
// 简化.11.3: a runtime counts when it has canIUse or one of the four mission methods (canIUse is not required).
function sdkCandidates() {
  return [
    typeof TTMinis !== 'undefined' && TTMinis && TTMinis.game,
    typeof tt !== 'undefined' && tt,
    typeof wx !== 'undefined' && wx
  ];
}

function hasNativeSDK() {
  var candidates = sdkCandidates();
  var names = ['canIUse', 'addShortcut', 'startEntranceMission', 'getShortcutMissionReward', 'getEntranceMissionReward'];
  for (var i = 0; i < candidates.length; i++) {
    var c = candidates[i];
    if (!c || (typeof c !== 'object' && typeof c !== 'function')) continue;
    for (var j = 0; j < names.length; j++) if (typeof c[names[j]] === 'function') return true;
  }
  return false;
}

// A home component can be rebuilt during the same runtime. The launch entry belongs to the runtime.
var observedStartup = new WeakSet();
function readEntry(sdk, method) {
  if (typeof sdk[method] !== 'function') return null;
  try {
    var entry = sdk[method]();
    if (entry && typeof entry.scene === 'string' && entry.scene) return entry;
  } catch (_) {}
  return null;
}

function initialEntry(candidates) {
  for (var i = 0; i < candidates.length; i++) {
    var sdk = candidates[i];
    if (!sdk || (typeof sdk !== 'object' && typeof sdk !== 'function')) continue;
    if (observedStartup.has(sdk)) return null;
    // The current entry can already be newer than launch while the engine loads the first home.
    var entry = readEntry(sdk, 'getEnterOptionsSync') || readEntry(sdk, 'getLaunchOptionsSync');
    if (entry) {
      observedStartup.add(sdk);
      return entry;
    }
  }
  return null;
}

function MissionFlow(options) {
  options = options || {};
  var copy = {};
  for (var key in options) if (Object.prototype.hasOwnProperty.call(options, key)) copy[key] = options[key];
  options = copy;
  // v7.7 (kit 2.0): reward omitted = the fixed growth reward of PlatformConfig.js (5B in this game's
  // currency, Saul 2026-10-29), added to draft.coins; reward text '+N Coins'. growthReward() throws until
  // normalLevelCoins is set, so a forgotten B pays nothing (SaveStore.update refuses the write).
  if (options.store && options.reward === undefined && typeof options.render === 'function') {
    var growth = options.config || require('./PlatformConfig');
    options.reward = function (kind, draft) { draft.coins = (Number(draft.coins) || 0) + growth.growthReward(); };
    if (!options.rewardText) {
      var amount = '';
      try { amount = '+' + growth.growthReward() + ' Coins'; } catch (_) {}
      options.rewardText = {shortcut: amount, profile: amount};
    }
  }
  if (!options.store || typeof options.reward !== 'function' || typeof options.render !== 'function') {
    throw new Error('MissionFlow needs store, reward(kind, draft) and render(view)');
  }
  this.store = options.store;
  this.reward = options.reward;
  this.renderView = options.render;
  this.onGranted = options.onGranted || null;
  this.rewardText = options.rewardText || {shortcut: '', profile: ''};
  this.ownsMissions = !options.missions;
  // Own timer on by default, so a check still ends if the game forgets to call tick().
  this.serviceOptions = options.missionTimeoutMs ? {timeoutMs: options.missionTimeoutMs} : undefined;
  this.missions = options.missions || new TikTokMissionService(this.serviceOptions);
  this.native = options.native !== undefined ? !!options.native : hasNativeSDK();
  this.kind = null;
  this.phase = 'closed';      // closed | idle | opening | checking | done
  this.message = '';
  this.version = 0;           // changes on open / close / return from background
  this.op = 0;                // changes on every new request; only the newest may update the panel
  this.entryOp = 0;
}

MissionFlow.prototype.isClaimed = function (kind) { return this.store.isClaimed(kind); };

MissionFlow.prototype.view = function () {
  var claimed = this.kind ? this.isClaimed(this.kind) : false;
  var busy = this.phase === 'opening' || this.phase === 'checking';
  return {
    open: this.kind !== null, kind: this.kind, phase: this.phase, busy: busy, claimed: claimed,
    message: this.message, native: this.native,
    rewardText: this.kind ? (this.rewardText[this.kind] || '') : '',
    // The single main button: go to TikTok first, check after coming back. Disabled while busy or claimed.
    action: claimed ? 'none' : (this.phase === 'idle' && this.navigatedOnce ? 'check' : 'start'),
    canStart: !busy && !claimed, canCheck: !busy && !claimed
  };
};

MissionFlow.prototype._render = function () { try { this.renderView(this.view()); } catch (_) {} };

MissionFlow.prototype._guard = function () {
  var self = this, version = this.version, kind = this.kind;
  return function () { return self.version === version && self.kind === kind; };
};

// open(kind)                    panel games: show the intro and check the reward first (unchanged)
// open(kind, {navigate: true})  简化.11.3, home-entry taps: the tap itself goes to TikTok at once (same user
//                               gesture, no reward query in front of it); the reward is checked in onShow().
MissionFlow.prototype.open = function (kind, options) {
  if (!KINDS[kind]) return;
  this.missions.cancel();
  this.kind = kind;
  this.version++; this.op++;
  this.navigatedOnce = false;
  this.phase = 'idle';
  this.message = this.isClaimed(kind) ? TEXT.claimed : (this.native ? TEXT['intro_' + kind] : TEXT.preview);
  this._render();
  if (!this.native) return;
  if (options && options.navigate === true) return this.start();
  if (!this.isClaimed(kind)) this.check();
};

// 简化.11.3: going to TikTok is allowed after the reward was collected too (the entry keeps working; the reward
// is still paid once, _grant() checks platformClaims).
MissionFlow.prototype.start = function () {
  if (!this.kind) return;
  if (this.phase === 'opening' || this.phase === 'checking') { this.message = TEXT.wait; this._render(); return; }
  var self = this, op = ++this.op, isCurrent = this._guard();
  this.phase = 'opening'; this.message = TEXT.opening; this._render();
  return this.missions.navigate(this.kind, {isCurrent: isCurrent}).then(function (r) {
    if (!isCurrent() || op !== self.op) return;
    self.phase = 'idle';
    if (r.status === 'success') {
      self.navigatedOnce = true;
      self.message = self.isClaimed(self.kind) ? TEXT.claimed : TEXT.navigated;
    } else self.message = r.status === 'unsupported' && !self.native ? TEXT.preview : r.message;
    self._render();
  });
};

MissionFlow.prototype.check = function () {
  if (!this.kind) return;
  if (this.isClaimed(this.kind)) { this.message = TEXT.claimed; this._render(); return; }
  if (this.phase === 'checking') return this.pendingCheck;   // merge taps during one check
  if (this.phase === 'opening') { this.message = TEXT.wait; this._render(); return; }
  var self = this, op = ++this.op, isCurrent = this._guard(), kind = this.kind;
  this.phase = 'checking'; this.message = TEXT.checking; this._render();
  this.pendingCheck = this.missions.query(kind, {isCurrent: isCurrent}).then(function (r) {
    if (!isCurrent() || op !== self.op) return;
    self.pendingCheck = null;
    if (r.eligible) { self._grant(kind); return; }
    self.phase = 'idle';
    self.message = r.status === 'ineligible' ? TEXT.notReady
      : r.status === 'unsupported' && !self.native ? TEXT.preview : r.message;
    self._render();
  });
  return this.pendingCheck;
};

MissionFlow.prototype._saveReward = function (kind) {
  var self = this;
  return this.store.update(function (draft) {
    if (draft.platformClaims[kind] === true) return false;
    draft.platformClaims[kind] = true;
    return self.reward(kind, draft);
  });
};

MissionFlow.prototype._grant = function (kind) {
  var result = this._saveReward(kind);
  if (result.ok) {
    this.phase = 'done';
    this.message = TEXT.granted + (this.rewardText[kind] || '');
    this._render();
    if (this.onGranted) { try { this.onGranted(kind, result.data); } catch (_) {} }
    return;
  }
  this.phase = 'idle';
  this.message = this.isClaimed(kind) ? TEXT.claimed : TEXT.saveFailed;
  this._render();
};

MissionFlow.prototype.close = function () {
  this.missions.cancel();
  this.kind = null;
  this.version++; this.op++;
  this.phase = 'closed'; this.message = ''; this.pendingCheck = null;
  this._render();
};

// Use the platform callback. Cocos EVENT_SHOW without entry options is only a visibility event.
MissionFlow.prototype.startEntryTracking = function () {
  if (!this.native || this.trackingEntries || this.disposed) return;
  this.trackingEntries = true;
  var self = this, candidates = sdkCandidates(), sawShow = false;
  var listener = function (entry) {
    if (entry && typeof entry.scene === 'string' && entry.scene) sawShow = true;
    self.onShow(entry);
  };
  for (var i = 0; i < candidates.length; i++) {
    var sdk = candidates[i];
    if (!sdk || typeof sdk.onShow !== 'function' || typeof sdk.offShow !== 'function') continue;
    try {
      sdk.onShow(listener);
      this.stopEntryTracking = function () { sdk.offShow(listener); };
      break;
    } catch (_) {}
  }
  // Let the owning component finish binding its renderer and wallet listeners before a cold reply.
  return Promise.resolve().then(function () {
    if (self.disposed) return;
    var entry = initialEntry(candidates);
    if (!sawShow) return self.onShow(entry);
  });
};

MissionFlow.prototype.onShow = function (entry) {
  if (!entry || !this.native || this.disposed) return;
  var kind = entry.scene === 'center' ? 'profile' : entry.scene === 'desktop_shortcut' ? 'shortcut' : null;
  if (!kind || this.isClaimed(kind)) return;
  if (this.kind === kind) {
    this.missions.cancel();
    this.op++;
    this.pendingCheck = null;
    this.phase = 'idle';
    this.navigatedOnce = true;
    this.message = '';
    this._render();
  }
  // The automatic request has a lifetime independent of the player-opened panel.
  if (!this.entryMissions) {
    this.entryMissions = this.ownsMissions ? new TikTokMissionService(this.serviceOptions) : this.missions;
  }
  var self = this, op = ++this.entryOp;
  var current = function () { return !self.disposed && op === self.entryOp; };
  this.entryMissions.onResume();
  return this.entryMissions.query(kind, {isCurrent: current}).then(function (result) {
    if (!current() || result.eligible !== true || self.isClaimed(kind)) return;
    var saved = self._saveReward(kind);
    if (!saved.ok || !self.isClaimed(kind)) return;
    if (self.kind === kind) {
      // The platform return may outrun the navigation reply. Ignore that older panel result.
      self.op++;
      self.phase = 'done';
      self.message = '';
      self.pendingCheck = null;
    }
    var view = self.view();
    view.message = '';
    try { self.renderView(view); } catch (_) {}
    if (self.onGranted) { try { self.onGranted(kind, saved.data, {source: 'entry'}); } catch (_) {} }
  });
};

MissionFlow.prototype.tick = function () { this.missions.tick(); };

MissionFlow.prototype.dispose = function () {
  this.disposed = true;
  if (this.stopEntryTracking) { try { this.stopEntryTracking(); } catch (_) {} this.stopEntryTracking = null; }
  if (this.entryMissions && this.entryMissions !== this.missions) this.entryMissions.dispose();
  this.close();
  if (this.ownsMissions) this.missions.dispose();
};

MissionFlow.TEXT = TEXT;
module.exports = MissionFlow;

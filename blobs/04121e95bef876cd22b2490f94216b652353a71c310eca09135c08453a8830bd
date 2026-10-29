'use strict';
var config = require('./PlatformConfig');
// Shared by every service instance importing this module: UI cancellation is not a native close.
var nativeSession = null;
var sequence = 0;
var messages = {
  completed: 'Reward ready.', cancelled: 'Video closed. No reward was claimed.',
  error: 'The video could not open. Please try again.', timeout: 'The video is taking too long. Please close this panel or try again later.',
  unsupported: 'Rewarded videos are available inside TikTok.', busy: 'A video is still active. Please finish or close it first.',
  stale: 'This session has ended. No reward was claimed.', unconfigured: 'This reward is not available.'
};
function rootSDK(method) {
  var candidates = [
    typeof TTMinis !== 'undefined' && TTMinis.game,
    typeof tt !== 'undefined' && tt,
    typeof wx !== 'undefined' && wx
  ];
  for (var i = 0; i < candidates.length; i++) {
    var candidate = candidates[i];
    if (!candidate || typeof candidate[method] !== 'function') continue;
    try {
      if (typeof candidate.canIUse === 'function' && !candidate.canIUse(method)) continue;
      return candidate; // Preserve the API receiver; never detach native methods.
    } catch (_) {}
  }
  return null;
}
function current(o) { try { return !o.isCurrent || o.isCurrent() === true; } catch (_) { return false; } }
function errorCode(e) { return e && (typeof e.errorCode === 'number' || typeof e.errorCode === 'string') ? e.errorCode : null; }
function safely(fn) { try { fn(); } catch (_) {} }
function makeResult(status, session, error) {
  return {status: status, rewarded: status === 'completed', message: messages[status],
    phase: session ? session.phase : 'request', requestId: session ? session.id : null,
    placementKey: session ? session.options.placementKey : null, errorCode: errorCode(error)};
}
function RewardedService(options) {
  options = options || {};
  this.getSDK = options.getSDK || rootSDK;
  this.now = options.now || Date.now;
  this.requestTimeoutMs = options.requestTimeoutMs || 15000;
  this.playbackTimeoutMs = options.playbackTimeoutMs || 120000;
  this.pending = null;
  var self = this;
  this.poll = options.autoPoll === false ? null : setInterval(function () { self.tick(); }, 100);
  if (this.poll && this.poll.unref) this.poll.unref();
}
RewardedService.prototype.tick = function () {
  var s = this.pending;
  if (!s || s.uiSettled) return;
  if (!current(s.options)) return s.settle('stale');
  if (this.now() >= s.deadline) s.settle('timeout');
};
RewardedService.prototype.request = function (options) {
  options = options || {};
  this.tick();
  if (nativeSession) return Promise.resolve(makeResult('busy', null));
  var sdk;
  try { sdk = this.getSDK('createRewardedVideoAd'); } catch (_) {}
  if (!sdk || typeof sdk.createRewardedVideoAd !== 'function') return Promise.resolve(makeResult('unsupported', null));
  try { if (typeof sdk.canIUse === 'function' && !sdk.canIUse('createRewardedVideoAd')) return Promise.resolve(makeResult('unsupported', null)); }
  catch (_) { return Promise.resolve(makeResult('unsupported', null)); }
  var adUnitId = config.getAdUnitId(options.placementKey);
  if (!adUnitId) return Promise.resolve(makeResult('unconfigured', null));
  if (!current(options)) return Promise.resolve(makeResult('stale', null));
  var self = this;
  return new Promise(function (resolve) {
    var s = {id: ++sequence, options: options, phase: 'request', ad: null,
      deadline: self.now() + self.requestTimeoutMs, uiSettled: false, terminal: false};
    self.pending = s;
    nativeSession = s;
    s.settle = function (status, error) {
      if (s.uiSettled) return;
      s.uiSettled = true;
      if (self.pending === s) self.pending = null;
      var result = makeResult(status, s, error);
      resolve(result);
    };
    function finish(status, error) {
      if (s.terminal) return;
      s.terminal = true;
      if (nativeSession === s) nativeSession = null;
      if (s.ad) {
        if (typeof s.ad.offClose === 'function') safely(function () { s.ad.offClose(onClose); });
        if (typeof s.ad.offError === 'function') safely(function () { s.ad.offError(onError); });
      }
      // No late success after timeout/cancel/stale, even if native playback eventually ends.
      s.settle(current(options) ? status : 'stale', error);
    }
    function onClose(res) { finish(res && res.isEnded === true ? 'completed' : 'cancelled'); }
    function onError(e) { finish('error', e); }
    try {
      s.ad = sdk.createRewardedVideoAd({adUnitId: adUnitId});
      if (!s.ad || typeof s.ad.onClose !== 'function' || typeof s.ad.onError !== 'function' || typeof s.ad.show !== 'function') {
        finish('unsupported'); return;
      }
      s.ad.onClose(onClose);
      s.ad.onError(onError);
      if (s.terminal) return;
      var shown = s.ad.show();
      if (shown && typeof shown.then === 'function') {
        shown.then(function () {
          // Resolving show means shown, never watched/completed.
          if (s.terminal || s.uiSettled) return;
          s.phase = 'playing';
          s.deadline = self.now() + self.playbackTimeoutMs;
        }, function (e) { finish('error', e); });
      }
    } catch (e) { finish('error', e); }
  });
};
RewardedService.prototype.cancelOwner = function (ownerId) {
  if (this.pending && this.pending.options.ownerId === ownerId) this.pending.settle('cancelled');
};
RewardedService.prototype.isNativeBusy = function () { return nativeSession !== null; };
RewardedService.prototype.dispose = function () {
  if (this.pending) this.pending.settle('stale');
  if (this.poll !== null) clearInterval(this.poll);
  this.poll = null;
  // Keep native event listeners until a real SDK terminal signal releases the global lock.
};
module.exports = RewardedService;

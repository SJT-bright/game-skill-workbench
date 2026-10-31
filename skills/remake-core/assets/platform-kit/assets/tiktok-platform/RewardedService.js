'use strict';
var config = require('./PlatformConfig');
// Rewarded-ad timeout rule (Basil rule, remake-ads/references/ad-timeout-and-regression.md):
// - request phase (until show() resolves) may time out: requestTimeoutMs, default 15 s;
//   time spent in the background does not count.
// - after show() resolves there is NO timeout: the reward depends only on onClose(isEnded) / onError.
// - if no callback arrives, exitAvailable() turns true exitAfterMs (default 30 s) after playback
//   started; the game shows an X that calls exit().
// - timeout, exit, cancel and dispose unbind the ad's callbacks and release the session at once,
//   so the next request can start immediately. No lock outlives a settled request.
// Shared by every service instance importing this module: one live ad session at a time.
var nativeSession = null;
var sequence = 0;
var messages = {
  completed: 'Reward ready.', cancelled: 'Video closed. No reward was claimed.',
  error: 'The video could not open. Please try again.', timeout: 'The video took too long to start. Please try again.',
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
function makeResult(status, session, error, reason) {
  return {status: status, rewarded: status === 'completed', message: messages[status],
    phase: session ? session.phase : 'request', requestId: session ? session.id : null,
    placementKey: session ? session.options.placementKey : null, errorCode: errorCode(error),
    reason: reason || null};
}
function RewardedService(options) {
  options = options || {};
  this.getSDK = options.getSDK || rootSDK;
  this.now = options.now || Date.now;
  this.requestTimeoutMs = options.requestTimeoutMs || 15000;
  this.exitAfterMs = options.exitAfterMs || 30000;
  this.pending = null;
  var self = this;
  this.poll = options.autoPoll === false ? null : setInterval(function () { self.tick(); }, 100);
  if (this.poll && this.poll.unref) this.poll.unref();
}
RewardedService.prototype.tick = function () {
  var s = this.pending;
  if (!s || s.terminal) return;
  if (!current(s.options)) return s.finish('stale');
  if (s.phase === 'request') {
    // Background time does not count: the deadline is frozen while hidden.
    if (s.hiddenAt === null && this.now() >= s.deadline) s.finish('timeout');
  } else if (!s.exitNotified && this.exitAvailable()) {
    s.exitNotified = true;
    if (typeof s.options.onExitAvailable === 'function') safely(function () { s.options.onExitAvailable(); });
  }
};
// Lifecycle forwarding (cc.game EVENT_HIDE / EVENT_SHOW, or tt.onHide / tt.onShow).
RewardedService.prototype.onHide = function () {
  var s = this.pending;
  if (s && s.hiddenAt === null) s.hiddenAt = this.now();
};
RewardedService.prototype.onShow = function () {
  var s = this.pending;
  if (!s || s.hiddenAt === null) return;
  var away = Math.max(0, this.now() - s.hiddenAt);
  s.hiddenAt = null;
  if (s.phase === 'request') s.deadline += away;
};
// True once playback has run exitAfterMs with no callback: show the X now.
RewardedService.prototype.exitAvailable = function () {
  var s = this.pending;
  return !!(s && !s.terminal && s.phase === 'playing' && this.now() >= s.exitAt);
};
// The player pressed the X: no reward, callbacks unbound, next request may start at once.
RewardedService.prototype.exit = function () {
  if (this.pending) this.pending.finish('cancelled', null, 'exit');
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
    var s = {id: ++sequence, options: options, phase: 'request', ad: null, hiddenAt: null,
      deadline: self.now() + self.requestTimeoutMs, exitAt: Infinity, exitNotified: false, terminal: false};
    self.pending = s;
    nativeSession = s;
    function onClose(res) { s.finish(res && res.isEnded === true ? 'completed' : 'cancelled'); }
    function onError(e) { s.finish('error', e); }
    function onHide() { self.onHide(); }
    function onShow() { self.onShow(); }
    // Single terminal path: every outcome unbinds callbacks and releases the session together.
    s.finish = function (status, error, reason) {
      if (s.terminal) return;
      s.terminal = true;
      if (self.pending === s) self.pending = null;
      if (nativeSession === s) nativeSession = null;
      if (s.ad) {
        if (typeof s.ad.offClose === 'function') safely(function () { s.ad.offClose(onClose); });
        if (typeof s.ad.offError === 'function') safely(function () { s.ad.offError(onError); });
      }
      if (typeof sdk.offHide === 'function') safely(function () { sdk.offHide(onHide); });
      if (typeof sdk.offShow === 'function') safely(function () { sdk.offShow(onShow); });
      // No late success after timeout/exit/cancel/stale: the callbacks are already unbound.
      resolve(makeResult(current(options) ? status : 'stale', s, error, reason));
    };
    try {
      if (typeof sdk.onHide === 'function') sdk.onHide(onHide);
      if (typeof sdk.onShow === 'function') sdk.onShow(onShow);
      s.ad = sdk.createRewardedVideoAd({adUnitId: adUnitId});
      if (!s.ad || typeof s.ad.onClose !== 'function' || typeof s.ad.onError !== 'function' || typeof s.ad.show !== 'function') {
        s.finish('unsupported'); return;
      }
      s.ad.onClose(onClose);
      s.ad.onError(onError);
      if (s.terminal) return;
      var shown = s.ad.show();
      if (shown && typeof shown.then === 'function') {
        shown.then(function () {
          // Resolving show means playback started, never watched/completed. No timeout from here.
          if (s.terminal) return;
          s.phase = 'playing';
          s.exitAt = self.now() + self.exitAfterMs;
        }, function (e) { s.finish('error', e); });
      } else {
        s.phase = 'playing';
        s.exitAt = self.now() + self.exitAfterMs;
      }
    } catch (e) { s.finish('error', e); }
  });
};
RewardedService.prototype.cancelOwner = function (ownerId) {
  if (this.pending && this.pending.options.ownerId === ownerId) this.pending.finish('cancelled', null, 'owner');
};
RewardedService.prototype.isNativeBusy = function () { return nativeSession !== null; };
RewardedService.prototype.dispose = function () {
  if (this.pending) this.pending.finish('stale');
  if (this.poll !== null) clearInterval(this.poll);
  this.poll = null;
};
module.exports = RewardedService;

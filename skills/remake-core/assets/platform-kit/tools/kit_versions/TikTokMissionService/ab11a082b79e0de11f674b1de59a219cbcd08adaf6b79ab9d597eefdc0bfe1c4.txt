'use strict';
var methods = {
  shortcut: {navigate: 'addShortcut', query: 'getShortcutMissionReward'},
  profile: {navigate: 'startEntranceMission', query: 'getEntranceMissionReward'}
};
var messages = {
  success: 'Return through this TikTok entry, then check your reward.',
  eligible: 'Your reward is ready to claim.', ineligible: 'Open this game from the TikTok entry, then check again.',
  unsupported: 'This feature is available inside a supported TikTok app.',
  error: 'The request failed. Please try again.', timeout: 'The check took too long. Please try again.',
  invalid: 'No reward information was returned. Please try again.', cancelled: 'The check ended. Please try again.',
  stale: 'This check has ended. Please check again.'
};
function sdk(method) {
  var candidates = [
    typeof TTMinis !== 'undefined' && TTMinis.game,
    typeof tt !== 'undefined' && tt,
    typeof wx !== 'undefined' && wx
  ];
  for (var i = 0; i < candidates.length; i++) {
    var candidate = candidates[i];
    if (!candidate || typeof candidate[method] !== 'function' || typeof candidate.canIUse !== 'function') continue;
    try {
      if (candidate.canIUse(method)) return candidate;
    } catch (_) {}
  }
  return null;
}
function isCurrent(options) { try { return !options.isCurrent || options.isCurrent() === true; } catch (_) { return false; } }
function result(status, request, e) {
  return {status: status, eligible: status === 'eligible', rewarded: false, message: messages[status],
    requestId: request ? request.id : null, kind: request ? request.kind : null,
    api: request ? request.method : null, errorCode: e && e.errorCode !== undefined ? e.errorCode : null};
}
function TikTokMissionService(options) {
  options = options || {};
  this.getSDK = options.getSDK || sdk;
  this.now = options.now || Date.now;
  this.timeoutMs = options.timeoutMs || 10000;
  this.pending = {};
  this.epoch = 0;
  this.sequence = 0;
  var self = this;
  this.poll = options.autoPoll === false ? null : setInterval(function () { self.tick(); }, 100);
  if (this.poll && this.poll.unref) this.poll.unref();
}
TikTokMissionService.prototype.tick = function () {
  var self = this;
  Object.keys(this.pending).forEach(function (key) {
    var r = self.pending[key];
    if (!isCurrent(r.options)) r.settle('stale');
    else if (self.now() >= r.deadline) r.settle('timeout');
    else if (r.emptyAt !== null && self.now() >= r.emptyAt) r.settle('invalid');
  });
};
TikTokMissionService.prototype._call = function (kind, action, options) {
  options = options || {};
  this.tick();
  var method = methods[kind] && methods[kind][action];
  if (!method) return Promise.resolve(result('unsupported', null));
  var key = kind + ':' + action;
  if (this.pending[key]) return this.pending[key].promise;
  var api;
  try { api = this.getSDK(method); } catch (_) {}
  try {
    if (!api || typeof api[method] !== 'function' || typeof api.canIUse !== 'function' || !api.canIUse(method))
      return Promise.resolve(result('unsupported', null));
  } catch (_) { return Promise.resolve(result('unsupported', null)); }
  if (!isCurrent(options)) return Promise.resolve(result('stale', null));
  var self = this;
  var resolve;
  var promise = new Promise(function (done) { resolve = done; });
  var r = {id: ++this.sequence, kind: kind, method: method, action: action, options: options,
    epoch: this.epoch, deadline: this.now() + this.timeoutMs, emptyAt: null, settled: false, promise: promise};
  r.settle = function (status, error) {
    if (r.settled) return;
    r.settled = true;
    if (self.pending[key] === r) delete self.pending[key];
    resolve(result(r.epoch === self.epoch && isCurrent(options) ? status : 'stale', r, error));
  };
  this.pending[key] = r;
  function empty() {
    if (r.settled) return;
    // Allow a valid same-turn Promise to follow complete/undefined success.
    // Longer or missing results still have a bounded visible exit.
    if (r.emptyAt === null) r.emptyAt = Math.min(r.deadline, self.now() + 100);
  }
  function success(value) {
    if (r.settled) return;
    if (action === 'navigate') return r.settle('success');
    if (value && value.canReceiveReward === true) r.settle('eligible');
    else if (value && value.canReceiveReward === false) r.settle('ineligible');
    else empty();
  }
  function fail(error) { r.settle('error', error); }
  try {
    var returned = api[method]({success: success, fail: fail, complete: empty});
    if (returned && typeof returned.then === 'function') returned.then(success, fail);
  } catch (error) { fail(error); }
  return promise;
};
TikTokMissionService.prototype.navigate = function (kind, options) { return this._call(kind, 'navigate', options); };
TikTokMissionService.prototype.query = function (kind, options) { return this._call(kind, 'query', options); };
TikTokMissionService.prototype.cancel = function () {
  this.epoch++;
  var self = this;
  Object.keys(this.pending).forEach(function (key) { self.pending[key].settle('cancelled'); });
};
TikTokMissionService.prototype.onResume = function () { this.cancel(); };
TikTokMissionService.prototype.dispose = function () {
  this.cancel();
  if (this.poll !== null) clearInterval(this.poll);
  this.poll = null;
};
module.exports = TikTokMissionService;

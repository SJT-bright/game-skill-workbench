'use strict';
// One accepted display policy per game runtime. Remote refresh stays outside ad transactions.
// This module owns only a separate configuration cache; it never reads or writes player saves.
var VERSION = 1;
var ROOT_KEY = '__tiktokKitAdDisplayPolicyV1';
var MAX_INTEGER = 9007199254740991;
function rootObject() {
  if (typeof globalThis !== 'undefined') return globalThis;
  if (typeof window !== 'undefined') return window;
  return typeof global !== 'undefined' ? global : null;
}
function sdkFor(method) {
  var choices = [typeof TTMinis !== 'undefined' && TTMinis && TTMinis.game,
    typeof tt !== 'undefined' && tt];
  for (var i = 0; i < choices.length; i++) if (choices[i] && typeof choices[i][method] === 'function') return choices[i];
  return null;
}
function localStorage() {
  var storage;
  // Cocos 3.x web-adapter can publish sys.localStorage on window without a global cc.
  // Each lookup is isolated because browsers may expose a throwing localStorage getter.
  try { storage = typeof cc !== 'undefined' && cc && cc.sys && cc.sys.localStorage; }
  catch (_) { storage = null; }
  if (storage && typeof storage.getItem === 'function') return storage;
  try { storage = typeof window !== 'undefined' && window && window.localStorage; }
  catch (_) { storage = null; }
  if (storage && typeof storage.getItem === 'function') return storage;
  try { var root = rootObject(); storage = root && root.localStorage; }
  catch (_) { storage = null; }
  return storage && typeof storage.getItem === 'function' ? storage : null;
}
function own(o, key) { return Object.prototype.hasOwnProperty.call(o, key); }
function record(o) { return !!o && typeof o === 'object' && !Array.isArray(o); }
function integer(n) { return typeof n === 'number' && isFinite(n) && n >= 0 && n <= MAX_INTEGER && Math.floor(n) === n; }
function positive(n, fallback) { return integer(n) && n > 0 ? n : fallback; }
// Stable cache-source identifier, not a cryptographic authenticity claim. Identity is also checked in full.
function fingerprint(text) {
  var a = 2166136261, b = 5381;
  for (var i = 0; i < text.length; i++) { a = ((a ^ text.charCodeAt(i)) * 16777619) >>> 0; b = ((b * 33) ^ text.charCodeAt(i)) >>> 0; }
  return text.length + '-' + a.toString(16) + '-' + b.toString(16);
}
function settings(config) {
  config = config || {};
  var block = config.adDisplay === undefined ? {} : config.adDisplay;
  if (!record(block)) throw new Error('ad_display_invalid_config');
  if (own(block, 'enabled') && typeof block.enabled !== 'boolean') throw new Error('ad_display_invalid_enabled');
  if (own(block, 'remoteUrl') && typeof block.remoteUrl !== 'string') throw new Error('ad_display_invalid_remote_url');
  var url = block.remoteUrl || '';
  if (url && !/^https:\/\/[^\s/?#]+(?:[/?#]|$)/i.test(url)) throw new Error('ad_display_requires_https');
  var gameId = config.gameId || '', appId = config.appId || '', channel = block.channel === undefined ? 'production' : block.channel;
  if (typeof gameId !== 'string' || typeof appId !== 'string' || typeof channel !== 'string' || !channel) throw new Error('ad_display_invalid_identity');
  if (url && (!gameId || gameId === 'change-me' || !appId)) throw new Error('ad_display_unconfigured_identity');
  var source = fingerprint(url);
  return {gameId: gameId, appId: appId, channel: channel, url: url, source: source,
    enabled: block.enabled !== false, refreshAfterMs: positive(block.refreshAfterMs, 60000),
    requestTimeoutMs: positive(block.requestTimeoutMs, 1500),
    identity: JSON.stringify([VERSION, gameId, appId, channel, source])};
}
function parsed(value) {
  if (typeof value === 'string') { try { return JSON.parse(value); } catch (_) { return null; } }
  return record(value) ? value : null;
}
function valid(value, cfg, cached) {
  return record(value) && value.schemaVersion === VERSION && value.gameId === cfg.gameId && value.appId === cfg.appId &&
    value.channel === cfg.channel && integer(value.revision) && record(value.ads) && typeof value.ads.enabled === 'boolean' &&
    (!cached || value.sourceFingerprint === cfg.source);
}
function acceptedRecord(value, cfg) {
  return {schemaVersion: VERSION, gameId: cfg.gameId, appId: cfg.appId, channel: cfg.channel,
    sourceFingerprint: cfg.source, revision: value.revision, ads: {enabled: value.ads.enabled}};
}
function Policy(config, options) {
  options = options || {};
  this._cfg = settings(config);
  this.version = VERSION;
  this.identity = this._cfg.identity;
  this._signature = JSON.stringify([this._cfg.enabled, this._cfg.refreshAfterMs, this._cfg.requestTimeoutMs]);
  this.cacheKey = 'tiktok:ad-display:v1:' + encodeURIComponent(this.identity);
  this._storage = own(options, 'storage') ? options.storage : localStorage();
  this._getSDK = options.getSDK || sdkFor;
  this._request = options.request || null;
  this._now = options.now || Date.now;
  this._setTimeout = options.setTimeout || setTimeout;
  this._clearTimeout = options.clearTimeout || clearTimeout;
  this._accepted = null;
  this._listeners = [];
  this._lastAttempt = null;
  this._inflight = null;
  this._requestSequence = 0;
  this._lifecycleBound = false;
  this._lastOutcome = 'default';
  this._cacheWriteFailed = false;
  // Synchronous initialization must finish before this instance can be published or read by an ad.
  if (this._storage && typeof this._storage.getItem === 'function') {
    try {
      var raw = this._storage.getItem(this.cacheKey), value = parsed(raw);
      if (valid(value, this._cfg, true)) { this._accepted = acceptedRecord(value, this._cfg); this._lastOutcome = 'cache'; }
      else if (raw !== null && raw !== undefined && raw !== '') this._lastOutcome = 'invalid_cache';
    } catch (_) { this._lastOutcome = 'cache_unreadable'; }
  }
  if (options.bindLifecycle !== false) this._bindLifecycle();
}
Policy.prototype.isEnabled = function () {
  return this._cfg.enabled && (!this._accepted || this._accepted.ads.enabled === true);
};
Policy.prototype.state = function () {
  return {version: VERSION, identity: this.identity, ready: true, gameId: this._cfg.gameId, appId: this._cfg.appId,
    channel: this._cfg.channel, sourceFingerprint: this._cfg.source, remoteConfigured: !!this._cfg.url,
    revision: this._accepted ? this._accepted.revision : null, enabled: this.isEnabled(),
    localEnabled: this._cfg.enabled, remoteEnabled: this._accepted ? this._accepted.ads.enabled : null,
    lastAttemptAt: this._lastAttempt, lastOutcome: this._lastOutcome, cacheWriteFailed: this._cacheWriteFailed};
};
Policy.prototype.subscribe = function (fn) {
  if (typeof fn !== 'function') return function () {};
  var self = this, active = true;
  this._listeners.push(fn);
  return function () {
    if (!active) return; active = false;
    var index = self._listeners.indexOf(fn); if (index >= 0) self._listeners.splice(index, 1);
  };
};
Policy.prototype._notify = function () {
  var listeners = this._listeners.slice();
  for (var i = 0; i < listeners.length; i++) { try { listeners[i](this.state()); } catch (_) {} }
};
Policy.prototype._bindLifecycle = function () {
  if (this._lifecycleBound || !this._cfg.url) return;
  var sdk, self = this;
  try { sdk = this._getSDK('onShow'); } catch (_) {}
  if (!sdk || typeof sdk.onShow !== 'function') return;
  try { sdk.onShow(function () { self.refresh(); }); this._lifecycleBound = true; } catch (_) {}
};
Policy.prototype._accept = function (value) {
  if (!valid(value, this._cfg, false)) { this._lastOutcome = 'invalid_response'; return; }
  var previous = this._accepted;
  if (previous && (value.revision < previous.revision || (value.revision === previous.revision && value.ads.enabled !== previous.ads.enabled))) {
    this._lastOutcome = 'old_or_conflicting_revision'; return;
  }
  if (previous && value.revision === previous.revision) { this._lastOutcome = 'unchanged'; return; }
  var wasEnabled = this.isEnabled();
  this._accepted = acceptedRecord(value, this._cfg);
  this._lastOutcome = 'accepted';
  this._cacheWriteFailed = false;
  if (this._storage && typeof this._storage.setItem === 'function') {
    try {
      var text = JSON.stringify(this._accepted);
      this._storage.setItem(this.cacheKey, text);
      this._cacheWriteFailed = typeof this._storage.getItem !== 'function' || this._storage.getItem(this.cacheKey) !== text;
    } catch (_) { this._cacheWriteFailed = true; }
  } else this._cacheWriteFailed = true;
  if (wasEnabled !== this.isEnabled()) this._notify();
};
Policy.prototype.refresh = function () {
  var self = this;
  if (!this._cfg.url) return Promise.resolve(this.state());
  if (this._inflight) return this._inflight;
  var now;
  try { now = this._now(); } catch (_) { now = Date.now(); }
  if (typeof now !== 'number' || !isFinite(now)) now = Date.now();
  if (this._lastAttempt !== null && now >= this._lastAttempt && now - this._lastAttempt < this._cfg.refreshAfterMs) return Promise.resolve(this.state());
  this._lastAttempt = now;
  var sdk, request = this._request;
  if (!request) {
    try { sdk = this._getSDK('request'); } catch (_) {}
    if (sdk && typeof sdk.request === 'function') request = function (o) { return sdk.request(o); };
  }
  if (!request) { this._lastOutcome = 'request_unavailable'; return Promise.resolve(this.state()); }
  var resolve, task, timer, finished = false, sequence = ++this._requestSequence;
  var promise = new Promise(function (done) { resolve = done; });
  this._inflight = promise;
  function finish(kind, response) {
    if (finished || sequence !== self._requestSequence) return;
    finished = true;
    if (timer !== undefined) self._clearTimeout(timer);
    if (kind === 'success') {
      if (response && response.statusCode === 200) self._accept(parsed(response.data));
      else self._lastOutcome = 'invalid_response';
    } else self._lastOutcome = kind;
    if (self._inflight === promise) self._inflight = null;
    resolve(self.state());
  }
  timer = this._setTimeout(function () {
    finish('timeout');
    if (task && typeof task.abort === 'function') { try { task.abort(); } catch (_) {} }
  }, this._cfg.requestTimeoutMs);
  try {
    task = request({url: this._cfg.url, method: 'GET', dataType: 'json', timeout: this._cfg.requestTimeoutMs,
      success: function (response) { finish('success', response); }, fail: function () { finish('network_error'); }});
    if (task && typeof task.then === 'function') task.then(function (response) { finish('success', response); }, function () { finish('network_error'); });
  } catch (_) { finish('network_error'); }
  return promise;
};
function get(config, options) {
  options = options || {};
  var root = own(options, 'root') ? options.root : rootObject(), cfg = settings(config);
  var existing = root && root[ROOT_KEY];
  if (existing) {
    if (existing.version !== VERSION || existing.identity !== cfg.identity || !existing.instance ||
        existing.instance.version !== VERSION || typeof existing.instance.isEnabled !== 'function') throw new Error('ad_display_policy_identity_conflict');
    if (existing.instance._signature !== JSON.stringify([cfg.enabled, cfg.refreshAfterMs, cfg.requestTimeoutMs])) throw new Error('ad_display_policy_config_conflict');
    existing.instance._bindLifecycle();
    return existing.instance;
  }
  var instance = new Policy(config, options);
  if (root) root[ROOT_KEY] = {version: VERSION, identity: instance.identity, instance: instance};
  return instance;
}
function current(root) {
  root = arguments.length ? root : rootObject();
  var entry = root && root[ROOT_KEY];
  return entry && entry.version === VERSION && entry.instance && entry.instance.version === VERSION &&
    entry.identity === entry.instance.identity && typeof entry.instance.isEnabled === 'function' ? entry.instance : null;
}
module.exports = {version: VERSION, ROOT_KEY: ROOT_KEY, get: get, current: current,
  create: function (config, options) { return new Policy(config, options); }};

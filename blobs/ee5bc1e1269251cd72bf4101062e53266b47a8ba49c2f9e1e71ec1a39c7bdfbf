'use strict';
// TikTok Platform Kit v1 - one save per game, one JSON string under one key. Copy unchanged.
//
// Why a string: TikTok/ByteDance storage can hand back an object whose key order differs from what
// was written, so comparing objects (JSON.stringify(readBack) === JSON.stringify(written)) fails at
// random. Here the game data is serialized ONCE to a string, that exact string is stored and the
// read-back is compared as a string.
//
// Rules this file enforces:
//  - update() works on a copy. Memory only changes after the write is read back identical.
//  - A failed write never reports success; the caller shows "Could not save" and keeps its state.
//  - A corrupt save is backed up and replaced by defaults with meta.recoveredFromCorrupt set, so
//    one-time rewards (platform claims) are treated as already claimed instead of paid twice.
//  - Everything that must change together (coins + "reward claimed" flag) goes in ONE update().
var config = require('./PlatformConfig');

function clone(value) { return JSON.parse(JSON.stringify(value)); }
function isRecord(value) { return !!value && typeof value === 'object' && !Array.isArray(value); }
function defaultStorage() {
  return typeof cc !== 'undefined' && cc.sys && cc.sys.localStorage ? cc.sys.localStorage : null;
}
// getStorageInfoSync().keys from the platform SDK (same lookup order as TikTokMissionService.js).
// Returns an array of keys, or null when the runtime cannot tell which keys exist.
function defaultStorageKeys() {
  var candidates = [
    typeof TTMinis !== 'undefined' && TTMinis && TTMinis.game,
    typeof tt !== 'undefined' && tt,
    typeof wx !== 'undefined' && wx
  ];
  for (var i = 0; i < candidates.length; i++) {
    var c = candidates[i];
    if (!c || typeof c.getStorageInfoSync !== 'function') continue;
    try {
      var info = c.getStorageInfoSync();
      if (info && Array.isArray(info.keys)) return info.keys;
    } catch (_) {}
  }
  return null;
}
function isUnreadable(raw) { return raw === undefined || raw === true || raw === false; }

// v1.2 (Mabel's Meadow r8, D4 problem 6): TikTok's publish scan asks for the Login API. The kit sends ONE
// login after the save has loaded and never waits for it: no flow, reward or save depends on the answer,
// and a missing API, a throw, fail or a rejected Promise are all ignored.
var loginSent = false;
function noop() {}
function defaultLogin() {
  if (loginSent) return false;
  var candidates = [
    typeof TTMinis !== 'undefined' && TTMinis && TTMinis.game,
    typeof tt !== 'undefined' && tt,
    typeof wx !== 'undefined' && wx
  ];
  for (var i = 0; i < candidates.length; i++) {
    var c = candidates[i];
    if (!c || typeof c.login !== 'function') continue;
    loginSent = true;
    try {
      var r = c.login({success: noop, fail: noop, complete: noop});
      if (r && typeof r.then === 'function') r.then(noop, noop);
    } catch (_) {}
    return true;
  }
  return false;
}

function SaveStore(defaults, options) {
  options = options || {};
  this.key = options.key || config.saveKey();
  this.storage = options.storage || defaultStorage();
  this.storageKeys = options.storageKeys || defaultStorageKeys;
  // login: false turns the fire-and-forget login off (tests); a function replaces the platform call.
  this.login = options.login === false ? noop : (typeof options.login === 'function' ? options.login : defaultLogin);
  this.loginTried = false;
  this.now = options.now || Date.now;
  this.defaults = clone(isRecord(defaults) ? defaults : {});
  if (!isRecord(this.defaults.platformClaims)) this.defaults.platformClaims = {shortcut: false, profile: false};
  if (!isRecord(this.defaults.meta)) this.defaults.meta = {};
  this.data = null;
  this.status = 'unloaded';
}

SaveStore.prototype._fill = function (data) {
  var self = this;
  Object.keys(this.defaults).forEach(function (k) {
    if (data[k] === undefined) data[k] = clone(self.defaults[k]);
  });
  if (!isRecord(data.platformClaims)) data.platformClaims = {shortcut: false, profile: false};
  if (!isRecord(data.meta)) data.meta = {};
  return data;
};

// Returns {ok, status: 'new'|'loaded'|'recovered'|'unavailable', data}.
// v1.2 (MergeShot2048 v81-v85 on a real iPhone): TikTok storage can read back true/false/undefined, or throw,
// for a key. Such a read is never treated as a save. getStorageInfoSync().keys decides whether the key exists:
// missing key = no save yet, defaults are written once; existing key with an unreadable value = corrupt save
// (backed up, defaults written once, one-time rewards treated as claimed). Nothing is logged per read.
SaveStore.prototype.load = function () {
  var result = this._load();
  this._loginOnce();
  return result;
};

// After the first load only; deferred so a slow or throwing SDK can never delay or break the load.
SaveStore.prototype._loginOnce = function () {
  if (this.loginTried) return;
  this.loginTried = true;
  var login = this.login;
  function send() { try { login(); } catch (_) {} }
  try { if (typeof setTimeout === 'function') setTimeout(send, 0); else send(); } catch (_) {}
};

SaveStore.prototype._load = function () {
  if (!this.storage) { this.data = clone(this.defaults); this.status = 'unavailable'; return this._result(false, 'storage_unavailable'); }
  var raw = null, threw = false;
  try { raw = this.storage.getItem(this.key); }
  catch (_) { threw = true; }
  if (threw || isUnreadable(raw)) {
    var keys = null;
    try { keys = this.storageKeys(); } catch (_) { keys = null; }
    var known = Array.isArray(keys);
    if (known && keys.indexOf(this.key) < 0) return this._fresh();
    if (threw) { this.data = clone(this.defaults); this.status = 'unavailable'; return this._result(false, 'read_failed'); }
    if (raw === undefined && !known) { this.data = clone(this.defaults); this.status = 'new'; return this._result(true); }
    return this._recover(raw);
  }
  if (raw === null || raw === '') {
    this.data = clone(this.defaults); this.status = 'new'; return this._result(true);
  }
  var parsed = null;
  try { parsed = typeof raw === 'string' ? JSON.parse(raw) : raw; } catch (_) { parsed = null; }
  if (!isRecord(parsed)) return this._recover(raw);
  this.data = this._fill(parsed);
  this.status = 'loaded';
  return this._result(true);
};

// No save under this key: start from defaults and write them once, so the next read returns a string.
SaveStore.prototype._fresh = function () {
  this.data = clone(this.defaults);
  this.status = 'new';
  var written = this._write(this.data);
  return this._result(true, written);
};

SaveStore.prototype._recover = function (raw) {
  try { this.storage.setItem(this.key + ':corrupt-backup', typeof raw === 'string' ? raw : String(raw)); } catch (_) {}
  var fresh = clone(this.defaults);
  fresh.meta.recoveredFromCorrupt = this.now();
  this.data = fresh;
  this.status = 'recovered';
  var written = this._write(fresh);
  return this._result(written === null, written);
};

SaveStore.prototype._write = function (draft) {
  var text;
  try { text = JSON.stringify(draft); } catch (_) { return 'serialize_failed'; }
  var previous = null;
  try { previous = this.storage.getItem(this.key); } catch (_) {}
  try { this.storage.setItem(this.key, text); } catch (_) { return 'write_failed'; }
  var back;
  try { back = this.storage.getItem(this.key); } catch (_) { back = null; }
  if (back === text) return null;
  // Read-back differs: put the previous text back so memory and storage still agree.
  try { if (typeof previous === 'string') this.storage.setItem(this.key, previous); } catch (_) {}
  return 'readback_mismatch';
};

SaveStore.prototype._result = function (ok, error) {
  return {ok: ok, status: this.status, error: error || null, data: this.data ? clone(this.data) : null};
};

// A copy of the current save. Change the save only through update().
SaveStore.prototype.get = function () {
  if (this.status === 'unloaded') this.load();
  return clone(this.data);
};

// mutator(draft) edits the copy; return false to cancel. Returns {ok, error, data}.
SaveStore.prototype.update = function (mutator) {
  if (this.status === 'unloaded') this.load();
  if (!this.storage) return this._result(false, 'storage_unavailable');
  var draft = clone(this.data);
  var answer;
  try { answer = mutator(draft); } catch (_) { return this._result(false, 'mutator_threw'); }
  if (answer === false) return this._result(false, 'cancelled');
  if (!isRecord(draft)) return this._result(false, 'invalid_draft');
  var error = this._write(draft);
  if (error) return this._result(false, error);
  this.data = draft;
  if (this.status === 'new' || this.status === 'unavailable') this.status = 'loaded';
  return this._result(true);
};

SaveStore.prototype.isClaimed = function (kind) {
  if (this.status === 'unloaded') this.load();
  if (this.data.meta && this.data.meta.recoveredFromCorrupt) return true;
  return this.data.platformClaims[kind] === true;
};

// Test hook only: lets a test send the one-per-process login again.
SaveStore._resetLoginForTests = function () { loginSent = false; };
module.exports = SaveStore;

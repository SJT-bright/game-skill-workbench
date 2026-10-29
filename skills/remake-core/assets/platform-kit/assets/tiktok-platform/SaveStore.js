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

function SaveStore(defaults, options) {
  options = options || {};
  this.key = options.key || config.saveKey();
  this.storage = options.storage || defaultStorage();
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
SaveStore.prototype.load = function () {
  if (!this.storage) { this.data = clone(this.defaults); this.status = 'unavailable'; return this._result(false, 'storage_unavailable'); }
  var raw = null;
  try { raw = this.storage.getItem(this.key); }
  catch (_) { this.data = clone(this.defaults); this.status = 'unavailable'; return this._result(false, 'read_failed'); }
  if (raw === null || raw === undefined || raw === '') {
    this.data = clone(this.defaults); this.status = 'new'; return this._result(true);
  }
  var parsed = null;
  try { parsed = typeof raw === 'string' ? JSON.parse(raw) : raw; } catch (_) { parsed = null; }
  if (!isRecord(parsed)) return this._recover(raw);
  this.data = this._fill(parsed);
  this.status = 'loaded';
  return this._result(true);
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

module.exports = SaveStore;

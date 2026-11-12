'use strict';
// TikTok Platform Kit storage guard. Known SDK/bridge compatibility models, not a real-device verdict.
//
// Rule (2026-11-12): reading saved data never stops the game.
//   - setItem writes text only: numbers and Booleans become String(value), objects become JSON text.
//   - getItem hands back a non-empty string or an object unchanged; a number becomes text.
//   - anything else (true / false / '' / undefined / null / NaN, or a read that throws) is "no value": null.
//     A key the platform lists with '' stays ''. The game then uses its default, exactly as for a new player.
//   - no key is ever locked: the game can always save.
// History: the version in games up to 2026-11-10 (1853efbe, base MergeShot2048 v85, real iPhone) returned null in
// these cases. The 2026-11-11 versions threw and locked the key instead; a game built with them did not start on
// a real phone (startup load failed: "Stored value unreadable ... IS_GAME_MUSIC"). This file returns to null and
// prints one console line per key for a Boolean, a read that throws or a listed key that reads empty, so a phone
// log shows what the storage really returned (a plain null / undefined for a key nobody lists stays silent).
// recoverTyped() below can fetch the real value of an old key through the async API before the game reads it.
// SaveStore keys remain raw; SaveStore decides about them itself. See cross-platform-runtime-contract.md.
var SAVESTORE_KEY = /:save:v\d+(:corrupt-backup)?$/;
function install(cc, api) {
  var root = typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this);
  // Game scripts inside the Cocos bundle cannot require() this root file: they reach recoverTyped() through this global.
  root.TikTokStorageGuard = install;
  var log = root.__tiktokKitStorageEvents = root.__tiktokKitStorageEvents || [];
  function note(key, kind) { if (log.length < 60) log.push({key: String(key), kind: kind, at: Date.now()}); }
  function listed(key, storage) {
    var list = [api, root.TTMinis && root.TTMinis.game, root.tt];
    for (var i = 0; i < list.length; i++) {
      var owner = list[i];
      if (!owner || typeof owner.getStorageInfoSync !== 'function') continue;
      try {
        var info = owner.getStorageInfoSync();
        if (info && Array.isArray(info.keys)) return info.keys.indexOf(String(key)) >= 0;
      } catch (ignore) {}
    }
    // Standard Web Storage provides its own presence index even without a platform API.
    try {
      if (storage && typeof storage.key === 'function' && Number.isSafeInteger(storage.length) && storage.length >= 0 && storage.length <= 10000) {
        for (var k = 0; k < storage.length; k++) if (storage.key(k) === String(key)) return true;
        return false;
      }
    } catch (ignore) {}
    return null;
  }
  function text(value) {
    if (typeof value === 'string') return value;
    if (typeof value === 'number' || typeof value === 'boolean') return String(value);
    if (value && typeof value === 'object') { try { return JSON.stringify(value); } catch (error) { return String(value); } }
    return String(value);
  }
  function guard(storage) {
    if (!storage || typeof storage.getItem !== 'function' || storage.getItem.__tiktokKitStorageGuard) return false;
    var read = storage.getItem, write = storage.setItem, knownAbsent = Object.create(null);
    var writeCount = Object.create(null), warnedKeys = Object.create(null), warned = 0;
    // One short console line per key (at most 20 keys) so a phone log shows what the storage returned.
    function noValue(key, kind, value) {
      note(key, kind);
      if (!warnedKeys[String(key)] && warned < 20 && typeof console !== 'undefined' && console && typeof console.warn === 'function') {
        warnedKeys[String(key)] = true; warned++;
        try { console.warn('[TikTokKit] storage ' + String(key) + ': ' + kind + (typeof value === 'boolean' ? ' ' + value : '') + ', read as no value'); } catch (ignore) {}
      }
      return null;
    }
    var guardedRead = function (key) {
      var value;
      try { value = read.call(storage, key); }
      catch (error) {
        if (knownAbsent[String(key)]) return null;
        if (SAVESTORE_KEY.test(String(key))) throw error;
        if (listed(key, storage) === false) { note(key, 'throw_absent'); return null; }
        return noValue(key, 'read_threw');
      }
      // An async-confirmed missing key must not conceal a subsequently readable SDK write.
      if (knownAbsent[String(key)]) {
        if (typeof value === 'string' || value && typeof value === 'object' || typeof value === 'number' && isFinite(value)) delete knownAbsent[String(key)];
        else return null;
      }
      if (SAVESTORE_KEY.test(String(key))) return value;
      if (typeof value === 'string' && value !== '') return value;
      if (value && typeof value === 'object') return value;
      if (typeof value === 'number' && isFinite(value)) return String(value);
      var present = listed(key, storage);
      if (value === '' && present === true) return '';
      if (present === false) { note(key, 'confirmed_absent'); return null; }
      // null / undefined without a key list is the usual answer for a key that was never written: no console line.
      if ((value === null || value === undefined) && present === null) { note(key, 'absent_unknown'); return null; }
      // Still not a string, number or object: a Boolean, '' or NaN, or nothing at all for a key the platform lists.
      // It may be a real switch, a missing key or a number the bridge turned into a Boolean; this layer cannot tell.
      return noValue(key, typeof value === 'boolean' ? 'boolean_read' : 'empty_read', value);
    };
    guardedRead.__tiktokKitStorageGuard = true;
    // blocked: always empty since 2026-11-12 (no key is locked); kept so code written against 2026-11-11 still runs.
    guardedRead.__tiktokKitStorageState = {storage: storage, read: read, write: write, listed: function(key){return listed(key,storage);}, blocked: Object.create(null), knownAbsent: knownAbsent, writeCount: writeCount, generation: 0, note: note};
    storage.getItem = guardedRead;
    if (typeof write === 'function') {
      var guardedWrite = function (key, value) {
        if (typeof value !== 'string') { note(key, 'as_text_' + typeof value); value = text(value); }
        var result = write.call(storage, key, value);
        delete knownAbsent[String(key)]; writeCount[String(key)] = (writeCount[String(key)] || 0) + 1; return result;
      };
      guardedWrite.__tiktokKitStorageGuard = true;
      storage.setItem = guardedWrite;
    }
    return true;
  }
  var main = cc && cc.sys && cc.sys.localStorage;
  var installed = guard(main);
  var other = root.localStorage;
  if (other && other !== main) installed = guard(other) || installed;
  return installed;
}
// A stored value against this game's schema. Types: integer, number, boolean, string, json_object.
// A Boolean is never a number here; recoverTyped() handles the two declared exceptions.
function typedValue(value, spec) {
  var type = spec.type, parsed = value, encoded;
  if (type === 'integer' || type === 'number') {
    if (typeof value === 'string' && !/^-?(?:\d+(?:\.\d+)?)(?:[eE][+-]?\d+)?$/.test(value)) return null;
    if (typeof value !== 'number' && typeof value !== 'string') return null;
    parsed = Number(value);
    if (!isFinite(parsed) || type === 'integer' && !Number.isSafeInteger(parsed) ||
        spec.min !== undefined && parsed < spec.min || spec.max !== undefined && parsed > spec.max) return null;
    encoded = typeof value === 'string' ? value : String(parsed);
  } else if (type === 'boolean') {
    if (typeof value === 'boolean') parsed = value;
    else if (value === 'true' || value === 'false') parsed = value === 'true';
    else return null;
    encoded = String(parsed);
  } else if (type === 'string') {
    if (typeof value !== 'string' || spec.maxLength !== undefined && value.length > spec.maxLength ||
        spec.minLength !== undefined && value.length < spec.minLength) return null;
    encoded = value;
  } else if (type === 'json_object') {
    try { parsed = typeof value === 'string' ? JSON.parse(value) : value; } catch (error) { return null; }
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null;
    try { encoded = typeof value === 'string' ? value : JSON.stringify(parsed); } catch (error) { return null; }
    if (typeof encoded !== 'string') return null;
  } else return null;
  if (Array.isArray(spec.enum) && spec.enum.indexOf(parsed) < 0) return null;
  if (typeof spec.validate === 'function') {
    try { if (spec.validate(JSON.parse(JSON.stringify(parsed))) !== true) return null; } catch (error) { return null; }
  }
  return {text:encoded};
}
function missingStorage(error) {
  if (!error || typeof error !== 'object') return false;
  if (error.errCode === 'STORAGE_KEY_NOT_FOUND' || error.errCode === 'KEY_NOT_FOUND') return true;
  return typeof error.errMsg === 'string' && /^getStorage:fail (?:data not found|key not found|no such key)[.;]?$/i.test(error.errMsg);
}
// Optional helper for old keys, called before the game reads them (cc may be null on Cocos 3.x):
//   var guard = globalThis.TikTokStorageGuard;
//   guard.recoverTyped(cc, platform, [{key:'Coin', type:'integer', min:0}, {key:'IS_MUSIC', type:'boolean'}], function (error, results) {...})
// For each key whose sync read is not usable it asks the async API for the real value and stores it as text.
// It never stops the game: when no real value can be had (async fails, hangs, answers with a Boolean again, the
// value breaks the schema, time is up) the key simply reads as "no value" and done() is still called WITHOUT an error.
// error is set only for a wrong schema list or when a newer call took over (code TIKTOK_STORAGE_SUPERSEDED: the
// newer call's callback continues the startup). results[key] says what happened:
//   kept                 already readable text that fits the schema; nothing written
//   value_recovered      the real value was found and stored as text
//   boolean_kept         type 'boolean': the Boolean itself is the value ("true" / "false" stored)
//   boolean_as_number    numeric spec with acceptBoolean: true (a 0/1 flag): stored as "1" / "0"
//   absent               the platform confirmed there is no such key (new player)
//   <why>_no_value       no real value; the key reads as no value (why: async_failed, async_empty, schema_reject,
//                        api_unavailable, timeout)
//   <why>_left_as_is     the storage returns a readable value outside the schema; the game reads it as before
//   write_unconfirmed    the text was written but did not read back; the next read decides
//   newer_write_kept     the game saved this key meanwhile; its value stays
//   not_checked_no_sdk   no guard or no platform SDK (browser preview); nothing done
// A Boolean false for a key the platform does not list is a missing key on several devices, so only `true`, or a
// Boolean for a listed key, counts as a stored Boolean.
install.recoverTyped = function (cc, api, specs, done, timeoutMs) {
  var storage = cc && cc.sys && cc.sys.localStorage;
  if (!storage) {
    var root = typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : null);
    storage = root && root.localStorage;
  }
  var state = storage && storage.getItem && storage.getItem.__tiktokKitStorageState;
  if (!Array.isArray(specs) || typeof done !== 'function') throw Error('schema list and callback required');
  if (!state || !api) {
    var unchecked = {};
    specs.forEach(function (s) { if (s && typeof s.key === 'string') unchecked[s.key] = 'not_checked_no_sdk'; });
    setTimeout(function () { done(undefined, unchecked); }, 0);
    return;
  }
  var token = ++state.generation, previous = state.cancelRecovery, ended = false, timer, lifecycle = false;
  var remaining = typeof timeoutMs === 'number' && timeoutMs > 0 ? timeoutMs : 5000, hidden = false, lastTime = Date.now();
  var results = {}, outOfTime = false, waiting = null;
  function accountTime() { var now=Date.now(); if (!hidden) remaining -= Math.max(0,now-lastTime); lastTime=now; }
  function onHide() { if (!current()) return; accountTime(); hidden=true; }
  function onShow() { if (!current()) return; hidden=false; lastTime=Date.now(); }
  function deadline() {
    if (!current()) return; accountTime();
    // Out of foreground time: the key being waited for and every key after it are settled from the sync read alone.
    if (!hidden && remaining <= 0) { outOfTime = true; if (waiting) waiting(); return; }
    timer=setTimeout(deadline,hidden ? 250 : Math.max(1,Math.min(250,remaining)));
  }
  function current() { return !ended && state.generation === token; }
  function finish(error) {
    if (ended) return; ended = true; clearTimeout(timer);
    if (state.cancelRecovery === cancel) state.cancelRecovery = null;
    if (lifecycle) { try { api.offHide(onHide); } catch (ignore) {} try { api.offShow(onShow); } catch (ignore2) {} }
    done(error, results);
  }
  function cancel() { var error=Error('Typed storage recovery superseded by a newer call'); error.code='TIKTOK_STORAGE_SUPERSEDED'; finish(error); }
  // Own the batch BEFORE cancellation can run caller code and recursively start a newer batch.
  state.cancelRecovery = cancel;
  if (previous) previous();
  if (!current()) { cancel(); return; }
  var queue = specs.slice();
  if (typeof api.onHide === 'function' && typeof api.offHide === 'function' && typeof api.onShow === 'function' && typeof api.offShow === 'function') {
    lifecycle=true; try { api.onHide(onHide); api.onShow(onShow); } catch (ignore) { try {api.offHide(onHide);api.offShow(onShow);}catch(ignore2){} lifecycle=false; }
  }
  timer=setTimeout(deadline,hidden ? 250 : Math.max(1,Math.min(250,remaining)));
  function next() {
    if (!current()) return;
    if (!queue.length) return finish();
    var spec = queue.shift();
    if (!spec || typeof spec.key !== 'string' || !spec.key || ['integer','number','boolean','string','json_object'].indexOf(spec.type) < 0)
      return finish(Error('Explicit typed legacy key schema required'));
    var key = spec.key, value, thrown = false, settled = false;
    var seenWrites = state.writeCount[key] || 0;
    try { value = state.read.call(storage, key); } catch (error) { thrown = true; }
    var present = state.listed(key);
    // Boolean/sentinel/unknown empty reads can be bridge distortion, so validate them through async API.
    var ambiguous = thrown || value === null || value === undefined || typeof value === 'boolean' || value === '' && present !== true;
    var existing = !ambiguous && typedValue(value, spec);
    function settle(outcome) {
      settled = true; waiting = null;
      state.note(key, 'typed_' + outcome); results[key] = outcome; next();
    }
    function absent() { state.knownAbsent[key] = true; settle('absent'); }
    function store(textValue, outcome) {
      // The game wrote this key while the async read was out: its newer value stays.
      if ((state.writeCount[key] || 0) !== seenWrites) return settle('newer_write_kept');
      var back;
      try { state.write.call(storage, key, textValue); back = state.read.call(storage, key); } catch (error) { back = undefined; }
      if (back !== textValue) return settle('write_unconfirmed');
      delete state.knownAbsent[key]; settle(outcome);
    }
    // No real value could be had for this key.
    function noRealValue(why) {
      if (typeof value === 'boolean' && (value === true || present === true)) {
        if (spec.type === 'boolean') return store(String(value), 'boolean_kept');
        if ((spec.type === 'integer' || spec.type === 'number') && spec.acceptBoolean === true) {
          var flag = typedValue(value ? 1 : 0, spec);
          if (flag) return store(flag.text, 'boolean_as_number');
        }
      }
      if (!ambiguous) return settle(why + '_left_as_is');
      state.knownAbsent[key] = true; settle(why + '_no_value');
    }
    function persist(original) {
      var checked = typedValue(original, spec);
      if (!checked) return noRealValue('schema_reject');
      store(checked.text, 'value_recovered');
    }
    if (present === false && ambiguous) return absent();
    if (existing && typeof value === 'string') { delete state.knownAbsent[key]; return settle('kept'); }
    if (existing) return persist(value);
    if (outOfTime) return noRealValue('timeout');
    if (typeof api.getStorage !== 'function') return noRealValue('api_unavailable');
    waiting = function () { if (!current() || settled) return; noRealValue('timeout'); };
    function failed(error) {
      if (!current() || settled) return;
      // Only an explicit missing-key response plus no contradictory key index proves a fresh key.
      if (present !== true && missingStorage(error)) return absent();
      noRealValue('async_failed');
    }
    function success(result) {
      if (!current() || settled) return;
      if (!result || !Object.prototype.hasOwnProperty.call(result,'data')) return noRealValue('async_empty');
      persist(result.data);
    }
    try {
      var task = api.getStorage({key: key, success: success, fail: failed, complete: function () {}});
      if (task && typeof task.then === 'function') task.then(success, failed);
    } catch (error) { failed(error); }
  }
  next();
};
// Backward-compatible numeric-only convenience entry. All callbacks/ownership use recoverTyped.
install.recoverNumeric = function (cc, api, specs, done, timeoutMs) {
  return install.recoverTyped(cc, api, specs.map(function(spec){
    var copy = {}; Object.keys(spec || {}).forEach(function(k){copy[k]=spec[k];});
    copy.type = copy.integer === false ? 'number' : 'integer'; return copy;
  }), done, timeoutMs);
};
module.exports = install;

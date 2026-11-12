'use strict';
// TikTok Platform Kit storage guard. Known SDK/bridge compatibility models, not a real-device verdict.
// New writes are text. A listed but unreadable legacy key is NOT a new player.
// SaveStore keys remain raw; its schema/recovery owns them. See cross-platform-runtime-contract.md.
var SAVESTORE_KEY = /:save:v\d+(:corrupt-backup)?$/;
function install(cc, api) {
  var root = typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this);
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
    if (value && typeof value === 'object') return JSON.stringify(value);
    return String(value);
  }
  function guard(storage) {
    if (!storage || typeof storage.getItem !== 'function' || storage.getItem.__tiktokKitStorageGuard) return false;
    var read = storage.getItem, write = storage.setItem, blocked = Object.create(null), knownAbsent = Object.create(null);
    function unreadable(key) {
      blocked[String(key)] = true; note(key, 'unreadable_preserved');
      var error = new Error('Stored value unreadable; preserve save and retry typed recovery: ' + String(key));
      error.code = 'TIKTOK_STORAGE_UNREADABLE'; error.key = String(key); return error;
    }
    var guardedRead = function (key) {
      var value;
      try { value = read.call(storage, key); }
      catch (error) {
        if (knownAbsent[String(key)]) return null;
        if (SAVESTORE_KEY.test(String(key))) throw error;
        if (listed(key, storage) === false) { note(key, 'throw_absent'); return null; }
        throw unreadable(key);
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
      // Unknown metadata is not proof of a fresh install. Do not default or overwrite it.
      throw unreadable(key);
    };
    guardedRead.__tiktokKitStorageGuard = true;
    guardedRead.__tiktokKitStorageState = {storage: storage, read: read, write: write, listed: function(key){return listed(key,storage);}, blocked: blocked, knownAbsent: knownAbsent, generation: 0, note: note};
    storage.getItem = guardedRead;
    if (typeof write === 'function') {
      var guardedWrite = function (key, value) {
        if (blocked[String(key)]) throw unreadable(key);
        if (typeof value !== 'string') { note(key, 'as_text_' + typeof value); value = text(value); }
        var result = write.call(storage, key, value); delete knownAbsent[String(key)]; return result;
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
// Call before game save consumers. Schema types: integer, number, boolean, string, json_object.
// No Boolean -> numeric guessing. Errors preserve data; caller owns bounded visible Retry/exit.
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
install.recoverTyped = function (cc, api, specs, done, timeoutMs) {
  var storage = cc && cc.sys && cc.sys.localStorage;
  if (!storage) {
    var root = typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : null);
    storage = root && root.localStorage;
  }
  var state = storage && storage.getItem && storage.getItem.__tiktokKitStorageState;
  if (!state || !api || !Array.isArray(specs) || typeof done !== 'function') throw Error('storage guard, SDK, schema and callback required');
  var token = ++state.generation, previous = state.cancelRecovery, ended = false, timer, lifecycle = false;
  var remaining = typeof timeoutMs === 'number' && timeoutMs > 0 ? timeoutMs : 5000, hidden = false, lastTime = Date.now();
  function accountTime() { var now=Date.now(); if (!hidden) remaining -= Math.max(0,now-lastTime); lastTime=now; }
  function onHide() { if (!current()) return; accountTime(); hidden=true; }
  function onShow() { if (!current()) return; hidden=false; lastTime=Date.now(); }
  function deadline() {
    if (!current()) return; accountTime();
    if (!hidden && remaining <= 0) return finish(Error('Typed storage recovery timed out; save preserved'));
    timer=setTimeout(deadline,hidden ? 250 : Math.max(1,Math.min(250,remaining)));
  }
  function current() { return !ended && state.generation === token; }
  function finish(error) {
    if (ended) return; ended = true; clearTimeout(timer);
    if (state.cancelRecovery === cancel) state.cancelRecovery = null;
    if (lifecycle) { try { api.offHide(onHide); } catch (ignore) {} try { api.offShow(onShow); } catch (ignore2) {} }
    done(error);
  }
  function cancel() { var error=Error('Typed storage recovery superseded; save preserved'); error.code='TIKTOK_STORAGE_SUPERSEDED'; finish(error); }
  // Own the batch BEFORE cancellation can run caller code and recursively start a newer batch.
  state.cancelRecovery = cancel;
  if (previous) previous();
  if (!current()) { cancel(); return; }
  var queue = specs.slice();
  if (typeof api.onHide === 'function' && typeof api.offHide === 'function' && typeof api.onShow === 'function' && typeof api.offShow === 'function') {
    lifecycle=true; try { api.onHide(onHide); api.onShow(onShow); } catch (ignore) { try {api.offHide(onHide);api.offShow(onShow);}catch(ignore2){} lifecycle=false; }
  }
  timer=setTimeout(deadline,hidden ? 250 : Math.max(1,Math.min(250,remaining)));
  function absent(key) { delete state.blocked[key]; state.knownAbsent[key] = true; state.note(key,'typed_confirmed_absent'); next(); }
  function next() {
    if (!current()) return;
    if (!queue.length) return finish();
    var spec = queue.shift();
    if (!spec || typeof spec.key !== 'string' || !spec.key || ['integer','number','boolean','string','json_object'].indexOf(spec.type) < 0)
      return finish(Error('Explicit typed legacy key schema required'));
    var key = spec.key, value, thrown = false;
    try { value = state.read.call(storage, key); } catch (error) { thrown = true; }
    var present = state.listed(key);
    // Boolean/sentinel/unknown empty reads can be bridge distortion, so validate them through async API.
    var ambiguous = thrown || value === null || value === undefined || typeof value === 'boolean' || value === '' && present !== true;
    var existing = !ambiguous && typedValue(value, spec);
    if (present === false && ambiguous) return absent(key);
    if (existing && typeof value === 'string') { delete state.blocked[key]; delete state.knownAbsent[key]; return next(); }
    state.blocked[key] = true;
    function persist(original) {
      if (!current()) return;
      var checked = typedValue(original, spec);
      if (!checked) return finish(Error('Typed storage value violates schema; save preserved: ' + key));
      try {
        state.write.call(storage, key, checked.text);
        if (state.read.call(storage, key) !== checked.text) throw Error('Typed storage recovery readback mismatch: ' + key);
        delete state.blocked[key]; delete state.knownAbsent[key]; state.note(key, 'typed_value_recovered'); next();
      } catch (error) { finish(error); }
    }
    if (existing) return persist(value);
    if (typeof api.getStorage !== 'function') return finish(Error('Typed storage API unavailable; save preserved: ' + key));
    var settled = false;
    function failed(error) {
      if (!current() || settled) return; settled = true;
      // Only an explicit missing-key response plus no contradictory key index proves a fresh key.
      if (present !== true && missingStorage(error)) return absent(key);
      finish(Error('Typed storage recovery failed; save preserved: ' + key));
    }
    function success(result) {
      if (!current() || settled) return; settled = true;
      if (!result || !Object.prototype.hasOwnProperty.call(result,'data')) return finish(Error('Typed storage data missing; save preserved: ' + key));
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

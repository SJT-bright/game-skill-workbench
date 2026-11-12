'use strict';
// TikTok Platform Kit storage guard. Known SDK/bridge compatibility models, not a real-device verdict.
// New writes are text. A listed but unreadable legacy key is NOT a new player.
// SaveStore keys remain raw; its schema/recovery owns them. See cross-platform-runtime-contract.md.
var SAVESTORE_KEY = /:save:v\d+(:corrupt-backup)?$/;
function install(cc, api) {
  var root = typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this);
  var log = root.__tiktokKitStorageEvents = root.__tiktokKitStorageEvents || [];
  function note(key, kind) { if (log.length < 60) log.push({key: String(key), kind: kind, at: Date.now()}); }
  function listed(key) {
    var list = [api, root.TTMinis && root.TTMinis.game, root.tt];
    for (var i = 0; i < list.length; i++) {
      var owner = list[i];
      if (!owner || typeof owner.getStorageInfoSync !== 'function') continue;
      try {
        var info = owner.getStorageInfoSync();
        if (info && Array.isArray(info.keys)) return info.keys.indexOf(String(key)) >= 0;
      } catch (ignore) {}
    }
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
    var read = storage.getItem, write = storage.setItem, blocked = Object.create(null);
    function unreadable(key) {
      blocked[String(key)] = true; note(key, 'unreadable_preserved');
      var error = new Error('Stored value unreadable; preserve save and retry typed recovery: ' + String(key));
      error.code = 'TIKTOK_STORAGE_UNREADABLE'; error.key = String(key); return error;
    }
    var guardedRead = function (key) {
      if (SAVESTORE_KEY.test(String(key))) return read.call(storage, key);
      var value;
      try { value = read.call(storage, key); }
      catch (error) {
        if (listed(key) === false) { note(key, 'throw_absent'); return null; }
        throw unreadable(key);
      }
      if (typeof value === 'string' && value !== '') return value;
      if (value && typeof value === 'object') return value;
      if (typeof value === 'number' && isFinite(value)) return String(value);
      var present = listed(key);
      if (value === '' && present === true) return '';
      if (present === false) { note(key, 'confirmed_absent'); return null; }
      // Unknown metadata is not proof of a fresh install. Do not default or overwrite it.
      throw unreadable(key);
    };
    guardedRead.__tiktokKitStorageGuard = true;
    guardedRead.__tiktokKitStorageState = {storage: storage, read: read, write: write, listed: listed, blocked: blocked, note: note};
    storage.getItem = guardedRead;
    if (typeof write === 'function') {
      var guardedWrite = function (key, value) {
        if (blocked[String(key)]) throw unreadable(key);
        if (typeof value !== 'string') { note(key, 'as_text_' + typeof value); value = text(value); }
        return write.call(storage, key, value);
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
// Call before game save consumers. `specs` comes from this game's numeric save schema, never all SDK keys.
// [{key:'wallet', min:0, max:..., integer:true}]. No inferred Boolean -> 0/1 conversions.
// Callback receives an error on unreadable/unknown/timeout; caller must show bounded Retry, not clear storage.
install.recoverNumeric = function (cc, api, specs, done, timeoutMs) {
  var storage = cc && cc.sys && cc.sys.localStorage;
  var state = storage && storage.getItem && storage.getItem.__tiktokKitStorageState;
  if (!state || !api || !Array.isArray(specs) || typeof done !== 'function') throw Error('storage guard, SDK, numeric schema and callback required');
  if (state.cancelRecovery) state.cancelRecovery();
  var ended = false, timer;
  function cancel() { finish(Error('Typed storage recovery superseded; save preserved')); }
  state.cancelRecovery = cancel;
  function finish(error) {
    if (ended) return; ended = true; clearTimeout(timer);
    if (state.cancelRecovery === cancel) state.cancelRecovery = null;
    done(error);
  }
  var queue = specs.slice();
  timer = setTimeout(function () { finish(Error('Typed storage recovery timed out; save preserved')); }, timeoutMs || 5000);
  function numeric(value, spec) {
    if (typeof value === 'string' && !/^-?(?:\d+(?:\.\d+)?)(?:[eE][+-]?\d+)?$/.test(value)) return false;
    if (typeof value !== 'number' && typeof value !== 'string') return false;
    var n = Number(value);
    return isFinite(n) && (spec.integer === false || Number.isSafeInteger(n)) &&
      (spec.min === undefined || n >= spec.min) && (spec.max === undefined || n <= spec.max);
  }
  function next() {
    if (ended) return;
    if (!queue.length) return finish();
    var spec = queue.shift();
    if (!spec || typeof spec.key !== 'string' || !spec.key || SAVESTORE_KEY.test(spec.key)) return finish(Error('Explicit numeric legacy key schema required'));
    var key = spec.key, value, thrown = false;
    try { value = state.read.call(storage, key); } catch (error) { thrown = true; }
    var present = state.listed(key);
    if (present === false) return next();
    if (!thrown && numeric(value, spec)) { delete state.blocked[key]; return next(); }
    state.blocked[key] = true;
    if (present !== true || typeof api.getStorage !== 'function') return finish(Error('Legacy numeric storage presence or typed API unavailable; save preserved: ' + key));
    var settled = false;
    function failed() { if (ended || settled) return; settled = true; finish(Error('Typed storage recovery failed; save preserved: ' + key)); }
    function success(result) {
      if (ended || settled) return; settled = true;
      var original = result && result.data;
      if (!numeric(original, spec)) return finish(Error('Typed storage value violates numeric schema; save preserved: ' + key));
      try {
        var encoded = String(original);
        state.write.call(storage, key, encoded);
        if (state.read.call(storage, key) !== encoded) throw Error('Typed storage recovery readback mismatch: ' + key);
        delete state.blocked[key]; state.note(key, 'typed_numeric_recovered'); next();
      } catch (error) { finish(error); }
    }
    try {
      var task = api.getStorage({key: key, success: success, fail: failed, complete: function () {}});
      if (task && typeof task.then === 'function') task.then(success, failed);
    } catch (error) { failed(); }
  }
  next();
};
module.exports = install;

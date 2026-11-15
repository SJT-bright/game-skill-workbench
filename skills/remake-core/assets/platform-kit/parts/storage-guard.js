'use strict';
// TikTok Platform Kit 2.0 storage layer (storage-guard.js). Copy unchanged; 待真机复测.
// Base: MergeShot2048 v85 storage-guard.js (sha 40aee1a4..., real-iPhone vConsole evidence 10-28/10-29),
// plus the key-list rule of TobinsGem / Tansys and the v7.5 SaveStore rule.
// TikTok storage does not behave like a browser:
//   - a key that was never written can read back as false, '' or undefined (SorensRivet, JaspersKelp,
//     Fenicks, AdasAmber, TobinsGem, GimblesGem, DoubleJumpDuo, Tansys, ThumbPinball);
//   - a raw number written with setItem(key, 3) can read back as the Boolean true (MergeShot2048).
// So, on cc.sys.localStorage (and window.localStorage when it is a different object):
//   1. setItem writes text only: numbers and Booleans become String(value), objects become JSON text.
//   2. getItem returning a non-empty string or an object hands it back unchanged; a number becomes text.
//   3. getItem returning null / undefined / '' / false / true asks getStorageInfoSync().keys whether the
//      key exists. Not listed (or no key list) = new player = null. Listed '' stays ''. Listed true/false/
//      undefined is a value the platform cannot hand back = null, so the game writes its default once.
//   4. A read that throws for a key the platform does not list is "no saved value" (null).
// install(cc, api) is idempotent: a second call on the same storage does nothing.
var SAVESTORE_KEY = /:save:v\d+(:corrupt-backup)?$/;
module.exports = function install(cc, api) {
  var root = typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this);
  var log = root.__tiktokKitStorageEvents = root.__tiktokKitStorageEvents || [];
  function note(key, kind) { if (log.length < 60) log.push({key: String(key), kind: kind, at: Date.now()}); }
  function owners() {
    return [api, root.TTMinis && root.TTMinis.game, root.tt];
  }
  function listed(key) {
    var list = owners();
    for (var i = 0; i < list.length; i++) {
      var owner = list[i];
      if (!owner || typeof owner.getStorageInfoSync !== 'function') continue;
      try {
        var info = owner.getStorageInfoSync();
        if (info && Array.isArray(info.keys)) return info.keys.indexOf(String(key)) >= 0;
      } catch (ignore) {}
    }
    return null; // key index unavailable
  }
  function text(value) {
    if (typeof value === 'string') return value;
    if (typeof value === 'number' || typeof value === 'boolean') return String(value);
    if (value && typeof value === 'object') { try { return JSON.stringify(value); } catch (e) { return String(value); } }
    return String(value);
  }
  function guard(storage) {
    if (!storage || typeof storage.getItem !== 'function' || storage.getItem.__tiktokKitStorageGuard) return false;
    var read = storage.getItem, write = storage.setItem;
    var guardedRead = function (key) {
      // SaveStore keys (<gameId>:<appId>:save:v1 and its :corrupt-backup) are read raw: SaveStore already
      // applies the same key-list rule itself and must keep telling "corrupt save" from "no save".
      if (SAVESTORE_KEY.test(String(key))) return read.call(storage, key);
      var value;
      try { value = read.call(storage, key); }
      catch (error) {
        if (listed(key) === false) { note(key, 'throw_absent'); return null; }
        throw error;
      }
      if (typeof value === 'string' && value !== '') return value;
      if (value && typeof value === 'object') return value;
      if (typeof value === 'number') return String(value);
      var present = listed(key);
      if (value === '' && present === true) return '';
      if (value !== null || present === true) {
        note(key, (present === true ? 'unreadable_' : 'absent_') + (value === '' ? 'empty' : String(value)));
      }
      return null;
    };
    guardedRead.__tiktokKitStorageGuard = true;
    storage.getItem = guardedRead;
    if (typeof write === 'function') {
      var guardedWrite = function (key, value) {
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
};

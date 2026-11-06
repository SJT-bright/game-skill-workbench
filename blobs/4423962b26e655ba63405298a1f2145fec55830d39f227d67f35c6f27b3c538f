/* Buy / make / refund as one transaction, for Cocos Creator 2.4 and 3.x (platform kit 2.0, 生成时预防 R4L3, 补查第 8 组).
 * One file for both engines. 2.4: copy it into assets/tiktok-platform/ and
 *   var ShopTx = require('ShopTx');
 * 3.x: import it as a plugin script (it also sets the global TikTokShopTx). It needs a SaveStore (grant()).
 *
 * Why (问题普查补查 第四节 8, 喵咪小吃铺): a furniture bought in room B was charged room A's price (the price was read
 * from a field the room tab had changed meanwhile); cancelling while the dish was cooking gave back the ingredients the
 * stove had already used; three fish made a dish that showed the meat result (the result picture was read from the
 * order list after it had moved to the next order); the apartment showed the same sample room twice. All four are one
 * mistake: a buy / make / refund read mutable globals at its end, had no lock, and wrote the save in pieces.
 *
 *   var shop = ShopTx.create(saveStore);                      // one per scene (or one per game)
 *   var tx = shop.begin('buy', {                              // null = this lock is busy (double tap, second button)
 *     lock: 'furniture:' + room.id + ':' + item.id,           // string or list; the same key cannot run twice at once
 *     buttons: [this.buyBtn, this.tabBar],                    // cc.Button or node with one: interactable = false meanwhile
 *     snapshot: {room: room.id, item: item.id, price: prices[room.id][item.id]},   // or a function; deep copy, frozen
 *     cost: {coins: prices[room.id][item.id]}                 // what it takes; top-level numbers or 'inventory.fish'
 *   });
 *   if (!tx) return;                                          // shop.lastRefusal = 'busy' | 'not_enough' | ...
 *   ... later, from the confirm button / the cook timer, read ONLY tx.snap (never this.currentPrice, orders[i]) ...
 *   tx.commit({add: {}, apply: function (d) { d.rooms[tx.snap.room].push(tx.snap.item); }}, function (r) { ... });
 *
 *   cook: begin('make', {lock: 'stove:1', snapshot: {order, recipe}, cost: {'inv.fish': 3}}); each step the stove really
 *   uses an ingredient: tx.consume({'inv.fish': 1}); done: tx.commit({add: {coins: tx.snap.recipe.price},
 *   apply: d => d.dishes.push(tx.snap.recipe.result)}); show tx.snap.recipe.result, never orders[current].
 *   cancel: tx.cancel(onDone) writes ONLY what consume() recorded; the rest of the cost was never taken.
 *
 * Rules this file enforces:
 *  - snapshot: taken once in begin() (a function is called once), deep-copied and frozen. Changing it throws in strict
 *    code; changing the game's tables afterwards does not change it.
 *  - lock: begin() with a busy key returns null and writes nothing. The listed buttons are not interactable until the
 *    transaction ends (commit ok, cancel ok, abort), then get back their own earlier value.
 *  - cost is reserved, not written: begin() refuses ('not_enough') when the save minus what other open transactions
 *    reserved is below it; shop.available(key) gives the number to show.
 *  - commit: ONE SaveStore.grant(): cost taken, reward added, apply(draft) changes, claim id, in one write. grant's id
 *    (default 'run:tx:<kind>:<n>:<time>', or opts.id such as 'order:' + order.id for a once-only order) means a second
 *    commit / a late callback never pays twice. A failed write changes nothing and keeps the transaction open (retry
 *    commit, or cancel). After the end every commit / cancel / consume returns {ok: false, error: 'closed'}.
 *  - cancel: refunds what was not consumed (= never takes it) and takes what consume() recorded, in one grant.
 *  - tx.guard(fn): a timer / animation callback that does nothing once the transaction has ended.
 *  - ShopTx.catalog(rows, {name, key}): sample / table rows with unique ids; a repeated id, or two rows the same apart
 *    from the id (the doubled sample room), throws at load. get(id) returns a frozen copy for snapshots.
 *
 * Proof: tests/shop-tx.test.js (the four 喵咪小吃铺 cases fail with the old code shape and pass through this part; two taps
 * pay once; a failed save changes nothing). Node only: 待真机复测.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module && module.exports) module.exports = api;
  if (root) root.TikTokShopTx = api;
})(typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this), function () {
  'use strict';
  var VERSION = '1.0.0';

  function isRecord(v) { return !!v && typeof v === 'object' && !Array.isArray(v); }
  function clone(v) { return v === undefined ? undefined : JSON.parse(JSON.stringify(v)); }
  function deepFreeze(v) {
    if (v && typeof v === 'object' && !Object.isFrozen(v)) {
      Object.freeze(v);
      Object.keys(v).forEach(function (k) { deepFreeze(v[k]); });
    }
    return v;
  }
  function num(v) {
    if (typeof v === 'number') return isFinite(v) ? v : null;
    if (typeof v === 'string' && v.trim() !== '' && isFinite(Number(v))) return Number(v);
    return null;
  }
  function pathGet(obj, key) {
    var parts = String(key).split('.');
    for (var i = 0; i < parts.length; i++) { if (!isRecord(obj)) return undefined; obj = obj[parts[i]]; }
    return obj;
  }
  // amounts: {key: n}; returns a clean copy or throws (a wrong amount is a code error, found on the first tap)
  function amounts(map, what) {
    var out = {};
    if (map === undefined || map === null) return out;
    if (!isRecord(map)) throw new Error('[ShopTx] ' + what + ' must be {key: number}');
    Object.keys(map).forEach(function (k) {
      var n = num(map[k]);
      if (n === null || n < 0) throw new Error('[ShopTx] ' + what + '.' + k + ' must be a number >= 0 (got ' + map[k] + ')');
      if (n > 0) out[k] = n;
    });
    return out;
  }
  function locksOf(lock, kind) {
    var list = lock === undefined || lock === null ? [kind] : (Array.isArray(lock) ? lock : [lock]);
    return list.map(String);
  }
  function buttonOf(b) {
    if (!b) return null;
    if (typeof b.interactable === 'boolean') return b;
    if (typeof b.getComponent === 'function') {
      var c = null;
      try { c = b.getComponent('cc.Button'); } catch (_) { c = null; }
      if (c && typeof c.interactable === 'boolean') return c;
    }
    return null;
  }

  function create(store, options) {
    if (!store || typeof store.grant !== 'function' || typeof store.get !== 'function') {
      throw new Error('[ShopTx] create(store): store must be the game\'s SaveStore (grant / get)');
    }
    options = options || {};
    var now = typeof options.now === 'function' ? options.now : Date.now;
    var log = typeof options.log === 'function' ? options.log : function (line) {
      if (typeof console !== 'undefined' && console.warn) console.warn(line);
    };
    var held = {};          // lock key -> tx
    var open = [];          // open transactions (for reservations)
    var seq = 0;
    var shop = {lastRefusal: null};

    function reservedBy(key, except) {
      var sum = 0;
      open.forEach(function (t) { if (t !== except && t._left[key]) sum += t._left[key]; });
      return sum;
    }
    function saved(key) { var n = num(pathGet(store.get(), key)); return n === null ? 0 : n; }

    shop.available = function (key) { return saved(key) - reservedBy(key, null); };
    shop.isBusy = function (lock) { return locksOf(lock, '').some(function (k) { return !!held[k]; }); };
    shop.openCount = function () { return open.length; };
    shop.abortAll = function () { open.slice().forEach(function (t) { t.abort(); }); };   // leaving the scene

    shop.begin = function (kind, opts) {
      opts = opts || {};
      kind = String(kind || 'tx');
      var keys = locksOf(opts.lock, kind);
      for (var i = 0; i < keys.length; i++) {
        if (held[keys[i]]) { shop.lastRefusal = 'busy'; return null; }
      }
      var cost = amounts(opts.cost, 'cost');
      var short = Object.keys(cost).filter(function (k) { return saved(k) - reservedBy(k, null) < cost[k]; });
      if (short.length) { shop.lastRefusal = 'not_enough'; shop.lastShort = short; return null; }
      var snap = typeof opts.snapshot === 'function' ? opts.snapshot() : opts.snapshot;
      snap = deepFreeze(clone(snap === undefined ? {} : snap));
      seq += 1;
      var started = Number(now());
      var tx = {
        kind: kind,
        id: opts.id !== undefined && opts.id !== null && opts.id !== '' ? String(opts.id)
          : 'run:tx:' + kind + ':' + seq + ':' + (isFinite(started) ? started : 0),
        snap: snap,
        cost: deepFreeze(clone(cost)),
        state: 'open',
        _left: clone(cost),      // reserved and not consumed
        _used: {}                // consumed (taken on commit and on cancel)
      };
      var buttons = [];
      (opts.buttons || []).forEach(function (b) {
        var btn = buttonOf(b);
        if (btn && buttons.every(function (x) { return x.btn !== btn; })) { buttons.push({btn: btn, was: btn.interactable}); btn.interactable = false; }
      });
      keys.forEach(function (k) { held[k] = tx; });
      open.push(tx);

      function end(state) {
        if (tx.state !== 'open') return;
        tx.state = state;
        keys.forEach(function (k) { if (held[k] === tx) delete held[k]; });
        var at = open.indexOf(tx);
        if (at >= 0) open.splice(at, 1);
        buttons.forEach(function (b) { try { b.btn.interactable = b.was; } catch (_) {} });
      }
      function closed() { return {ok: false, error: 'closed', state: tx.state}; }

      // grant() with top-level numbers in add and dotted keys (inventory.fish) inside the same write.
      function write(id, delta, apply, onDone) {
        var top = {}, nested = {}, problem = null;
        Object.keys(delta).forEach(function (k) {
          if (!delta[k]) return;
          if (k.indexOf('.') < 0) top[k] = delta[k]; else nested[k] = delta[k];
        });
        var r = store.grant({id: id, add: top, apply: function (draft) {
          var keys2 = Object.keys(nested);
          for (var j = 0; j < keys2.length; j++) {
            var parts = keys2[j].split('.'), last = parts.pop(), parent = draft;
            for (var p = 0; p < parts.length; p++) {
              if (!isRecord(parent[parts[p]])) { if (nested[keys2[j]] < 0) { problem = 'not_enough'; return false; } parent[parts[p]] = {}; }
              parent = parent[parts[p]];
            }
            var have = num(parent[last]); if (have === null) have = 0;
            if (have + nested[keys2[j]] < 0) { problem = 'not_enough'; return false; }
            parent[last] = have + nested[keys2[j]];
          }
          if (apply && apply(draft) === false) { problem = 'cancelled'; return false; }
        }}, onDone);
        if (!r.ok && problem) r.error = problem;
        return r;
      }

      tx.consume = function (part) {
        if (tx.state !== 'open') return closed();
        var use = amounts(part, 'consume');
        var keys3 = Object.keys(use);
        for (var j = 0; j < keys3.length; j++) {
          if (!(tx._left[keys3[j]] >= use[keys3[j]])) return {ok: false, error: 'more_than_reserved', key: keys3[j]};
        }
        keys3.forEach(function (k) {
          tx._left[k] -= use[k]; if (!tx._left[k]) delete tx._left[k];
          tx._used[k] = (tx._used[k] || 0) + use[k];
        });
        return {ok: true, used: clone(tx._used), left: clone(tx._left)};
      };

      // commit({add: {coins: 50}, apply(draft)}, onDone): the whole cost (consumed or not) is taken here.
      tx.commit = function (result, onDone) {
        if (tx.state !== 'open') { var c = closed(); if (tx.state === 'committed') { c.ok = true; c.already = true; c.error = null; } return c; }
        result = result || {};
        var add = amounts(result.add, 'add'), delta = {};
        Object.keys(tx.cost).forEach(function (k) { delta[k] = (delta[k] || 0) - tx.cost[k]; });
        Object.keys(add).forEach(function (k) { delta[k] = (delta[k] || 0) + add[k]; });
        var r = write(tx.id, delta, typeof result.apply === 'function' ? result.apply : null, null);
        if (r.ok) {
          end('committed');
          if (typeof onDone === 'function') { try { onDone(r); } catch (e) { log('[ShopTx] commit onDone: ' + (e && e.message || e)); } }
        }
        return r;   // failed: nothing changed, still open (retry commit or cancel)
      };

      // cancel(onDone): only what consume() recorded is taken; the rest of the cost never left the save.
      tx.cancel = function (onDone) {
        if (tx.state !== 'open') return closed();
        var delta = {}, any = false;
        Object.keys(tx._used).forEach(function (k) { delta[k] = -tx._used[k]; any = true; });
        var r = any ? write(tx.id + ':cancel', delta, null, null) : {ok: true, error: null, already: false, data: store.get()};
        if (r.ok) {
          end('cancelled');
          r.refunded = clone(tx._left);
          r.used = clone(tx._used);
          if (typeof onDone === 'function') { try { onDone(r); } catch (e) { log('[ShopTx] cancel onDone: ' + (e && e.message || e)); } }
        }
        return r;
      };

      // abort(): leave without writing (scene destroyed before anything was consumed). Consumed amounts are logged.
      tx.abort = function () {
        if (tx.state !== 'open') return closed();
        if (Object.keys(tx._used).length) log('[ShopTx] ' + tx.kind + ' aborted with consumed ' + JSON.stringify(tx._used) + ' not written: call cancel() instead');
        end('aborted');
        return {ok: true};
      };

      tx.guard = function (fn) {
        return function () { if (tx.state !== 'open') return undefined; return fn.apply(this, arguments); };
      };
      tx.isOpen = function () { return tx.state === 'open'; };
      shop.lastRefusal = null;
      return tx;
    };
    return shop;
  }

  // Table / sample rows with one id each. A repeated id or two rows equal apart from the id throw (dev and release:
  // the data is wrong, not the player). opts.same: true allows equal rows (for real duplicates such as two plain tiles).
  function catalog(rows, opts) {
    opts = opts || {};
    var key = opts.key || 'id', name = opts.name || 'catalog';
    if (!Array.isArray(rows)) throw new Error('[ShopTx] catalog ' + name + ': rows must be a list');
    var byId = {}, seen = {}, order = [];
    rows.forEach(function (row, i) {
      if (!isRecord(row)) throw new Error('[ShopTx] catalog ' + name + ' row ' + i + ' is not an object');
      var id = row[key];
      if (id === undefined || id === null || id === '') throw new Error('[ShopTx] catalog ' + name + ' row ' + i + ' has no ' + key);
      id = String(id);
      if (Object.prototype.hasOwnProperty.call(byId, id)) throw new Error('[ShopTx] catalog ' + name + ': ' + key + ' ' + id + ' appears twice (rows ' + byId[id].i + ' and ' + i + ')');
      var body = clone(row); delete body[key];
      var text = JSON.stringify(sortKeys(body));
      if (!opts.same && Object.prototype.hasOwnProperty.call(seen, text)) {
        throw new Error('[ShopTx] catalog ' + name + ': rows ' + seen[text] + ' and ' + id + ' are the same apart from ' + key + ' (a copied sample)');
      }
      seen[text] = id;
      byId[id] = {i: i, row: deepFreeze(clone(row))};
      order.push(id);
    });
    return {
      ids: function () { return order.slice(); },
      has: function (id) { return Object.prototype.hasOwnProperty.call(byId, String(id)); },
      get: function (id) {
        var hit = byId[String(id)];
        if (!hit) throw new Error('[ShopTx] catalog ' + name + ': no ' + key + ' ' + id);
        return hit.row;
      },
      size: order.length
    };
  }
  function sortKeys(v) {
    if (Array.isArray(v)) return v.map(sortKeys);
    if (!isRecord(v)) return v;
    var out = {};
    Object.keys(v).sort().forEach(function (k) { out[k] = sortKeys(v[k]); });
    return out;
  }

  return {VERSION: VERSION, create: create, catalog: catalog};
});

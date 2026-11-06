'use strict';
// node tests/shop-tx.test.js  -- parts/ShopTx.js (生成时预防 R4L3, 补查第 8 组, 喵咪小吃铺 4 cases).
// Every case runs twice: the old code shape (globals read at the end, no lock, save written in pieces) must give the
// wrong result, and the same flow through ShopTx must give the right one. Plus: two taps pay once, a failed save changes
// nothing and keeps the transaction open, buttons are locked and restored, reservations, late callbacks dropped.
// SHOP_TX_FILE: run the same checks on a broken copy (mutation check in the patch's test record).
var assert = require('assert');
var path = require('path');
var FILE = process.env.SHOP_TX_FILE || path.join(__dirname, '..', 'parts', 'ShopTx.js');
delete require.cache[require.resolve(FILE)];
var ShopTx = require(FILE);
var SaveStore = require(path.join(__dirname, '..', 'assets', 'tiktok-platform', 'SaveStore.js'));

var passed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('ok   ' + name); }
  catch (e) { console.log('FAIL ' + name + '\n     ' + (e && e.stack || e)); process.exitCode = 1; }
}
function memStorage() {
  var m = {}, broken = false;
  return {
    getItem: function (k) { return Object.prototype.hasOwnProperty.call(m, k) ? m[k] : null; },
    setItem: function (k, v) { if (broken) throw new Error('disk full'); m[k] = String(v); },
    keys: function () { return Object.keys(m); },
    breakWrites: function (b) { broken = b; },
    raw: m
  };
}
function newStore(extra) {
  var storage = memStorage();
  var defaults = Object.assign({coins: 1000, inv: {fish: 10, meat: 10}, rooms: {A: [], B: []}, dishes: []}, extra || {});
  var store = new SaveStore(defaults, {key: 'shop-tx-test', storage: storage, storageKeys: function () { return storage.keys(); },
    login: false, schema: false, log: function () {}});
  store.load();
  store._storage = storage;
  return store;
}
// what is on disk (a new save is not written until its first update: then the defaults are what a reload gives)
function saved(store) { var t = store._storage.raw['shop-tx-test']; return t === undefined ? JSON.parse(JSON.stringify(store.defaults)) : JSON.parse(t); }
function writes(store) {               // counts setItem calls from now on
  var n = {count: 0}, orig = store._storage.setItem;
  store._storage.setItem = function (k, v) { if (k === 'shop-tx-test') n.count++; return orig.call(this, k, v); };
  return n;
}
var PRICES = {A: {sofa: 100, lamp: 40}, B: {sofa: 300, lamp: 90}};

// ---------- case 1: 家具跨房间复用价格 (T13:room_price_reused) ----------
// Old shape (节选自喵咪小吃铺的写法): the price is cached per item, and the confirm popup reads the current room field.
function oldShop(store) {
  var game = {room: 'A', item: null, priceCache: {}};
  function priceOf(item) { return game.priceCache[item] || (game.priceCache[item] = PRICES[game.room][item]); }
  return {
    enter: function (room) { game.room = room; },
    open: function (item) { game.item = item; game.price = priceOf(item); },
    confirm: function () {
      store.update(function (d) { d.coins -= game.price; });           // write 1
      store.update(function (d) { d.rooms[game.room].push(game.item); });   // write 2
    }
  };
}
function newShop(store, shop) {
  var tx = null;
  return {
    open: function (room, item) {
      tx = shop.begin('buy', {lock: 'furniture:' + room + ':' + item,
        snapshot: {room: room, item: item, price: PRICES[room][item]}, cost: {coins: PRICES[room][item]}});
      return tx;
    },
    confirm: function () {
      var t = tx;
      return t.commit({apply: function (d) { d.rooms[t.snap.room].push(t.snap.item); }});
    }
  };
}
test('1 old: sofa in room B is charged room A\'s cached price (must be wrong)', function () {
  var store = newStore(), s = oldShop(store);
  s.enter('A'); s.open('sofa'); s.confirm();
  s.enter('B'); s.open('sofa'); s.confirm();
  assert.strictEqual(saved(store).coins, 1000 - 100 - 100);            // room B sofa cost 100, should be 300
  assert.notStrictEqual(saved(store).coins, 1000 - 100 - 300);
});
test('1 old: room tab changed while the confirm popup is open: item lands in the other room (must be wrong)', function () {
  var store = newStore(), s = oldShop(store);
  s.enter('A'); s.open('lamp'); s.enter('B'); s.confirm();
  assert.deepStrictEqual(saved(store).rooms, {A: [], B: ['lamp']});
});
test('1 ShopTx: each room charges its own price; switching tabs after begin changes nothing', function () {
  var store = newStore(), shop = ShopTx.create(store), s = newShop(store, shop);
  assert.ok(s.open('A', 'sofa')); assert.ok(s.confirm().ok);
  assert.ok(s.open('B', 'sofa')); assert.ok(s.confirm().ok);
  assert.strictEqual(saved(store).coins, 1000 - 100 - 300);
  var t = s.open('A', 'lamp');
  PRICES.A.lamp = 999;                                                  // a table change after begin
  try { assert.ok(s.confirm().ok); } finally { PRICES.A.lamp = 40; }
  assert.strictEqual(t.snap.price, 40);
  assert.deepStrictEqual(saved(store).rooms, {A: ['sofa', 'lamp'], B: ['sofa']});
  assert.strictEqual(saved(store).coins, 1000 - 100 - 300 - 40);
});
test('1 ShopTx: the snapshot is frozen (writing to it throws in strict code)', function () {
  var store = newStore(), shop = ShopTx.create(store), src = {price: 5, nested: {a: 1}};
  var tx = shop.begin('buy', {snapshot: src});
  assert.throws(function () { tx.snap.price = 1; });
  assert.throws(function () { tx.snap.nested.a = 2; });
  src.price = 77; assert.strictEqual(tx.snap.price, 5);
  var calls = 0, t2 = shop.begin('buy2', {snapshot: function () { calls++; return {x: 1}; }});
  assert.strictEqual(calls, 1); assert.strictEqual(t2.snap.x, 1);
});

// ---------- case 2: 制作等待时取消退回已消耗的食材 (T13:consumed_ingredient_refunded) ----------
function oldCook(store) {
  var cooking = null;
  return {
    start: function () { store.update(function (d) { d.inv.fish -= 3; }); cooking = {used: 0}; },
    step: function () { cooking.used++; },                              // the stove uses one fish per step
    cancel: function () { store.update(function (d) { d.inv.fish += 3; }); cooking = null; }
  };
}
test('2 old: cancel after 2 of 3 fish were used gives all 3 back (must be wrong)', function () {
  var store = newStore(), c = oldCook(store);
  c.start(); c.step(); c.step(); c.cancel();
  assert.strictEqual(saved(store).inv.fish, 10);                       // should be 8
});
test('2 ShopTx: cancel takes only the consumed fish, in one write; available() shows the reservation', function () {
  var store = newStore(), shop = ShopTx.create(store);
  var tx = shop.begin('make', {lock: 'stove:1', cost: {'inv.fish': 3}});
  assert.strictEqual(shop.available('inv.fish'), 7);
  assert.strictEqual(saved(store).inv.fish, 10);                       // reserved, not written
  assert.ok(tx.consume({'inv.fish': 1}).ok); assert.ok(tx.consume({'inv.fish': 1}).ok);
  assert.strictEqual(tx.consume({'inv.fish': 2}).error, 'more_than_reserved');
  var w = writes(store), r = tx.cancel();
  assert.ok(r.ok); assert.strictEqual(w.count, 1);
  assert.deepStrictEqual(r.refunded, {'inv.fish': 1}); assert.deepStrictEqual(r.used, {'inv.fish': 2});
  assert.strictEqual(saved(store).inv.fish, 8);
  assert.strictEqual(shop.available('inv.fish'), 8);
  assert.strictEqual(tx.cancel().error, 'closed');
  assert.strictEqual(saved(store).inv.fish, 8);
});
test('2 ShopTx: cancel before any step writes nothing; a late timer callback after cancel does nothing', function () {
  var store = newStore(), shop = ShopTx.create(store), ran = 0;
  var tx = shop.begin('make', {lock: 'stove:1', cost: {'inv.fish': 3}});
  var late = tx.guard(function () { ran++; tx.consume({'inv.fish': 1}); });
  var w = writes(store);
  assert.ok(tx.cancel().ok); assert.strictEqual(w.count, 0);
  late(); assert.strictEqual(ran, 0);
  assert.strictEqual(saved(store).inv.fish, 10);
});
test('2 ShopTx: two stoves cannot reserve more fish than the save has', function () {
  var store = newStore({inv: {fish: 5, meat: 0}}), shop = ShopTx.create(store);
  assert.ok(shop.begin('make', {lock: 'stove:1', cost: {'inv.fish': 3}}));
  assert.strictEqual(shop.begin('make', {lock: 'stove:2', cost: {'inv.fish': 3}}), null);
  assert.strictEqual(shop.lastRefusal, 'not_enough');
});

// ---------- case 3: 三条鱼合成却显示肉类成品 (T15:recipe_result_mismatch) ----------
var RECIPES = {fishStew: {need: {'inv.fish': 3}, result: 'fish_stew.png', price: 60}, meatPie: {need: {'inv.meat': 3}, result: 'meat_pie.png', price: 80}};
var ORDERS = [{id: 'o1', recipe: 'fishStew'}, {id: 'o2', recipe: 'meatPie'}];
function oldKitchen(store) {
  var g = {current: 0, shown: null};
  return {
    start: function () { var o = ORDERS[g.current]; store.update(function (d) { d.inv.fish -= RECIPES[o.recipe].need['inv.fish'] || 0; }); },
    nextOrder: function () { g.current++; },                           // the counter moves on while the dish cooks
    done: function () {
      var r = RECIPES[ORDERS[g.current].recipe];                       // read at the end: the next order
      store.update(function (d) { d.dishes.push(r.result); d.coins += r.price; });
      g.shown = r.result; return g.shown;
    }
  };
}
test('3 old: three fish cooked, the next order\'s meat result is shown and paid (must be wrong)', function () {
  var store = newStore(), k = oldKitchen(store);
  k.start(); k.nextOrder();
  assert.strictEqual(k.done(), 'meat_pie.png');
  assert.strictEqual(saved(store).coins, 1080);
});
test('3 ShopTx: the result comes from the snapshot of the order taken at begin', function () {
  var store = newStore(), shop = ShopTx.create(store), current = 0;
  var o = ORDERS[current], tx = shop.begin('make', {lock: 'stove:1',
    snapshot: function () { return {order: o, recipe: RECIPES[o.recipe]}; }, cost: RECIPES[o.recipe].need});
  current++;                                                            // counter moves on
  ['inv.fish', 'inv.fish', 'inv.fish'].forEach(function (k) { var p = {}; p[k] = 1; tx.consume(p); });
  var w = writes(store);
  var r = tx.commit({add: {coins: tx.snap.recipe.price}, apply: function (d) { d.dishes.push(tx.snap.recipe.result); }});
  assert.ok(r.ok); assert.strictEqual(w.count, 1);
  assert.strictEqual(tx.snap.recipe.result, 'fish_stew.png');
  var s = saved(store);
  assert.deepStrictEqual(s.dishes, ['fish_stew.png']); assert.strictEqual(s.coins, 1060); assert.strictEqual(s.inv.fish, 7);
});

// ---------- case 4: 重复的示例房间 (T15:duplicate_sample_room) ----------
var SAMPLE_ROOMS = [{id: 'apt1', layout: ['bed', 'desk'], price: 200}, {id: 'apt2', layout: ['sofa'], price: 300}];
test('4 old: a copied sample room is shown twice (must be wrong)', function () {
  var rows = SAMPLE_ROOMS.concat([{id: 'apt3', layout: ['bed', 'desk'], price: 200}]);   // copy-pasted, id changed
  var shown = rows.map(function (r) { return r.id; });                 // old code just renders the list
  assert.strictEqual(shown.length, 3);
});
test('4 ShopTx.catalog: a repeated id and a copy apart from the id both throw at load', function () {
  assert.throws(function () { ShopTx.catalog(SAMPLE_ROOMS.concat([{id: 'apt1', layout: ['x'], price: 1}]), {name: 'rooms'}); }, /appears twice/);
  assert.throws(function () { ShopTx.catalog(SAMPLE_ROOMS.concat([{id: 'apt3', layout: ['bed', 'desk'], price: 200}]), {name: 'rooms'}); }, /same apart from id/);
  assert.throws(function () { ShopTx.catalog([{layout: []}], {name: 'rooms'}); }, /has no id/);
  var cat = ShopTx.catalog(SAMPLE_ROOMS, {name: 'rooms'});
  assert.deepStrictEqual(cat.ids(), ['apt1', 'apt2']);
  assert.throws(function () { cat.get('apt1').price = 1; });
  assert.ok(ShopTx.catalog([{id: 't1', kind: 'plain'}, {id: 't2', kind: 'plain'}], {same: true}).size === 2);
});

// ---------- double tap / concurrent taps ----------
test('old: two taps on confirm charge twice (must be wrong)', function () {
  var store = newStore(), s = oldShop(store);
  s.enter('A'); s.open('sofa'); s.confirm(); s.confirm();
  assert.strictEqual(saved(store).coins, 800);
  assert.deepStrictEqual(saved(store).rooms.A, ['sofa', 'sofa']);
});
test('ShopTx: two taps on buy -> second begin is refused; two taps on confirm -> paid once', function () {
  var store = newStore(), shop = ShopTx.create(store);
  var a = shop.begin('buy', {lock: 'furniture:A:sofa', cost: {coins: 100}, snapshot: {room: 'A', item: 'sofa'}});
  var b = shop.begin('buy', {lock: 'furniture:A:sofa', cost: {coins: 100}});
  assert.ok(a); assert.strictEqual(b, null); assert.strictEqual(shop.lastRefusal, 'busy');
  var w = writes(store);
  var apply = function (d) { d.rooms.A.push('sofa'); };
  assert.ok(a.commit({apply: apply}).ok);
  var again = a.commit({apply: apply});
  assert.ok(again.ok && again.already);
  assert.strictEqual(w.count, 1);
  assert.strictEqual(saved(store).coins, 900); assert.deepStrictEqual(saved(store).rooms.A, ['sofa']);
});
test('ShopTx: two buttons sharing a lock list (buy + sell of one item) cannot run at once', function () {
  var store = newStore(), shop = ShopTx.create(store);
  var a = shop.begin('buy', {lock: ['item:sofa', 'wallet']});
  assert.strictEqual(shop.begin('sell', {lock: ['item:sofa']}), null);
  assert.ok(shop.isBusy('wallet'));
  a.abort(); assert.ok(shop.begin('sell', {lock: ['item:sofa']}));
});
test('ShopTx: the same once-only order id never pays twice, even from a new transaction', function () {
  var store = newStore(), shop = ShopTx.create(store);
  assert.ok(shop.begin('make', {id: 'order:o1'}).commit({add: {coins: 50}}).ok);
  var r = shop.begin('make', {id: 'order:o1'}).commit({add: {coins: 50}});
  assert.ok(r.ok && r.already); assert.strictEqual(saved(store).coins, 1050);
});

// ---------- buttons, failed save ----------
test('ShopTx: listed buttons are not interactable meanwhile and get their own value back', function () {
  var store = newStore(), shop = ShopTx.create(store);
  var btn = {interactable: true}, off = {interactable: false}, comp = {interactable: true};
  var node = {getComponent: function (n) { return n === 'cc.Button' ? comp : null; }};
  var tx = shop.begin('buy', {buttons: [btn, off, node, null, {}]});
  assert.strictEqual(btn.interactable, false); assert.strictEqual(comp.interactable, false);
  tx.commit({});
  assert.strictEqual(btn.interactable, true); assert.strictEqual(off.interactable, false); assert.strictEqual(comp.interactable, true);
});
test('ShopTx: a failed save changes nothing, keeps the lock and the buttons, and a retry pays once', function () {
  var store = newStore(), shop = ShopTx.create(store), btn = {interactable: true}, done = 0;
  var tx = shop.begin('buy', {lock: 'x', buttons: [btn], cost: {coins: 100}});
  store._storage.breakWrites(true);
  var r = tx.commit({apply: function (d) { d.rooms.A.push('sofa'); }}, function () { done++; });
  assert.strictEqual(r.ok, false); assert.strictEqual(done, 0);
  assert.strictEqual(store.get().coins, 1000); assert.deepStrictEqual(store.get().rooms.A, []);
  assert.ok(tx.isOpen()); assert.ok(shop.isBusy('x')); assert.strictEqual(btn.interactable, false);
  store._storage.breakWrites(false);
  assert.ok(tx.commit({apply: function (d) { d.rooms.A.push('sofa'); }}, function () { done++; }).ok);
  assert.strictEqual(done, 1); assert.strictEqual(saved(store).coins, 900); assert.strictEqual(btn.interactable, true);
});
test('ShopTx: commit refuses when the save cannot pay (spent elsewhere meanwhile) and writes nothing', function () {
  var store = newStore({inv: {fish: 3, meat: 0}}), shop = ShopTx.create(store);
  var tx = shop.begin('make', {cost: {'inv.fish': 3}});
  store.update(function (d) { d.inv.fish = 1; });                      // another code path spent it
  var r = tx.commit({add: {coins: 10}});
  assert.strictEqual(r.ok, false); assert.strictEqual(r.error, 'not_enough');
  assert.strictEqual(saved(store).coins, 1000); assert.ok(tx.isOpen());
});
test('ShopTx: create() without a SaveStore and wrong amounts fail loudly', function () {
  assert.throws(function () { ShopTx.create({}); }, /SaveStore/);
  var shop = ShopTx.create(newStore());
  assert.throws(function () { shop.begin('buy', {cost: {coins: -5}}); }, />= 0/);
  assert.throws(function () { shop.begin('buy', {cost: {coins: 'x'}}); }, /number/);
});

console.log((process.exitCode ? 'FAILED' : 'all passed') + ' (' + passed + ' passed)');

'use strict';
// Engine-independent ownership for asynchronous modal UI. Not auto-installed into old games.
// Supply isAlive()/disposeNode() for the game's Cocos 2.x/3.x lifetime. Resources/cache are separate.
function ModalOwner(options) {
  options = options || {};
  this.isAlive = options.isAlive || function () { return true; };
  this.disposeNode = options.disposeNode || function (node) { if (node && node.destroy) node.destroy(); };
  this.entries = new Map();
  this.singletons = new Map();
  this.nodes = new Map();
  this.nextId = 0;
  this.disposed = false;
}

ModalOwner.prototype.begin = function (key, options) {
  if (typeof key !== 'string' || !key) throw new Error('ModalOwner.begin needs a stable route key');
  if (this.disposed || !this.isAlive()) throw new Error('ModalOwner has no live owner');
  options = options || {};
  var existing = this.singletons.get(key);
  if (options.singleton !== false && existing && existing.current()) return {created: false, session: existing};
  var owner = this;
  var s = {
    id: ++this.nextId, key: key, state: 'opening', root: null, view: null, blocker: null,
    cleanup: [], nodes: new Set(),
    current: function () { return !owner.disposed && owner.isAlive() && owner.entries.get(s.id) === s && s.state !== 'closed'; },
    // Hold releases for this session only (e.g. an input/pause token). No global unlock/reset.
    hold: function (release) {
      if (typeof release !== 'function') throw new Error('hold needs a release function');
      if (!s.current()) { release(); return false; }
      s.cleanup.push(release); return true;
    },
    mount: function (root, view, blocker) { return owner.mount(s, root, view, blocker); },
    close: function () { return owner.close(s); }
  };
  this.entries.set(s.id, s);
  if (options.singleton !== false) this.singletons.set(key, s);
  return {created: true, session: s};
};

function below(node, parent) {
  for (var n = node; n; n = n.parent) if (n === parent) return true;
  return false;
}

ModalOwner.prototype.mount = function (s, root, view, blocker) {
  if (!root || !view || root === view || (blocker && (blocker === root || blocker === view))) {
    throw new Error('mount requires a distinct container, view and optional blocker');
  }
  var parts = [root, view, blocker].filter(Boolean), owner = this;
  // Separate session containers must not contain one another. Use sibling roots for
  // stacked modals; parenting a modal inside another would destroy the child while
  // leaving its input/pause token alive. Also protect an entire stale result subtree.
  parts.forEach(function (n) {
    owner.nodes.forEach(function (held, owned) {
      if (held !== s && (below(n, owned) || below(owned, n))) {
        throw new Error('modal subtree overlaps another session; use sibling session containers');
      }
    });
  });
  if (!s.current()) {
    // Own late-created UI only; do not dispose shared textures/cache or another session's UI.
    if (!this.nodes.has(root)) this.disposeNode(root);
    parts.slice(1).forEach(function (n) { if (!below(n, root) && !owner.nodes.has(n)) owner.disposeNode(n); });
    return false;
  }
  if (!below(view, root) || (blocker && !below(blocker, root))) {
    throw new Error('view and blocker must share their session container');
  }
  if (s.state === 'visible') {
    if (s.root === root && s.view === view && s.blocker === (blocker || null)) return true;
    throw new Error('duplicate mount: dispose the extra result, do not replace a visible modal');
  }
  parts.forEach(function (n) { owner.nodes.set(n, s); s.nodes.add(n); });
  s.root = root; s.view = view; s.blocker = blocker || null; s.state = 'visible';
  return true;
};

ModalOwner.prototype.close = function (s) {
  if (this.entries.get(s.id) !== s || s.state === 'closed') return false;
  // Revoke the token BEFORE cleanup: reentrant opens and late callbacks cannot regain ownership.
  this.entries.delete(s.id);
  if (this.singletons.get(s.key) === s) this.singletons.delete(s.key);
  s.state = 'closed';
  var owner = this, failures = [];
  s.nodes.forEach(function (n) { if (owner.nodes.get(n) === s) owner.nodes.delete(n); });
  if (s.root) {
    // Cocos destruction may be deferred to end of frame: stop input capture immediately.
    try { s.root.active = false; } catch (e) { failures.push(e); }
    try { this.disposeNode(s.root); } catch (e) { failures.push(e); }
  }
  s.cleanup.splice(0).reverse().forEach(function (release) { try { release(); } catch (e) { failures.push(e); } });
  s.nodes.clear();
  if (failures.length) { var error = new Error('modal cleanup failed'); error.causes = failures; throw error; }
  return true;
};

ModalOwner.prototype.dispose = function () {
  if (this.disposed) return;
  this.disposed = true;
  var owner = this, failures = [];
  Array.from(this.entries.values()).forEach(function (s) { try { owner.close(s); } catch (e) { failures.push(e); } });
  if (failures.length) { var error = new Error('modal owner cleanup failed'); error.causes = failures; throw error; }
};

module.exports = ModalOwner;

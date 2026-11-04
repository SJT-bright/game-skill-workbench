'use strict';
// TikTok Platform Kit 2.0 - fixed home entries: "Add to Home Screen" and "Profile Revisit". Copy unchanged.
// 待真机复测 (Node-tested only: tests/home-entries.test.js). 简化.11.3: one tap goes to TikTok; the reward is checked on return.
//
// Put two button nodes in the home bottom row (nothing else goes in that row, rule U3), add this
// component to their parent, drag the two nodes into shortcutNode / profileNode, then from the home scene:
//     this.getComponent('HomeGrowthEntries').init(saveStore, {onGranted: function (kind, data) { ...top bar... }});
// The reward is ALWAYS PlatformConfig.growthReward() (5B in this game's currency, Saul 2026-10-29);
// there is no option to change it. MissionFlow does the platform calls (TTMinis.game -> tt -> wx).
// Rules taken from earlier games:
//  - the entries are always shown, also in a browser (ThumbPinball / GimblesGem hid them, nobody saw them);
//  - without the TikTok runtime a tap shows "Available in TikTok" (never a fake success, TovesTulip/AdasAmber);
//  - an entry whose icon did not load shows its text instead of an empty box;
//  - taps during a request are merged and a reward is paid once per entry per save.
var MissionFlow = require('./MissionFlow');

var TEXT = {
  shortcut: 'Add to Home',
  profile: 'Profile Revisit',
  unsupported: 'Available in TikTok',
  collected: 'Collected'
};
var ICON_WAIT_MS = 2000;

function Controller(options) {
  options = options || {};
  if (!options.store) throw new Error('HomeGrowthEntries needs the game SaveStore');
  var self = this;
  this.config = options.config || require('./PlatformConfig');
  this.toast = typeof options.toast === 'function' ? options.toast : function () {};
  this.renderState = typeof options.render === 'function' ? options.render : function () {};
  this.iconFallback = {shortcut: false, profile: false};
  this.lastView = null;
  this.flow = new MissionFlow({
    store: options.store, config: this.config, missions: options.missions, native: options.native,
    missionTimeoutMs: options.missionTimeoutMs,
    render: function (view) { self.lastView = view; self._render(); },
    onGranted: options.onGranted
  });
  logPlatformCalls(this.flow.missions);
  log('runtime ' + describeRuntime() + ', native ' + this.flow.native);
  this._render();
}

// 简化.11.3: what the platform answered goes to the console (vConsole on the phone), so a tap that does nothing
// can be told apart: no SDK object, canIUse false, a fail() with errorCode, or no answer (timeout).
// Only inside the engine (cc.sys exists): the Node tests keep their stdout for the JSON result.
function log(text) {
  try {
    if (typeof cc === 'undefined' || !cc || !cc.sys) return;
    if (typeof console === 'undefined' || !console || typeof console.info !== 'function') return;
    console.info('[TikTokKit] ' + text);
  } catch (_) {}
}

function describeRuntime() {
  var found = [], names = ['addShortcut', 'getShortcutMissionReward', 'startEntranceMission', 'getEntranceMissionReward'];
  var candidates = [
    ['TTMinis.game', typeof TTMinis !== 'undefined' && TTMinis && TTMinis.game],
    ['tt', typeof tt !== 'undefined' && tt],
    ['wx', typeof wx !== 'undefined' && wx]
  ];
  candidates.forEach(function (pair) {
    var sdk = pair[1];
    if (!sdk) return;
    var can = typeof sdk.canIUse === 'function';
    var parts = names.map(function (name) {
      var answer = '?';
      try { answer = can ? String(sdk.canIUse(name)) : 'no canIUse'; } catch (e) { answer = 'throws'; }
      return name + (typeof sdk[name] === 'function' ? '' : '(missing)') + '=' + answer;
    });
    found.push(pair[0] + ' {' + parts.join(', ') + '}');
  });
  return found.length ? found.join('; ') : 'no TTMinis.game / tt / wx';
}

function logPlatformCalls(missions) {
  if (!missions) return;
  ['navigate', 'query'].forEach(function (action) {
    var call = missions[action];
    if (typeof call !== 'function') return;
    missions[action] = function (kind, opts) {
      log(kind + ' ' + action + ' ...');
      var answer = call.call(missions, kind, opts);
      if (answer && typeof answer.then === 'function') {
        answer.then(function (r) {
          r = r || {};
          log(kind + ' ' + action + ' -> ' + r.status + (r.api ? ' (' + r.api + ')' : '') +
            (r.errorCode !== null && r.errorCode !== undefined ? ' errorCode ' + r.errorCode : '') +
            (r.errMsg ? ' errMsg ' + r.errMsg : ''));
        }, function () {});
      }
      return answer;
    };
  });
}

Controller.TEXT = TEXT;

Controller.prototype.rewardAmount = function () {
  try { return this.config.growthReward(); } catch (_) { return 0; }
};

Controller.prototype.state = function () {
  var flow = this.flow, amount = this.rewardAmount(), self = this, view = this.lastView;
  function entry(kind) {
    var claimed = flow.isClaimed(kind);
    return {
      kind: kind, title: TEXT[kind], claimed: claimed,
      reward: claimed ? TEXT.collected : (amount > 0 ? '+' + amount : ''),
      busy: !!(view && view.kind === kind && view.busy),
      iconFallback: self.iconFallback[kind],
      text: self.iconFallback[kind] ? TEXT[kind] + (claimed ? '\n' + TEXT.collected : (amount > 0 ? '\n+' + amount : '')) : ''
    };
  }
  return {shortcut: entry('shortcut'), profile: entry('profile'), message: view ? view.message : '', native: flow.native};
};

Controller.prototype._render = function () { try { this.renderState(this.state()); } catch (_) {} };

// One tap on an entry. Returns what happened, for tests and logs.
// 简化.11.3 (Saul 2026-11-02): every tap goes to TikTok at once (addShortcut / startEntranceMission inside the
// tap, the user gesture). Until 简化.11.2 the first tap only asked for the reward and a second tap was needed;
// together with canIUse answering undefined on the phone, the entries looked dead (77~86, Mosslight v20).
// Coming back to the game (onShow) checks the reward and pays once. A collected entry still opens TikTok.
Controller.prototype.press = function (kind) {
  if (kind !== 'shortcut' && kind !== 'profile') return 'ignored';
  var flow = this.flow;
  if (!flow.native) { this.toast(TEXT.unsupported); return 'unsupported'; }
  if (flow.kind !== kind) { flow.open(kind, {navigate: true}); return 'start'; }
  if (flow.view().busy) return 'busy';                             // merged
  flow.start();
  return 'start';
};

// The icon of this entry is missing or did not load: show its text instead.
Controller.prototype.iconFailed = function (kind) {
  if (this.iconFallback[kind] === false) { this.iconFallback[kind] = true; this._render(); }
};

Controller.prototype.onShow = function () { this.flow.onShow(); };
Controller.prototype.tick = function () { this.flow.tick(); };
Controller.prototype.dispose = function () { this.flow.dispose(); };

function platformToast(text) {
  var sdk = (typeof TTMinis !== 'undefined' && TTMinis && TTMinis.game) || (typeof tt !== 'undefined' && tt) || null;
  if (sdk && typeof sdk.showToast === 'function') {
    try { sdk.showToast({title: text, icon: 'none', duration: 2000}); return true; } catch (_) {}
  }
  return false;
}

function textureLoaded(sprite) {
  var frame = sprite && sprite.spriteFrame;
  var texture = frame && typeof frame.getTexture === 'function' ? frame.getTexture() : null;
  return !!(texture && texture.loaded);
}

var exported = {Controller: Controller, TEXT: TEXT};
if (typeof cc !== 'undefined' && cc && typeof cc.Class === 'function') {
  exported = cc.Class({
    extends: cc.Component,
    properties: {
      shortcutNode: {default: null, type: cc.Node},
      profileNode: {default: null, type: cc.Node},
      messageLabel: {default: null, type: cc.Label}
    },
    statics: {Controller: Controller, TEXT: TEXT},
    init: function (store, options) {
      options = options || {};
      var self = this;
      if (this.controller) this.controller.dispose();
      this.controller = new Controller({
        store: store, onGranted: options.onGranted, missions: options.missions, native: options.native,
        toast: function (text) { if (!platformToast(text)) self._message(text); },
        render: function (state) { self._paint(state); }
      });
      ['shortcut', 'profile'].forEach(function (kind) {
        var node = self[kind + 'Node'];
        if (!node) { cc.error('HomeGrowthEntries: ' + kind + 'Node is not set'); return; }
        node.active = true;
        node.off(cc.Node.EventType.TOUCH_END, self['_tap_' + kind], self);
        self['_tap_' + kind] = function () { self.controller.press(kind); };
        node.on(cc.Node.EventType.TOUCH_END, self['_tap_' + kind], self);
        var sprite = node.getComponent(cc.Sprite);
        if (!sprite || !sprite.spriteFrame) { self.controller.iconFailed(kind); return; }
        self.scheduleOnce(function () { if (!textureLoaded(sprite)) self.controller.iconFailed(kind); }, ICON_WAIT_MS / 1000);
      });
      if (!this._onShow) {
        this._onShow = function () { if (self.controller) self.controller.onShow(); };
        cc.game.on(cc.game.EVENT_SHOW, this._onShow);
      }
      this.controller._render();
      return this.controller;
    },
    _label: function (node) {
      var child = node.getChildByName('HomeEntryText');
      if (!child) {
        child = new cc.Node('HomeEntryText');
        child.parent = node;
        var label = child.addComponent(cc.Label);
        label.fontSize = 24; label.lineHeight = 28;
        label.horizontalAlign = cc.Label.HorizontalAlign.CENTER;
        label.overflow = cc.Label.Overflow.SHRINK;
        child.setContentSize(node.width || 160, node.height || 80);
        child.color = cc.Color.WHITE;
      }
      return child.getComponent(cc.Label);
    },
    _paint: function (state) {
      var self = this;
      ['shortcut', 'profile'].forEach(function (kind) {
        var node = self[kind + 'Node'];
        if (!node) return;
        var e = state[kind], label = self._label(node);
        // Icon missing or not loaded: the entry title is drawn as text, so the slot is never an empty box.
        label.string = e.iconFallback ? e.title + (e.reward ? '\n' + e.reward : '') : e.reward;
        label.node.active = label.string !== '';
        var button = node.getComponent(cc.Button);
        if (button) button.interactable = !e.busy;
      });
      if (state.message) this._message(state.message);
    },
    _message: function (text) {
      if (this.messageLabel) { this.messageLabel.string = text; this.messageLabel.node.active = true; }
    },
    update: function () { if (this.controller) this.controller.tick(); },
    onDestroy: function () {
      if (this._onShow) cc.game.off(cc.game.EVENT_SHOW, this._onShow);
      if (this.controller) this.controller.dispose();
      this.controller = null;
    }
  });
}
module.exports = exported;

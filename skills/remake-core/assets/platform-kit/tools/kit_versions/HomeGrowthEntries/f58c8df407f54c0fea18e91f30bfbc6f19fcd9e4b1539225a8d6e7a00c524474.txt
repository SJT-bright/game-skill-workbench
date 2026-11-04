'use strict';
// TikTok Platform Kit 2.0 - fixed home entries: "Add to Home Screen" and "Profile Revisit". Copy unchanged.
// 待真机复测 (Node-tested only: tests/home-entries.test.js).
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
  this._render();
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
Controller.prototype.press = function (kind) {
  if (kind !== 'shortcut' && kind !== 'profile') return 'ignored';
  var flow = this.flow;
  if (!flow.native) { this.toast(TEXT.unsupported); return 'unsupported'; }
  if (flow.isClaimed(kind)) { this.toast(MissionFlow.TEXT.claimed); return 'claimed'; }
  if (flow.kind !== kind) { flow.open(kind); return 'opened'; }   // open() checks first
  var view = flow.view();
  if (view.busy) return 'busy';                                    // merged
  if (view.action === 'check') { flow.check(); return 'check'; }
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

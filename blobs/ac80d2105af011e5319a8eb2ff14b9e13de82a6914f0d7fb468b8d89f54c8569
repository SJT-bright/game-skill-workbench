// HomeUI: the whole start menu, built on the unified wood art.
//   top row      : settings (top-left) + gem counter; the top-right corner stays free for TikTok
//   main visual  : logo, current level, PLAY, LEVELS; whole fruit drift up and down behind it
//   both sides   : DAILY + BLADES on the left, GIFT + ENDLESS on the right
//   bottom row   : only SHORTCUT (add to home screen) and PROFILE (revisit from profile)
// actions: {playLevel(n), playEndless()}
var UI = require('UIKit');
var P = require('Progress');
var Popups = require('Popups');
var MapUI = require('MapUI');
var services = require('GameServices');
var MissionFlow = require('MissionFlow');

var REWARD = 10; // gems, paid once per entry after TikTok confirms
// The kit answers this when the TikTok app has no such entry; that button is then hidden.
var UNSUPPORTED_TEXT = 'This feature is available inside a supported TikTok app.';
var FRUIT = ['apple', 'banana', 'basaha', 'peach', 'sandia'];

function HomeUI(menu, vis, actions) {
    this.menu = menu;
    this.vis = vis;
    this.actions = actions || {};
    this.flow = null;
    this.popup = null;
    P.ensure();
    this.build();
}

HomeUI.prototype.build = function () {
    var self = this, menu = this.menu, vis = this.vis;
    var left = -vis.width / 2, right = vis.width / 2, top = vis.height / 2, bottom = -vis.height / 2;
    ['startbg', 'startbtn'].forEach(function (n) {
        var c = menu.getChildByName(n);
        if (c) c.active = false;
    });

    this.drift = new cc.Node('fruit_drift');
    menu.addChild(this.drift);
    this.drift.setSiblingIndex(0);
    this.driftTimer = 0;

    // top row
    var rowY = top - 120;
    UI.tile(menu, 'tile_settings', 84, left + 62, rowY, function () { Popups.settings(menu); });
    this.gems = UI.gemBar(menu, left + 122, rowY);

    // main visual: the logo fills the space between the top row and the level line
    var cy = Math.round(-vis.height * 0.035);
    var logoTop = top - 168, logoBottom = cy + 142;
    var ls = UI.frameSize('logo');
    var logoH = Math.min(367, logoTop - logoBottom);
    var logo = UI.art(menu, 'logo', Math.round(logoH * ls.width / ls.height), 0, 0, Math.round((logoTop + logoBottom) / 2), 'logo');
    logo.runAction(cc.repeatForever(cc.sequence(
        cc.moveBy(1.6, 0, 6).easing(cc.easeSineInOut()), cc.moveBy(1.6, 0, -6).easing(cc.easeSineInOut()))));
    var lv = UI.row(menu, 0, cy + 100, 12);
    UI.art(lv, 't_level', 0, 40);
    this.levelNum = UI.number(lv, P.unlocked(), 48);
    var play = UI.wbutton(menu, 'btn_play', 340, 0, cy, function () { self.actions.playLevel(P.unlocked()); }, 'btn_play');
    play.getComponent(cc.Button).transition = cc.Button.Transition.NONE;
    play.runAction(cc.repeatForever(cc.sequence(cc.scaleTo(0.7, 1.04), cc.scaleTo(0.7, 1))));
    UI.wbutton(menu, 'btn_levels', 230, 0, cy - 112, function () { self.openMap(); }, 'btn_levels');

    // sides of the main visual
    var sx = right - 88, s1 = cy + 70, s2 = cy - 130;
    this.daily = UI.tile(menu, 'tile_daily', 100, -sx, s1, function () { Popups.daily(menu, refresh); }, 'l_daily', 28);
    this.blades = UI.tile(menu, 'tile_blades', 100, -sx, s2, function () { Popups.shop(menu, vis, refresh); }, 'l_blades', 28);
    this.gift = UI.tile(menu, 'tile_gift', 100, sx, s1, function () { Popups.gift(menu, refresh); }, 'l_gift', 28);
    UI.tile(menu, 'tile_endless', 100, sx, s2, function () { self.actions.playEndless(); }, 'l_endless', 28);
    this.dailyBadge = UI.badge(this.daily, 100);
    this.giftBadge = UI.badge(this.gift, 100);
    this.giftTime = UI.lightText(this.gift, '', 22, 0, -66);
    this.giftLabel = this.gift.getChildByName('label');
    if (P.best() > 0) UI.lightText(menu, 'Best ' + P.best(), 22, sx, s2 - 96);

    // bottom row: only the two entries
    this.entries = {};
    this.entries.shortcut = UI.tile(menu, 'tile_shortcut', 104, -120, bottom + 190,
        function () { self.openMission('shortcut'); }, 'l_shortcut', 28);
    this.entries.profile = UI.tile(menu, 'tile_profile', 104, 120, bottom + 190,
        function () { self.openMission('profile'); }, 'l_profile', 28);
    this.unsupported = {};

    function refresh() { self.refresh(); }
    this.flow = new MissionFlow({
        store: services.save,
        reward: function (kind, d) { d.gems = (d.gems || 0) + REWARD; },
        rewardText: {shortcut: '+' + REWARD + ' Gems', profile: '+' + REWARD + ' Gems'},
        render: function (v) { self.renderMission(v); },
        onGranted: function () { services.playSfx('reward'); self.refresh(); }
    });
    this.onShow = function () { if (self.flow) self.flow.onShow(); };
    cc.game.on(cc.game.EVENT_SHOW, this.onShow);
    menu.runAction(cc.repeatForever(cc.sequence(cc.delayTime(1), cc.callFunc(refresh))));
    this.refresh();
};

HomeUI.prototype.refresh = function () {
    if (!cc.isValid(this.menu)) return;
    services.loadAudio();   // no-op when loaded, loading, or inside the 20 s retry wait
    this.gems.set();
    UI.setNumber(this.levelNum, P.unlocked());
    this.dailyBadge.active = P.checkinStatus().can_claim;
    var ready = P.giftReady();
    this.giftBadge.active = ready;
    this.giftLabel.active = ready;
    this.giftTime.active = !ready;
    if (!ready) this.giftTime.getComponent(cc.Label).string = UI.fmtTime(P.giftLeftMs());
};

HomeUI.prototype.openMap = function () {
    var self = this;
    new MapUI(this.menu.parent, this.vis, function (n) { self.actions.playLevel(n); }, function () { self.refresh(); });
};

// Whole fruit tossed slowly from below the screen behind the menu (decoration only: no touch, no reward).
HomeUI.prototype.tickDrift = function (dt) {
    if (!this.menu.activeInHierarchy) return;
    this.driftTimer -= dt;
    if (this.driftTimer > 0) return;
    this.driftTimer = 1.4 + Math.random() * 0.8;
    var name = FRUIT[Math.floor(Math.random() * FRUIT.length)];
    var f = cc.resources.get('textures/fruit/' + name, cc.SpriteFrame);
    if (!f) return;
    var node = new cc.Node('drift');
    node.addComponent(cc.Sprite).spriteFrame = f;
    node.opacity = 215;
    node.scale = 0.75 + Math.random() * 0.25;
    var vis = this.vis;
    var x0 = (Math.random() < 0.5 ? -1 : 1) * (vis.width * (0.18 + Math.random() * 0.3));
    var y0 = -vis.height / 2 - 120;
    var peak = vis.height * (0.0 + Math.random() * 0.22);
    var x1 = x0 * (0.4 + Math.random() * 0.5);
    node.setPosition(x0, y0);
    this.drift.addChild(node);
    var up = 1.5 + Math.random() * 0.5;
    node.runAction(cc.spawn(
        cc.sequence(
            cc.moveTo(up, (x0 + x1) / 2, peak).easing(cc.easeSineOut()),
            cc.moveTo(up, x1, y0).easing(cc.easeSineIn()),
            cc.removeSelf()),
        cc.rotateBy(up * 2, (Math.random() < 0.5 ? -1 : 1) * (120 + Math.random() * 120))));
};

HomeUI.prototype.openMission = function (kind) {
    var self = this;
    if (this.popup && cc.isValid(this.popup.root)) this.popup.root.destroy();
    var root = UI.modal(this.menu, 'mission_popup');
    var p = UI.panel(root, 560, 560, 0, 0, kind === 'shortcut' ? 'l_shortcut' : 'l_profile', function () { self.closeMission(); });
    UI.art(p, kind === 'shortcut' ? 'w_add_to_home_screen' : 'w_revisit_from_profile', 0, 30, 0, 180);
    UI.sprite(p, kind === 'shortcut' ? 'tile_shortcut' : 'tile_profile', 120, 120, 0, 90, 'icon');
    var message = UI.text(p, '', 26, UI.BROWN, 0, -40, 460);
    var go = UI.wbutton(p, 'btn_go', 240, 0, -175, function () { self.missionAction(); }, 'btn_go');
    var check = UI.wbutton(p, 'btn_check_reward', 290, 0, -175, function () { self.missionAction(); }, 'btn_check_reward');
    check.active = false;
    this.popup = {root: root, message: message, go: go, check: check, kind: kind};
    this.flow.open(kind);
};

HomeUI.prototype.missionAction = function () {
    var v = this.flow.view();
    if (v.action === 'check') this.flow.check();
    else if (v.action === 'start') this.flow.start();
};

HomeUI.prototype.closeMission = function () {
    var kind = this.popup && this.popup.kind;
    this.flow.close();
    if (this.popup && cc.isValid(this.popup.root)) this.popup.root.destroy();
    this.popup = null;
    if (kind && this.unsupported[kind] && this.entries[kind] && cc.isValid(this.entries[kind])) {
        this.entries[kind].active = false;
    }
};

HomeUI.prototype.renderMission = function (v) {
    var p = this.popup;
    if (!p || !cc.isValid(p.root)) return;
    if (!v.open) { p.root.destroy(); this.popup = null; return; }
    if (v.native && v.message === UNSUPPORTED_TEXT) this.unsupported[v.kind] = true;
    var msg = v.message || '';
    if (!v.claimed && v.phase === 'idle' && v.action === 'start' && v.rewardText) msg += '\nReward: ' + v.rewardText;
    p.message.getComponent(cc.Label).string = msg;
    var showCheck = v.action === 'check';
    p.go.active = !v.claimed && !showCheck;
    p.check.active = !v.claimed && showCheck;
    UI.setEnabled(p.go, !v.busy);
    UI.setEnabled(p.check, !v.busy);
};

HomeUI.prototype.tick = function (dt) {
    if (this.flow) this.flow.tick();
    this.tickDrift(dt || 0);
};

HomeUI.prototype.dispose = function () {
    cc.game.off(cc.game.EVENT_SHOW, this.onShow);
    if (this.flow) this.flow.dispose();
    this.flow = null;
};

module.exports = HomeUI;

// GameAudioButton.js —— 按钮点击音（Cocos Creator 2.4，JavaScript）
// 用法一：在编辑器里给按钮挂这个组件，可改 soundId。
// 用法二（推荐）：每个界面打开时调用一次 require('GameAudioButton').attachAll(this.node)，
//         自动给界面里所有 cc.Button 加点击音；名字含 back / close 的按钮用返回音。

var GameAudioManager = require('GameAudioManager');

var GameAudioButton = cc.Class({
    extends: cc.Component,

    properties: {
        soundId: 'sfx_ui_click'
    },

    statics: {
        attachAll: function (root) {
            root.getComponentsInChildren(cc.Button).forEach(function (btn) {
                if (btn.getComponent(GameAudioButton)) return;
                var bs = btn.addComponent(GameAudioButton);
                if (/back|close|cancel|返回|关闭/i.test(btn.node.name)) bs.soundId = 'sfx_ui_back';
            });
        }
    },

    onEnable: function () { this.node.on('click', this._onClick, this); },
    onDisable: function () { this.node.off('click', this._onClick, this); },

    _onClick: function () {
        var btn = this.getComponent(cc.Button);
        if (btn && !btn.interactable) return;
        var am = GameAudioManager.instance;
        if (!am) return;
        am.unlock();
        am.playSFX(this.soundId);
    }
});

module.exports = GameAudioButton;

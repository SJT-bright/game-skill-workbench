// GameAudioButton.ts —— 按钮点击音（Cocos Creator 3.x）
// 用法一：在编辑器里给按钮挂这个组件，可改 soundId。
// 用法二（推荐）：每个界面打开时调用一次 GameAudioButton.attachAll(this.node)，
//         自动给界面里所有 Button 加点击音；名字含 back / close 的按钮用返回音。

import { _decorator, Component, Button, Node } from 'cc';
import { GameAudioManager } from './GameAudioManager';
const { ccclass, property } = _decorator;

@ccclass('GameAudioButton')
export class GameAudioButton extends Component {
    @property
    soundId = 'sfx_ui_click';

    onEnable() { this.node.on(Button.EventType.CLICK, this.onClick, this); }
    onDisable() { this.node.off(Button.EventType.CLICK, this.onClick, this); }

    private onClick() {
        const btn = this.getComponent(Button);
        if (btn && !btn.interactable) return;
        const am = GameAudioManager.instance;
        if (!am) return;
        am.unlock();
        am.playSFX(this.soundId);
    }

    static attachAll(root: Node) {
        root.getComponentsInChildren(Button).forEach(btn => {
            if (btn.getComponent(GameAudioButton)) return;
            const bs = btn.addComponent(GameAudioButton);
            if (/back|close|cancel|返回|关闭/i.test(btn.node.name)) bs.soundId = 'sfx_ui_back';
        });
    }
}

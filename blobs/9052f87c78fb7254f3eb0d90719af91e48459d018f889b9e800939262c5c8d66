#!/usr/bin/env python3
"""生成时预防 R4N4 (问题普查 补查2 第 3 / 10 组): ui_kit_scan K_ui_label_order and K_tween_stop_all.

  1 label order  SLS35 settings / shop text the old way (addComponent(cc.Label), .string and the font, then CLAMP),
                 3.x addComponent(Label) with .string and no overflow, addComponent(Label).string = ... -> reported;
                 the fixed copy (overflow + enableWrapText before .string, UI.text) -> not reported
  2 tween stop   Tween.stopAll(), cc.Tween.stopAll(), cc.director.getScene().stopAllActions(),
                 cc.find('Canvas').stopAllActions(), getActionManager().removeAllActions() -> reported;
                 cc.Tween.stopAllByTarget(node), this.node.stopAllActions(), session.newRun -> not
  3 levels       new remake game: warnings (K_W_...), English: warnings, legacy: info; never a block
  4 exempt       `// tiktok-kit:ui-ok why` on the line is skipped
Run: python3 test_ui_kit_scan_r4n4.py
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tiktok_finalize_steps import ui_kit_scan as U  # noqa: E402

# 照旧写法（SLS35 设置页规则正文、商店说明的节选，和 Retry / Home 的全局停止）
OLD = """cc.Class({
    extends: cc.Component,
    buildRules (panel) {
        var node = new cc.Node('Rules');
        panel.addChild(node);
        var label = node.addComponent(cc.Label);
        label.string = this.rulesText;
        label.fontSize = 28;
        label.lineHeight = 36;
        label.overflow = cc.Label.Overflow.CLAMP;
        label.enableWrapText = true;
        node.setContentSize(480, 220);
    },
    buildShop (panel) {
        panel.getChildByName('Desc').addComponent(cc.Label).string = 'Buy skins with coins.';
    },
    onRetry () {
        cc.Tween.stopAll();
        this.startLevel();
    },
    onHome () {
        Tween.stopAll();
        cc.director.getScene().stopAllActions();
        cc.find('Canvas').stopAllActions();
        cc.director.getActionManager().removeAllActions();
        cc.director.loadScene('Home');
    },
});
"""
OLD_3X = """import { _decorator, Component, Label, Node, Tween } from 'cc';
export class Settings extends Component {
    build(panel: Node) {
        const n = new Node('Tip');
        panel.addChild(n);
        const tip: Label = n.addComponent(Label);
        tip.string = 'Swipe to move.';
        tip.fontSize = 26;
    }
}
"""
FIXED = """var UI = require('GameUIKit');
cc.Class({
    extends: cc.Component,
    buildRules (panel) {
        var node = new cc.Node('Rules');
        panel.addChild(node);
        node.setContentSize(480, 220);
        var label = node.addComponent(cc.Label);
        label.overflow = cc.Label.Overflow.CLAMP;
        label.enableWrapText = true;
        label.fontSize = 28;
        label.string = this.rulesText;
        UI.text(panel, {w: 480, h: 120, text: 'Buy skins with coins.', overflow: 'shrink'});
    },
    onRetry () {
        cc.Tween.stopAllByTarget(this.board);
        this.node.stopAllActions();
        this.session.newRun(this.initRun);
    },
    onHome () {
        Tween.stopAll(); // tiktok-kit:ui-ok only the loading scene, no popup open
    },
});
"""


class LabelOrder(unittest.TestCase):
    def test_old_reported(self):
        labels, _ = U.scan_order(OLD, 'Settings.js')
        # R4O5: line 15 (an unsized `getChildByName('Desc').addComponent(cc.Label).string =`) is no longer reported
        self.assertEqual(sorted(x['line'] for x in labels), [6], labels)
        whats = ' '.join(x['what'] for x in labels)
        self.assertIn('label.string before label.overflow', whats)

    def test_old_3x_short_tip_not_reported(self):
        # R4O5: a one-line tip with no size, no wrap and no overflow is fine under NONE; the sized one is reported
        labels, _ = U.scan_order(OLD_3X, 'Settings.ts')
        self.assertEqual(labels, [])
        sized = OLD_3X.replace("panel.addChild(n);", "panel.addChild(n);\n        n.getComponent(UITransform).setContentSize(400, 80);")
        labels, _ = U.scan_order(sized, 'Settings.ts')
        self.assertEqual([x['line'] for x in labels], [7], labels)
        self.assertIn('no overflow', labels[0]['what'])

    def test_fixed_clean(self):
        labels, tweens = U.scan_order(FIXED, 'Settings.js')
        self.assertEqual(labels, [])
        self.assertEqual(tweens, [])


class LabelOrderNoiseR4O5(unittest.TestCase):
    """R4O5 (R4N4 calibration: 32 of 37 new games reported): only `.string` before `.overflow` on the same Label, and a
    Label whose node is given a size or which wraps but has no overflow. Short one-line value Labels are not reported."""

    def lines(self, text, rel='Hud.js'):
        return [x['line'] for x in U.scan_order(text, rel)[0]]

    def test_short_value_labels_not_reported(self):
        # 照 EnglishUI.ts / Main.ts 的写法：分数、关卡号、金币数，没设大小、没换行
        self.assertEqual(self.lines("var score = node.addComponent(cc.Label);\nscore.string = '0';\nscore.fontSize = 40;\n"
                                    "const lv = hud.addComponent(Label);\nlv.string = 'LV ' + n;\n"
                                    "row.addComponent(cc.Label).string = '' + coins;\n"), [])

    def test_string_before_overflow_still_reported(self):
        self.assertEqual(self.lines("var t = node.addComponent(cc.Label);\nt.string = s;\n"
                                    "t.overflow = cc.Label.Overflow.SHRINK;\n"), [1])

    def test_sized_or_wrapped_without_overflow_reported(self):
        self.assertEqual(self.lines("node.setContentSize(480, 220);\nvar a = node.addComponent(cc.Label);\na.string = s;\n"), [2])
        self.assertEqual(self.lines("var b = node.addComponent(cc.Label);\nb.enableWrapText = true;\nb.string = s;\n"), [1])
        self.assertEqual(self.lines("var c = new cc.Label();\nc.string = s;\nc.node.width = 300;\n"), [1])
        self.assertEqual(self.lines("const d = n.addComponent(Label);\nd.string = s;\nn.getComponent(UITransform)!.width = 300;\n",
                                    'Hud.ts'), [1])

    def test_sized_chain_reported(self):
        self.assertEqual(self.lines("box.setContentSize(400, 120);\nbox.addComponent(cc.Label).string = text;\n"), [2])

    def test_overflow_first_not_reported(self):
        self.assertEqual(self.lines("var e = node.addComponent(cc.Label);\ne.overflow = 2;\ne.enableWrapText = true;\n"
                                    "node.setContentSize(300, 90);\ne.string = s;\n"), [])


class TweenStopAll(unittest.TestCase):
    def test_old_reported(self):
        _, tweens = U.scan_order(OLD, 'Settings.js')
        self.assertEqual([x['line'] for x in tweens], [18, 22, 23, 24, 25], tweens)

    def test_by_target_not(self):
        _, tweens = U.scan_order('cc.Tween.stopAllByTarget(n);\nthis.node.stopAllActions();\nhero.stopAllActions();\n', 'x.js')
        self.assertEqual(tweens, [])


class Levels(unittest.TestCase):
    def _found(self):
        labels, tweens = U.scan_order(OLD, 'Settings.js')
        return {'files': 1, 'popups': [], 'masks': [], 'dev': [], 'labels': labels, 'tweens': tweens}

    def test_levels(self):
        f = self._found()
        new = U.findings(f, 'new', 'remake')
        self.assertEqual(sorted((x['id'], lv) for lv, x in new),
                         [('K_W_tween_stop_all', 'warn'), ('K_W_ui_label_order', 'warn')])
        self.assertEqual({lv for lv, _ in U.findings(f, 'new', 'remake', kit_era=True)}, {'warn'})
        self.assertEqual({lv for lv, _ in U.findings(f, 'new', 'localize')}, {'warn'})
        self.assertEqual({lv for lv, _ in U.findings(f, 'legacy', 'remake')}, {'info'})

    def test_project_scan(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / 'assets/scripts').mkdir(parents=True)
            (tmp / 'assets/scripts/Settings.js').write_text(OLD, encoding='utf-8')
            (tmp / 'assets/scripts/Fixed.js').write_text(FIXED, encoding='utf-8')
            (tmp / 'assets/tiktok-platform').mkdir(parents=True)
            (tmp / 'assets/tiktok-platform/GameUIKit.js').write_text(OLD, encoding='utf-8')   # kit dir skipped
            found = U.scan(tmp)
            self.assertEqual(len(found['labels']), 1)        # R4O5: the unsized one-line chain is no longer reported
            self.assertEqual(len(found['tweens']), 5)
            self.assertTrue(all(x['file'] == 'assets/scripts/Settings.js' for x in found['labels'] + found['tweens']))
        finally:
            shutil.rmtree(tmp)


if __name__ == '__main__':
    unittest.main(verbosity=2)

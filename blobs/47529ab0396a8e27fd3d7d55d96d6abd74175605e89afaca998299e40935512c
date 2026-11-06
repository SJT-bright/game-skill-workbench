#!/usr/bin/env python3
"""R4Q4 (问题普查补查3 第 4 组): the English inventory lists the original game's own reward / spend / item writes
(reward_todo), and the read-only source step reward_order_scan reports rewards saved in an animation callback, memory
changed before a save with no rollback, x2 rounded in two orders and a run total paid twice. Fixtures follow
奔跑吧巨人 (rollout-2026-11-05T03-52-23 :511, 03-51-19 :775) and 合成进化恐龙 (rollout-2026-11-05T02-22-20 :748 / :978);
each old writing is caught, the fixed writing is not.

  python3 -B remake-core/scripts/test_r4q4_reward_order.py      (well under a second)
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from tiktok_finalize_steps import reward_order_scan as S  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402

# 奔跑吧巨人 chest x2: hide the button, play the animation, save at the end of it
CHEST_OLD = """\
onChestDouble() {
    RewardedService.show('chest_x2', (ok) => {
        if (!ok) return;
        this.btnDouble.active = false;
        tween(this.chest).to(0.4, { scale: v3(1.2, 1.2, 1) }).call(() => {
            StorageManager.instance.setGlobalData('diamond', this.diamond + this.chestGain * 2);
            this.close();
        }).start();
    });
}
"""
CHEST_FIXED = """\
onChestDouble() {
    RewardedService.show('chest_x2', (ok) => {
        if (!ok) return;
        const r = store.grant({ id: 'chest:' + this.chestId + ':x2', add: { diamond: this.chestBase * 2 } });
        if (!r.ok) { this.toast('Could not save, tap again'); return; }
        this.refreshWallet();
        tween(this.chest).to(0.4, { scale: v3(1.2, 1.2, 1) }).call(() => { this.close(); }).start();
    });
}
"""
# 奔跑吧巨人 chest keys: memory first, save without a rollback
KEYS_OLD = """\
onKeyAd() {
    RewardedService.show('keys', (ok) => {
        if (!ok) return;
        this.data.keys += 3;
        StorageManager.instance.save();
        this.refreshKeys();
    });
}
"""
KEYS_FAIL_NO_RESTORE = """\
onKeyAd() {
    this.data.keys += 3;
    if (!StorageManager.instance.save()) {
        this.toast('save failed');
    }
}
"""
KEYS_FIXED = """\
onKeyAd() {
    RewardedService.show('keys', (ok) => {
        if (!ok) return;
        const r = store.grant({ id: 'keys:' + this.chestId, add: { keys: 3 } });
        if (r.ok) this.refreshKeys();
    });
}
"""
KEYS_ROLLBACK = """\
onKeyAd() {
    const before = this.data.keys;
    this.data.keys += 3;
    if (!StorageManager.instance.save()) {
        this.data.keys = before;
    }
}
"""
# 奔跑吧巨人 result x2: label ceil(base*2), grant 2*ceil(base)
X2_LABEL_OLD = "this.lbDouble.string = '+' + Math.ceil(this.baseGold * 2);\n"
X2_PAY_OLD = "const pay = 2 * Math.ceil(this.baseGold);\nstore.grant({ id: 'run:' + id + ':x2', add: { gold: pay } });\n"
X2_LABEL_FIXED = "const base = Math.ceil(this.baseGold);\nthis.lbDouble.string = '+' + base * 2;\n"
X2_PAY_FIXED = "const pay = 2 * Math.ceil(this.baseGold);\nstore.grant({ id: 'run:' + id + ':x2', add: { gold: pay } });\n"
# 合成进化恐龙: battle pays each kill to the wallet and to the run total, the result Claim pays the total again
DINO_BATTLE = """\
onKill(enemy) {
    GD.coin += enemy.reward;
    this.runCoins += enemy.reward;
}
"""
DINO_RESULT_OLD = """\
onClaim() {
    GD.coin += this.runCoins;
    this.close();
}
"""
DINO_RESULT_FIXED = """\
onClaim() {
    this.claimed = true;
    this.close();
}
onDouble() {
    RewardedService.show('result_x2', (ok) => {
        if (!ok) return;
        GD.coin += this.runCoins;
    });
}
"""


def scan(*files):
    return S.combine([S.scan_text(t, 'assets/s%d.ts' % i) for i, t in enumerate(files)])


def ids(found, policy='new'):
    return {item['id'] for _, item in S.findings(found, policy)}


class RewardOrderScanTests(unittest.TestCase):
    def test_save_in_animation_callback(self):
        self.assertIn('K_W_reward_in_anim_callback', ids(scan(CHEST_OLD)))
        self.assertNotIn('K_W_reward_in_anim_callback', ids(scan(CHEST_FIXED)))

    def test_callfunc_and_on_finished(self):
        old = "this.node.runAction(cc.sequence(cc.fadeOut(0.3), cc.callFunc(function () { GD.coin += 5; GD.save(); })));\n"
        anim = "anim.on('finished', () => { this.addCoins(50); }, this);\n"
        self.assertEqual(len(scan(old).get('anim')), 1)
        self.assertEqual(len(scan(anim).get('anim')), 1)
        self.assertEqual(scan("anim.on('finished', () => { this.refresh(); }, this);\n")['anim'], [])

    def test_memory_before_save_no_rollback(self):
        self.assertIn('K_W_reward_no_rollback', ids(scan(KEYS_OLD)))
        self.assertIn('K_W_reward_no_rollback', ids(scan(KEYS_FAIL_NO_RESTORE)))
        self.assertNotIn('K_W_reward_no_rollback', ids(scan(KEYS_FIXED)))
        self.assertNotIn('K_W_reward_no_rollback', ids(scan(KEYS_ROLLBACK)))

    def test_x2_rounding_two_orders(self):
        self.assertIn('K_W_x2_rounding_mismatch', ids(scan(X2_LABEL_OLD, X2_PAY_OLD)))
        self.assertNotIn('K_W_x2_rounding_mismatch', ids(scan(X2_LABEL_FIXED, X2_PAY_FIXED)))

    def test_run_total_paid_twice(self):
        self.assertIn('K_W_reward_prepaid_twice', ids(scan(DINO_BATTLE, DINO_RESULT_OLD)))
        self.assertNotIn('K_W_reward_prepaid_twice', ids(scan(DINO_BATTLE, DINO_RESULT_FIXED)))

    def test_exempt_comment_and_comments(self):
        exempt = "// tiktok-kit:reward-ok saved again on the next screen\nthis.data.keys += 3;\nthis.save();\n"
        self.assertEqual(scan(exempt)['rollback'], [])
        self.assertEqual(scan("// this.data.keys += 3; this.save();\n")['rollback'], [])

    def test_policy_levels(self):
        found = scan(CHEST_OLD, KEYS_OLD)
        self.assertEqual({lv for lv, _ in S.findings(found, 'new')}, {'warn'})
        self.assertEqual({lv for lv, _ in S.findings(found, 'legacy')}, {'info'})

    def test_registered_and_apply(self):
        self.assertIn('reward_order_scan', T.SOURCE_STEPS)
        import tiktok_finalize as F
        steps = list(F.SYNC_SOURCE_STEPS)
        self.assertLess(steps.index('reward_order_scan'), steps.index('ui_kit_scan'))
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / 'assets' / 'scripts').mkdir(parents=True)
            (tmp / 'assets' / 'scripts' / 'Chest.ts').write_text(CHEST_OLD + KEYS_OLD, encoding='utf-8')
            (tmp / 'assets' / 'tiktok-platform').mkdir()
            (tmp / 'assets' / 'tiktok-platform' / 'Kit.js').write_text(KEYS_OLD, encoding='utf-8')
            ctx = T.Ctx('source', tmp, policy='new')
            out = S.apply(ctx)
            got = {w['id'] for w in out['warnings']}
            self.assertEqual(got, {'K_W_reward_in_anim_callback', 'K_W_reward_no_rollback'})
            self.assertTrue(all(e['file'] == 'assets/scripts/Chest.ts' for w in out['warnings'] for e in w['evidence']))
            self.assertEqual(out['blocks'], [])
            self.assertEqual(S.apply(T.Ctx('source', tmp, policy='legacy'))['warnings'], [])
        finally:
            shutil.rmtree(tmp)


class RewardInventoryTests(unittest.TestCase):
    def test_reward_todo(self):
        import reward_inventory as R
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / 'assets' / 'scripts').mkdir(parents=True)
            (tmp / 'assets' / 'scripts' / 'Keys.ts').write_text(KEYS_OLD, encoding='utf-8')
            (tmp / 'assets' / 'scripts' / 'Summon.ts').write_text(
                "summon() {\n  if (GD.coin < 100) return;\n  GD.coin -= 100;\n  GD.diamondNum = GD.diamondNum - 1;\n"
                "  this.monkey += 1;\n  GD.save();\n}\n", encoding='utf-8')
            (tmp / 'assets' / 'scripts' / 'Ui.ts').write_text("this.count += 1;\n// GD.coin += 5;\n", encoding='utf-8')
            plan = R.plan(tmp)
            rows = plan['reward_todo']
            kinds = [(r['file'].split('/')[-1], r['kind'], r.get('field')) for r in rows]
            self.assertIn(('Keys.ts', 'reward_add', 'this.data.keys'), kinds)
            self.assertIn(('Summon.ts', 'reward_spend', 'GD.coin'), kinds)
            self.assertIn(('Summon.ts', 'reward_spend', 'GD.diamondNum'), kinds)
            self.assertIn(('Summon.ts', 'reward_save', None), kinds)
            self.assertFalse(any(r.get('field') == 'this.monkey' for r in rows))
            self.assertFalse(any(r['file'].endswith('Ui.ts') for r in rows))
            self.assertTrue(next(r for r in rows if r['file'].endswith('Keys.ts') and r['kind'] == 'reward_add')
                            .get('in_ad_callback'))
            self.assertTrue(all('fix' in r for r in rows))
            self.assertEqual(plan['reward_summary']['spend'], 2)
        finally:
            shutil.rmtree(tmp)

    def test_wallet_calls_listed(self):
        import reward_inventory as R
        got = R.changes("playerData.instance.updatePlayerInfo('key', -1); GameManager.addDiamond(-cost); addDiamond(5);")
        self.assertEqual(got, [('reward_spend', 'call:key'), ('reward_spend', 'call:addDiamond'),
                               ('reward_add', 'call:addDiamond')])
        self.assertEqual(R.changes('public static addDiamond (value: number = 1) {'), [])

    def test_finalize_inventory_has_reward_todo(self):
        import tiktok_finalize as F
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / 'assets').mkdir()
            (tmp / 'assets' / 'G.js').write_text("GD.gold += 5;\nGD.save();\n", encoding='utf-8')
            inv = F.inventory(tmp)
            self.assertIn('reward_todo', inv)
            self.assertIn('audio_todo', inv)
            self.assertEqual(inv['reward_summary']['add'], 1)
        finally:
            shutil.rmtree(tmp)


if __name__ == '__main__':
    unittest.main(verbosity=1)

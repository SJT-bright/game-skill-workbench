#!/usr/bin/env python3
"""R4N6 (问题普查补查2 第 6 / 9 / 11 组): save reads that lose 0 / false, ad receipts written apart from the grant,
level caps that differ from the real level count, 3.x game scripts that import a kit plugin, plugin .meta flags, and
make_save_schema.py --inventory. Each old writing (from the census games) is caught; the fixed writing is not.

  python3 -B remake-core/scripts/test_r4n6_save_read_scan.py
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from tiktok_finalize_steps import save_read_scan as S  # noqa: E402
from tiktok_finalize_steps import plugin3x_scan as P  # noqa: E402

# 合成进化恐龙 GD.init (rollout-2026-11-05T02-22-20 :544): old coins moved with `|| 100`, a saved 0 / false became 100
GD_INIT_OLD = """\
var GD = {};
GD.init = function () {
    var raw = cc.sys.localStorage.getItem('dino_save');
    var d = raw ? JSON.parse(raw) : {};
    GD.coin = d.coin || 100;
    if (!d.music) d.music = true;
    GD.level = d.level || 1;
};
"""
GD_INIT_FIXED = """\
var GD = {};
GD.init = function () {
    var raw = cc.sys.localStorage.getItem('dino_save');
    var d = raw ? JSON.parse(raw) : {};
    GD.coin = d.coin === undefined ? 100 : d.coin;
    if (d.music === undefined) d.music = true;
    GD.level = d.level || 0;
    GD.name = d.name || '';
};
"""
# 奔跑吧巨人 result x2 (rollout-2026-11-05T03-52-23 :511): paid, then the receipt in a second save
GIANT_X2_OLD = """\
onDoubleAd() {
    RewardedService.show('result_x2', (ok) => {
        if (!ok) return;
        const amount = this.runCoins * 2;
        const r = store.grant({ add: { coins: amount } });
        if (!r.ok) { this.toast('Could not save'); return; }
        store.update((d) => { d.lastReceipt = { run: this.runId, mult: 2, amount: amount }; });
    });
}
"""
GIANT_X2_FIXED = """\
onDoubleAd() {
    RewardedService.show('result_x2', (ok) => {
        if (!ok) return;
        const amount = this.runCoins * 2;
        store.grant({ id: 'run:' + this.runId + ':x2', add: { coins: amount },
                      apply: (d) => { d.lastReceipt = { run: this.runId, mult: 2, amount: amount }; } },
                    () => this.refreshWallet());
    });
}
"""
# 弹球传奇 MapCheckPointManager.js (rollout-2026-11-05T03-50-56 :550)
MAP_MAX = """\
cc.Class({
    extends: cc.Component,
    properties: {
        _MapMax:1000, //最大关卡数量
    },
});
"""
# 合成进化恐龙 EnglishRuntime (55 unresolved-module) and 奔跑吧巨人 side-effect imports
ESM_OLD = """\
import { _decorator, Component } from 'cc';
import RunSession from '../tiktok-platform/RunSession';
import '../tiktok-platform/RewardedService.plugin.js';
import GameUIKit from '../tiktok-platform/GameUIKit';
const { ccclass } = _decorator;
"""
ESM_FIXED = """\
import { _decorator, Component } from 'cc';
import GameUIKit from '../tiktok-platform/GameUIKit';
const kit = (globalThis as any).TikTokKit;
const run = (globalThis as any).TikTokRunSession;
"""


def project(files, engine3=False):
    root = Path(tempfile.mkdtemp(prefix='r4n6_'))
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text if isinstance(text, str) else json.dumps(text), encoding='utf-8')
    if engine3:
        (root / 'package.json').write_text(json.dumps({'creator': {'version': '3.8.8'}}), encoding='utf-8')
    return root


class SaveReads(unittest.TestCase):
    def test_gd_init_old_caught(self):
        hits = S.scan_text(GD_INIT_OLD, 'GD.js')['falsy']
        self.assertEqual([h['line'] for h in hits], [5, 6, 7], hits)
        self.assertIn('=== undefined', hits[0]['fix'])

    def test_gd_init_fixed_clean(self):
        self.assertEqual(S.scan_text(GD_INIT_FIXED, 'GD.js')['falsy'], [])

    def test_unrelated_or_default_not_caught(self):
        text = 'var w = opts.width || 720;\nvar name = label || "Player";\n'
        self.assertEqual(S.scan_text(text, 'a.js')['falsy'], [])

    def test_comment_and_exempt_skipped(self):
        text = ("var d = JSON.parse(cc.sys.localStorage.getItem('k'));\n// d.coin || 100\n"
                "// tiktok-kit:save-ok old saves never had 0 here\nvar c = d.coin || 100;\n")
        self.assertEqual(S.scan_text(text, 'a.js')['falsy'], [])


class Receipts(unittest.TestCase):
    def test_giant_old_caught(self):
        hits = S.scan_text(GIANT_X2_OLD, 'Result.ts')['receipt']
        self.assertTrue(hits, 'grant without id / receipt written apart must be reported')
        self.assertEqual(hits[0]['line'], 5)

    def test_giant_fixed_clean(self):
        self.assertEqual(S.scan_text(GIANT_X2_FIXED, 'Result.ts')['receipt'], [])

    def test_plain_level_reward_with_id_clean(self):
        text = "store.grant({id: 'level:' + n + ':first', add: {coins: 40}}, done);\n"
        self.assertEqual(S.scan_text(text, 'a.js')['receipt'], [])


class LevelCap(unittest.TestCase):
    def test_mapmax_vs_record(self):
        root = project({'assets/scripts/MapCheckPointManager.js': MAP_MAX,
                        'docs/levels/level_resources.json': {'count': 500, 'files': 'assets/resources/maps/*.json'}})
        f = S.findings(S.scan(root))
        ids = [x[1]['id'] for x in f]
        self.assertIn('K_W_level_cap_mismatch', ids)
        self.assertIn('_MapMax = 1000', [x[1] for x in f if x[1]['id'] == 'K_W_level_cap_mismatch'][0]['message'])

    def test_mapmax_matching_or_no_record(self):
        same = project({'assets/scripts/M.js': MAP_MAX.replace('1000', '500'),
                        'docs/levels/level_resources.json': {'count': 500}})
        none = project({'assets/scripts/M.js': MAP_MAX})
        self.assertEqual(S.findings(S.scan(same)), [])
        self.assertEqual(S.findings(S.scan(none)), [])

    def test_legacy_is_info(self):
        root = project({'assets/scripts/M.js': GD_INIT_OLD})
        self.assertEqual({lvl for lvl, _ in S.findings(S.scan(root), 'legacy')}, {'info'})

    def test_record_level_files(self):
        root = project({'assets/resources/maps/%d.json' % i: '{}' for i in range(1, 501)})
        out = subprocess.run([sys.executable, '-B', str(HERE / 'make_level_plan.py'), '--project', str(root),
                              '--record-level-files', 'assets/resources/maps/*.json'],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        rec = json.loads((root / 'docs/levels/level_resources.json').read_text(encoding='utf-8'))
        self.assertEqual((rec['count'], rec['max_index'], rec['gaps']), (500, 500, []))


class Plugin3x(unittest.TestCase):
    def test_esm_import_old_caught(self):
        hits = P.import_hits(ESM_OLD, 'assets/scripts/EnglishRuntime.ts', P.DEFAULT_NAMES)
        self.assertEqual([h['line'] for h in hits], [2, 3], hits)

    def test_game_own_module_of_same_name_clean(self):   # Marlows' own assets/scripts/PlatformConfig.ts
        root = project({'assets/scripts/Marlow.ts': "import {platformConfig} from './PlatformConfig';\n",
                        'assets/scripts/PlatformConfig.ts': 'export const platformConfig = {};\n'}, engine3=True)
        self.assertEqual(P.scan(root)['imports'], [])

    def test_esm_fixed_clean(self):
        self.assertEqual(P.import_hits(ESM_FIXED, 'assets/scripts/EnglishRuntime.ts', P.DEFAULT_NAMES), [])

    def test_meta_flags(self):
        good = {'userData': dict(P.FLAGS)}
        bad = {'userData': {'isPlugin': True, 'loadPluginInWeb': True}}
        self.assertEqual(P.meta_problem(json.dumps(good).encode()), None)
        self.assertIn('loadPluginInMiniGame', P.meta_problem(json.dumps(bad).encode()))
        self.assertIn('missing', P.meta_problem(None))

    def test_flags_are_one_source(self):
        from tiktok_finalize_steps import kit_sources
        sys.path.insert(0, str(HERE.parent / 'assets' / 'platform-kit' / 'tools'))
        import make_plugin_scripts
        self.assertEqual(P.FLAGS, make_plugin_scripts.PLUGIN_META_FLAGS)
        for k, v in P.FLAGS.items():
            self.assertEqual(kit_sources.PLUGIN_FLAGS[k], v)
        parts = json.loads((HERE.parent / 'assets/platform-kit/parts-3x/KIT_PARTS_3X.json').read_text(encoding='utf-8'))
        self.assertEqual(parts.get('plugin_meta_flags'), P.FLAGS)

    def test_project_scan_new_blocks_english_warns(self):
        files = {'assets/scripts/EnglishRuntime.ts': ESM_OLD,
                 'assets/tiktok-platform/RewardedService.plugin.js': '// kit\n',
                 'assets/tiktok-platform/RewardedService.plugin.js.meta': {'userData': {'isPlugin': True}}}
        root = project(files, engine3=True)
        found = P.scan(root)
        levels = {f['id']: f['level'] for f in P.findings(found, 'new', 'remake')}
        self.assertEqual(levels.get('K_plugin3x_import'), 'block')
        self.assertEqual(levels.get('K_plugin3x_meta'), 'block')
        levels = {f['id']: f['level'] for f in P.findings(found, 'new', 'localize')}
        self.assertEqual(levels.get('K_plugin3x_import'), 'warn')
        self.assertEqual({f['level'] for f in P.findings(found, 'legacy', 'remake')}, {'info'})


class SaveInventory(unittest.TestCase):
    def test_inventory_lists_every_key_and_builds(self):
        root = project({'assets/scripts/GD.js': GD_INIT_OLD + "cc.sys.localStorage.setItem('dino_best', String(b));\n"
                                                              "tt.setStorageSync('pinball_skins', JSON.stringify(s));\n"})
        out = subprocess.run([sys.executable, '-B', str(HERE / 'make_save_schema.py'), '--project', str(root),
                              '--inventory'], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        spec = json.loads((root / 'docs/save/save_keys.json').read_text(encoding='utf-8'))
        self.assertEqual(sorted(spec['inventory']), ['dino_best', 'dino_save', 'pinball_skins'])
        self.assertIn('read', spec['inventory']['dino_save']['how'])
        out = subprocess.run([sys.executable, '-B', str(HERE / 'make_save_schema.py'), '--project', str(root)],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        # a second inventory keeps what the AI wrote by hand
        spec['keys']['dino_save'] = {'type': 'string', 'default': '{}'}
        (root / 'docs/save/save_keys.json').write_text(json.dumps(spec), encoding='utf-8')
        subprocess.run([sys.executable, '-B', str(HERE / 'make_save_schema.py'), '--project', str(root), '--inventory'],
                       capture_output=True, text=True, check=True)
        spec2 = json.loads((root / 'docs/save/save_keys.json').read_text(encoding='utf-8'))
        self.assertEqual(spec2['keys']['dino_save'], {'type': 'string', 'default': '{}'})


if __name__ == '__main__':
    unittest.main()

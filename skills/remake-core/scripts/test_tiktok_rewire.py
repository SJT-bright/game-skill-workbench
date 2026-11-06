#!/usr/bin/env python3
"""生成时预防 P01 / P14 / P10 (Round 3 I2): `tiktok_finalize.py rewire-ads` and the inventory lists.

Before, stage 2 of an English game asked the AI to rewire the original's ad manager by hand; a missed branch or a
copied old RewardedService.js locked the game after an ad or used the wrong timeout (普查: ad_lock_after_close 50
games, ad_timeout 32). The growth entries kept their own amounts (切水果 REWARD = 10 gems). Fixtures are the real
files (fixtures_rewire/, copied unchanged from the game folders):
  1 old way    the originals create rewarded ads in game code (the A1 gate pattern finds them) and the old
               inventory has no rewire_todo / delete_list
  2 搭桥小能手  TTSdk.js (own multi-platform SDK, one ad object): rewire-ads rewrites showVideoAd to the generated
               AdBridge.js, createVideoAd gets an inert ad; game code then has 0 createRewardedVideoAd, parses, and
               the bridge on a fake tt grants a finished video once, never late, never locks (normal, X, late16,
               nocallback + tap); a second run changes nothing
  3 埃及宝石    HexPlatform.rewarded (180 s timer, shared lock, returns {promise, cancel}): not recognised, listed
               in rewire_todo, file byte-identical
  4 拇指弹球    old kit RewardedService.js at assets/platform/: listed in kit_copies; after rewire-ads + sync the
               game code has 0 createRewardedVideoAd outside the kit module
  5 切水果      HomeUI.js new MissionFlow({reward: ... + REWARD}): REWARD = 10 is gone, the reward pays
               growthReward() (5B), rewardText follows it
  6 P10        best-score and reward writes are listed as save_best / save_grant in rewire_todo; code that already
               uses SaveStore.best / grant, or only reads, is not
  7 P14        share / cross-promotion / rank calls go to delete_list
  8 CLI        `inventory` writes the three lists; `rewire-ads` rewrites and refreshes platform-inventory.json
  9 speed      plan + rewire on all fixtures under 3 seconds
Run: python3 test_tiktok_rewire.py   (needs node for 2 and 5)
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tiktok_finalize as F  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402
import tiktok_rewire as R  # noqa: E402
from package_gates.ads_static import CREATE_CALL  # noqa: E402

FX = HERE / 'fixtures_rewire'
KIT = T.KIT_DIR
OLD_RS = KIT / 'tools' / 'kit_versions' / 'RewardedService' / \
    '04121e95bef876cd22b2490f94216b652353a71c310eca09135c08453a8830bd.txt'   # = ThumbPinball-v6 assets/platform/
NODE = shutil.which('node')

SAVES = r"""
// 旋律动物园 / 海洋逃脱 / 方块冲冲 style (written from the census findings, not verbatim)
var Data = {
    onGameOver: function (score) {
        var best = Number(cc.sys.localStorage.getItem('best') || 0);
        if (best && score > best) cc.sys.localStorage.setItem('best', score);
    },
    claimDaily: function (n) {
        this.coins += n;
        this.refreshCoins();
        tt.setStorageSync('coins', this.coins);
    },
    goodBest: function (score) { save.best('best', score); },
    goodGrant: function (n, done) { save.grant({coins: n}, done); },
    readOnly: function () { return Number(cc.sys.localStorage.getItem('coins') || 0); }
};
"""
SOCIAL = """
cc.Class({ extends: cc.Component,
    onShare () { tt.shareAppMessage({title: 'Play'}); },
    onMore () { tt.navigateToMiniProgram({appId: 'x'}); },
    onRank () { var ctx = tt.getOpenDataContext(); ctx.postMessage({type: 'rank'}); }
});
"""

HARNESS = r"""
// Bridge on a fake tt with a virtual clock (same rules as remake-ads ad-timeout-and-regression.md, v7.4).
var path = require('path');
var dir = process.argv[2];
var t = 0, ticks = [], ads = [], touch = [];
var tt = global.tt = {
  canIUse: function () { return true; },
  onHide: function () {}, offHide: function () {}, onShow: function () {}, offShow: function () {},
  onTouchStart: function (f) { touch.push(f); },
  offTouchStart: function (f) { touch = touch.filter(function (g) { return g !== f; }); },
  createRewardedVideoAd: function () {
    var ad = {close: [], err: [], mode: null, started: null};
    ad.onClose = function (f) { ad.close.push(f); }; ad.offClose = function (f) { ad.close = ad.close.filter(function (g) { return g !== f; }); };
    ad.onError = function (f) { ad.err.push(f); }; ad.offError = function (f) { ad.err = ad.err.filter(function (g) { return g !== f; }); };
    ad.show = function () { return new Promise(function (res) { ad.started = res; }); };
    ad.end = function (done) { ad.close.slice().forEach(function (f) { f({isEnded: done}); }); };
    ads.push(ad); return ad;
  }
};
var config = require(path.join(dir, 'PlatformConfig.js'));
var RS = require(path.join(dir, 'RewardedService.js'));
var B = require(path.join(dir, 'AdBridge.js'));
var svc = new RS({now: function () { return t; }, autoPoll: false});
B.useService(svc);
function flush() { var p = Promise.resolve(); for (var i = 0; i < 10; i++) p = p.then(function () {}); return p; }
async function advance(ms) { for (var x = 0; x < ms; x += 100) { t += 100; svc.tick(); await flush(); } }
var fn = B['TTSdk.showVideoAd'];
function ask() { var r = {calls: []}; fn.call({}, function () {}, function () {}, function (v) { r.calls.push(v); }); return r; }
var out = {};
(async function () {
  var a = ask(); await flush(); ads[ads.length - 1].started(); await flush(); ads[ads.length - 1].end(true); await flush();
  out.normal = a.calls;
  var b = ask(); await flush(); ads[ads.length - 1].started(); await flush(); ads[ads.length - 1].end(false); await flush();
  out.x = b.calls;
  var c = ask(); await flush(); var late = ads[ads.length - 1]; await advance(15200);
  out.late16_at_15s = c.calls.slice();
  late.started(); await flush(); late.end(true); await flush();
  out.late16_after = c.calls;
  var d = ask(); await flush(); ads[ads.length - 1].started(); await flush(); ads[ads.length - 1].end(true); await flush();
  out.again_after_timeout = d.calls;
  var e = ask(); await flush(); ads[ads.length - 1].started(); await flush(); await advance(30200);
  out.nocallback_armed = touch.length;
  touch.slice().forEach(function (f) { f({}); }); await flush();
  out.nocallback_after_tap = e.calls;
  var g = ask(); await flush(); ads[ads.length - 1].started(); await flush(); ads[ads.length - 1].end(true); await flush();
  out.after_nocallback = g.calls;
  config.normalLevelCoins = 4;
  out.growth = [B.growthAmount(), config.growthReward(), B.growthText(' Gems')];
  var d2 = {gems: 1};
  var reward = new Function('require', 'd', process.argv[3]);
  reward(function (name) { if (name !== 'AdBridge') throw new Error(name); return B; }, d2);
  out.fruit_gems = d2.gems;
  console.log(JSON.stringify(out));
})().catch(function (e) { console.log(JSON.stringify({error: String(e && e.stack || e)})); });
"""


def project(root, files):
    """A Cocos 2.4 project with the given {relpath: bytes}."""
    (root / 'assets' / 'scenes').mkdir(parents=True)
    (root / 'assets' / 'scenes' / 'Main.fire.meta').write_text(
        '{"ver": "1.2.9", "uuid": "1b2c3d4e-0000-4000-8000-00000000abcd", "importer": "scene"}')
    (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
    for rel, data in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return root


def fixture(rel):
    return (FX / rel).read_bytes()


def game_creates(root):
    """createRewardedVideoAd in game code (everything under assets/ except the kit RewardedService.js)."""
    out = {}
    for p in (Path(root) / 'assets').rglob('*'):
        rel = p.relative_to(root).as_posix()
        if p.suffix in ('.js', '.ts') and p.is_file() and rel != 'assets/tiktok-platform/RewardedService.js':
            text = p.read_text(encoding='utf-8', errors='replace')
            n = len(re.findall(r'createRewardedVideoAd', R.mask(text))) + len(CREATE_CALL.findall(text))
            if n:
                out[rel] = n
    return out


class Rewire(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='rewire-'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_1_old_way(self):
        root = project(self.tmp / 'p', {'assets/scripts/sdk/TTSdk.js': fixture('dqiao/TTSdk.js'),
                                        'assets/scripts/HexPlatform.js': fixture('egypt/HexPlatform.js')})
        self.assertEqual(sorted(game_creates(root)), ['assets/scripts/HexPlatform.js', 'assets/scripts/sdk/TTSdk.js'])
        old = F.inventory(root)['categories']          # the old inventory: file names and hit counts only
        self.assertTrue(old['rewarded_ad'])
        self.assertFalse(any('function' in row or 'fix' in row for row in old['rewarded_ad']))

    @unittest.skipUnless(NODE, 'node not installed')
    def test_2_dqiao_rewired(self):
        root = project(self.tmp / 'p', {'assets/scripts/sdk/sdk/TTSdk.js': fixture('dqiao/TTSdk.js'),
                                        'assets/scripts/sdk/sdk.ts': fixture('dqiao/sdk.ts')})
        before_ts = (root / 'assets/scripts/sdk/sdk.ts').read_bytes()
        rec = R.rewire(root)
        self.assertIn('assets/scripts/sdk/sdk/TTSdk.js', rec['changed'])
        self.assertEqual(game_creates(root), {})
        self.assertEqual((root / 'assets/scripts/sdk/sdk.ts').read_bytes(), before_ts)   # the wrapper still works
        self.assertFalse([r for r in rec['rewire_todo'] if r['kind'] == 'ad'])
        new = (root / 'assets/scripts/sdk/sdk/TTSdk.js').read_bytes()
        self.assertIn(b'\r\n', new)                                              # line endings kept
        self.assertIn(b'"TTSdk.showVideoAd"', new)
        for rel in ('assets/scripts/sdk/sdk/TTSdk.js', R.BRIDGE_PATH):
            ok = subprocess.run([NODE, '--check', str(root / rel)], capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(R.rewire(root)['changed'], [])                          # second run: nothing
        out = self._harness(root, "d.gems = (d.gems || 0) + require('AdBridge').growthAmount();")
        self.assertEqual(out['normal'], [True])
        self.assertEqual(out['x'], [False])
        self.assertEqual(out['late16_at_15s'], [False])
        self.assertEqual(out['late16_after'], [False])                           # no late reward
        self.assertEqual(out['again_after_timeout'], [True])                     # not locked
        self.assertEqual(out['nocallback_armed'], 1)
        self.assertEqual(out['nocallback_after_tap'], [False])
        self.assertEqual(out['after_nocallback'], [True])

    def _harness(self, root, reward_line):
        kit = self.tmp / 'kit'
        kit.mkdir(exist_ok=True)
        for name in ('RewardedService.js', 'PlatformConfig.js'):
            shutil.copy(KIT / 'assets' / 'tiktok-platform' / name, kit / name)
        shutil.copy(root / R.BRIDGE_PATH, kit / 'AdBridge.js')
        (kit / 'h.js').write_text(HARNESS, encoding='utf-8')
        run = subprocess.run([NODE, str(kit / 'h.js'), str(kit), reward_line], capture_output=True, text=True,
                             timeout=30)
        out = json.loads(run.stdout.strip().splitlines()[-1])
        self.assertNotIn('error', out, out.get('error'))
        return out

    def test_3_egypt_listed(self):
        root = project(self.tmp / 'p', {'assets/scripts/HexPlatform.js': fixture('egypt/HexPlatform.js')})
        rec = R.rewire(root)
        self.assertEqual(rec['changed'], [])
        self.assertEqual((root / 'assets/scripts/HexPlatform.js').read_bytes(), fixture('egypt/HexPlatform.js'))
        rows = [r for r in rec['rewire_todo'] if r['kind'] == 'ad']
        self.assertEqual([(r['function'], r['auto']) for r in rows], [('rewarded', False)])
        self.assertIn('promise, cancel', rows[0]['why'])
        # its own add-to-home / revisit code calls api[method]() with the method name in a string
        growth = sorted({(r['function'], r['shape'], r['auto']) for r in rec['rewire_todo'] if r['kind'] == 'growth'})
        self.assertEqual(growth, [('start', 'direct_sdk', False), ('verify', 'direct_sdk', False)])

    def test_4_pinball_old_kit(self):
        root = project(self.tmp / 'p', {'assets/platform/RewardedService.js': OLD_RS.read_bytes(),
                                        'assets/tiktok-platform/PlatformConfig.js': b"var c = {appId: '1'};\n"})
        plan = R.plan(root)
        self.assertEqual([k['file'] for k in plan['kit_copies']], ['assets/platform/RewardedService.js'])
        self.assertFalse(plan['rewire_todo'])
        R.rewire(root)
        self.assertEqual(sorted(game_creates(root)), ['assets/platform/RewardedService.js'])   # until sync
        F.finalize_sync(root, 'localize', policy='new')
        self.assertEqual(game_creates(root), {})

    @unittest.skipUnless(NODE, 'node not installed')
    def test_5_fruitslice_growth(self):
        root = project(self.tmp / 'p', {'assets/scripts/HomeUI.js': fixture('fruitslice/HomeUI.js'),
                                        'assets/scripts/sdk/sdk/TTSdk.js': fixture('dqiao/TTSdk.js')})
        self.assertIn('REWARD = 10', fixture('fruitslice/HomeUI.js').decode())
        rec = R.rewire(root)
        text = (root / 'assets/scripts/HomeUI.js').read_text(encoding='utf-8')
        self.assertNotIn('REWARD = 10', text)
        self.assertIsNone(re.search(r'\bREWARD\b', R.mask(text)))
        line = re.search(r'reward: function \(kind, d\) \{ (.*?) \},', text).group(1)
        self.assertIn("require('AdBridge').growthAmount()", line)
        self.assertIn("growthText(\" Gems\")", text)
        self.assertIn('assets/scripts/HomeUI.js', rec['changed'])
        self.assertFalse([r for r in rec['rewire_todo'] if r['kind'] == 'growth'])
        ok = subprocess.run([NODE, '--check', str(root / 'assets/scripts/HomeUI.js')], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        out = self._harness(root, line)
        self.assertEqual(out['growth'], [20, 20, '+20 Gems'])      # 5B with B = 4
        self.assertEqual(out['fruit_gems'], 21)

    def test_6_save_sites(self):
        root = project(self.tmp / 'p', {'assets/scripts/Data.js': SAVES.encode()})
        rows = R.plan(root)['rewire_todo']
        got = sorted((r['kind'], r['function']) for r in rows)
        self.assertEqual(got, [('save_best', 'onGameOver'), ('save_grant', 'claimDaily')])
        self.assertTrue(all('SaveStore.' in r['fix'] for r in rows))

    def test_7_delete_list(self):
        root = project(self.tmp / 'p', {'assets/scripts/Social.js': SOCIAL.encode(),
                                        'assets/scripts/sdk/sdk/TTSdk.js': fixture('dqiao/TTSdk.js')})
        rows = R.plan(root)['delete_list']
        social = sorted((r['kind'], r['function']) for r in rows if r['file'].endswith('Social.js'))
        self.assertEqual(social, [('cross_promo', 'onMore'), ('rank', 'onRank'), ('share', 'onShare')])
        self.assertIn(('share', 'share'), [(r['kind'], r['function']) for r in rows if 'TTSdk' in r['file']])

    def test_8_cli(self):
        root = project(self.tmp / 'p', {'assets/scripts/sdk/sdk/TTSdk.js': fixture('dqiao/TTSdk.js'),
                                        'assets/scripts/HexPlatform.js': fixture('egypt/HexPlatform.js')})
        script = str(HERE / 'tiktok_finalize.py')
        inv = root / 'docs' / 'english' / 'platform-inventory.json'
        r1 = subprocess.run([sys.executable, script, 'inventory', '--project', str(root)], capture_output=True,
                            text=True)
        self.assertEqual(r1.returncode, 0, r1.stderr)
        data = json.loads(inv.read_text(encoding='utf-8'))
        self.assertEqual(sorted({r['function'] for r in data['rewire_todo'] if r['kind'] == 'ad'}),
                         ['createVideoAd', 'rewarded', 'showVideoAd'])
        self.assertTrue(data['delete_list'])
        r2 = subprocess.run([sys.executable, script, 'rewire-ads', '--project', str(root)], capture_output=True,
                            text=True)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn('rewire-ads:', r2.stdout)
        data = json.loads(inv.read_text(encoding='utf-8'))
        self.assertEqual([r['function'] for r in data['rewire_todo'] if r['kind'] == 'ad'], ['rewarded'])
        self.assertTrue((root / '.tiktok-kit' / 'rewire-ads.json').is_file())
        self.assertTrue((root / '.tiktok-kit' / 'rewire-backup' / 'assets/scripts/sdk/sdk/TTSdk.js').is_file())

    def test_10_shapes_from_the_library(self):
        """Signatures seen when rewire-ads ran over the 64 projects of the learning library (shortened)."""
        src = {
            # WaterGame RewardedAd.ts: TS function types in the parameters
            'Water.ts': "export class A { request(reward: () => void, fail: (reason: string) => void) {\n"
                        "  if (busy) { fail('open'); return; } const ad = tt.createRewardedVideoAd({adUnitId: 'x'});\n"
                        "  ad.onClose(r => { if (r.isEnded) reward(); else fail('no'); }); ad.show(); } }\n",
            # BrothersRush AdapterTT.ts: cb(false, 'reason') here, cb(true) elsewhere
            'Brothers.ts': "export class B { showVideo(param: VideoParam, cb) { if (!x) { cb(false, 'none'); return; }\n"
                           "  this.v = tt.createRewardedVideoAd({adUnitId: param.id}); this.cb = cb; this.v.show(); } }\n",
            # Mahjong WxPlatform.ts: numeric codes 0 / 1 / 2 -> meaning unknown
            'Mahjong.ts': "export class C { showRewardVideo(callback?: Function) { var v = tt.createRewardedVideoAd({});\n"
                          "  v.onClose(r => { callback(r.isEnded ? 1 : 0); }); v.onError(() => callback(2)); v.show(); } }\n",
            # a Promise of a result object (麻将 RewardedCore)
            'Core.js': "var D = { request: function (id) { return new Promise(function (resolve) {\n"
                       "  var ad = tt.createRewardedVideoAd({adUnitId: id}); ad.onClose(function (r) {\n"
                       "  resolve({status: r.isEnded ? 'completed' : 'cancelled'}); }); ad.show(); }); } };\n",
        }
        # BlockMaze MainLayer.ts: the growth entries give three items, not currency -> by hand, nothing changed
        src['Items.js'] = ("var f = new MissionFlow({store: s, reward: function (k, d) { d.itemHammerCount += 1; "
                           "d.itemBombCount += 1; }, rewardText: {shortcut: ITEMS, profile: ITEMS}, render: r});\n")
        root = project(self.tmp / 'p', {'assets/scripts/' + k: v.encode() for k, v in src.items()})
        growth = [r for r in R.plan(root)['rewire_todo'] if r['kind'] == 'growth']
        self.assertEqual([(g['file'].rsplit('/', 1)[-1], g['auto']) for g in growth], [('Items.js', False)])
        rows = {r['file'].rsplit('/', 1)[-1]: r for r in R.plan(root)['rewire_todo'] if r['kind'] == 'ad'}
        self.assertEqual((rows['Water.ts']['auto'], rows['Brothers.ts']['auto']), (True, True))
        self.assertEqual((rows['Mahjong.ts']['auto'], rows['Core.js']['auto']), (False, False))
        R.rewire(root)
        bridge = (root / R.BRIDGE_PATH).read_text(encoding='utf-8')
        self.assertIn("call(reward, []); }, function (r) { call(fail, [r.message]); }, false)", bridge)
        self.assertIn("call(cb, [true]); }, function (r) { call(cb, [false, r.message]); }, false)", bridge)
        self.assertNotIn('Mahjong', bridge)
        self.assertIn('createRewardedVideoAd', (root / 'assets/scripts/Mahjong.ts').read_text(encoding='utf-8'))
        self.assertEqual((root / 'assets/scripts/Items.js').read_text(encoding='utf-8'), src['Items.js'])

    def test_11_cocos3_by_hand(self):
        """R4N2: Cocos 3.x ad managers are rewired to the generated AdBridge3x.ts (ES import, TikTokKit
        .RewardedService); growth rewards stay by hand; no 2.4 AdBridge.js is written."""
        src = ("export class A { request(reward: () => void, fail: (reason: string) => void) {\n"
               "  const ad = tt.createRewardedVideoAd({adUnitId: 'x'}); ad.onClose(r => { if (r.isEnded) reward();"
               " else fail('no'); }); ad.show(); } }\n")
        root = project(self.tmp / 'p', {'assets/scripts/Water.ts': src.encode(),
                                        'assets/scripts/HomeUI.js': fixture('fruitslice/HomeUI.js')})
        (root / 'project.json').unlink()
        (root / 'package.json').write_text('{"creator": {"version": "3.8.6"}}')
        rows = [r for r in R.plan(root)['rewire_todo'] if r['kind'] in ('ad', 'growth')]
        self.assertEqual(sorted((r['kind'], r['auto']) for r in rows), [('ad', True), ('growth', False)])
        rec = R.rewire(root)
        self.assertEqual(sorted(rec['changed']), sorted(['assets/scripts/Water.ts', R.BRIDGE3X_PATH]))
        self.assertFalse((root / R.BRIDGE_PATH).exists())
        water = (root / 'assets/scripts/Water.ts').read_text(encoding='utf-8')
        self.assertIn("import { B as __TikTokAdBridge3x } from '../tiktok-platform/AdBridge3x';", water)
        self.assertNotIn('createRewardedVideoAd', water)

    # ------------------------------------------------------------ R4N2 (补查2 第 4 组): 3.x original ad entries
    DINO_SDK = ("import { sys, loader, Prefab } from 'cc';\nimport { Wechat } from './Platform/wechat/wechat';\n"
                "export class SdkMgr {\n    private channel: Channel = Channel.DEFAULT;\n"
                "    /**观看广告 */\n"
                "    public showRewardAd(des: any, callback: Function, cancel?: Function, fail?: Function) {\n"
                "        let cb = () => {\n            loader.loadRes('Alert', Prefab, (err, prefab: Prefab) => {})\n"
                "            callback();\n        }\n        console.log(\"观看广告\", des);\n"
                "        switch (this.channel) {\n            case Channel.DEFAULT: {\n                cb();\n"
                "                break;\n            }\n            case Channel.TT: {\n                break;\n"
                "            }\n            case Channel.WECHAT: {\n"
                "                Wechat.showRewardVideoAd().then((isSuc) => {\n"
                "                    if (isSuc) { cb(); } else if (cancel) { cancel(); }\n"
                "                }, (res?) => { if (fail) { fail(); } })\n                break;\n            }\n"
                "        }\n    }\n}\n")
    # 合成进化恐龙 preMain.onClickDino after the first English pass: this.node written into the cancel slot
    DINO_CALL = ("export class preMain {\n  onClickDino() {\n"
                 "    SdkMgr.ins.showRewardAd(\"观看激励视频-获取恐龙\", () => { GD.addSavedDino(1); }, this.node);\n"
                 "  }\n  onEgg() { SdkMgr.ins.showRewardAd(\"龙蛋\", () => { this.speed(); }); }\n}\n")
    GIANT = ("export class GameLogic {\n    public static pay (shareId: number, callback: Function) {\n"
             "        AudioManager.instance.pauseAll();\n        this.isWatchVideoAd = true;\n"
             "        if ((this.platform === 'ios' || this.platform === 'wx') && window.bondSDK) {\n"
             "            window.bondSDK.pay({\n                shareId: shareId,\n"
             "                success: ()=>{ this.isWatchVideoAd = false; callback(null); },\n"
             "                fail: (err)=>{ this.isWatchVideoAd = false; callback('fail', err); }\n            });\n"
             "        } else if (this.platform === 'cocosPlay') {\n            // jkwSDK.showRewardedVideoAd\n"
             "        } else {\n            this.isWatchVideoAd = false;\n            AudioManager.instance.resumeAll();\n"
             "            callback && callback(null);\n        }\n    }\n}\n")
    PIN_FIRE = ('[{"__type__": "cc.Button", "clickEvents": [{"__id__": 3}]},\n {\n    "__type__": "cc.ClickEvent",\n'
                '    "target": {\n      "__id__": 2\n    },\n    "component": "BallGameHall",\n'
                '    "_componentId": "",\n    "handler": "showVideoCallBack",\n    "customEventData": ""\n  },\n'
                ' {\n    "__type__": "cc.ClickEvent",\n    "target": {\n      "__id__": 2\n    },\n'
                '    "component": "BallGameHall",\n    "_componentId": "",\n    "handler": "onStartGame",\n'
                '    "customEventData": ""\n  }]\n')
    PIN_JS = ("cc.Class({\n    extends: cc.Component,\n    onStartGame: function () { cc.director.loadScene('g'); },\n"
              "    showVideoTip: function () {}\n});\n")

    def _v3(self, files):
        root = project(self.tmp / 'v3', {k: v.encode() for k, v in files.items()})
        (root / 'project.json').unlink()
        (root / 'package.json').write_text('{"creator": {"version": "3.5.0"}}')
        return root

    def test_12_dino_browser_grant_rewired(self):
        """合成进化恐龙: SdkMgr.showRewardAd grants in Channel.DEFAULT (browser) -> rewired to AdBridge3x; the
        bridge grants only in the success callback; the ownerNode call is listed."""
        root = self._v3({'assets/Script/tyq3.x/SdkMgr.ts': self.DINO_SDK, 'assets/pack1/src/preMain.ts': self.DINO_CALL})
        todo = R.plan(root)['rewire_todo']
        ad = [r for r in todo if r['kind'] == 'ad']
        self.assertEqual([(r['function'], r['auto'], r.get('nonplatform_grant')) for r in ad],
                         [('showRewardAd', True, True)])
        calls = [r for r in todo if r['kind'] == 'ad_call']
        self.assertEqual([(r['file'].rsplit('/', 1)[-1], r['line']) for r in calls], [('preMain.ts', 3)])
        self.assertIn('callback slot 3', calls[0]['why'])
        R.rewire(root)
        sdk = (root / 'assets/Script/tyq3.x/SdkMgr.ts').read_text(encoding='utf-8')
        self.assertIn("import { B as __TikTokAdBridge3x } from '../../tiktok-platform/AdBridge3x';", sdk)
        self.assertNotIn('Channel.DEFAULT: {', sdk)
        self.assertIn('return __TikTokAdBridge3x["SdkMgr.showRewardAd"].call(this, des, callback, cancel, fail);', sdk)
        bridge = (root / R.BRIDGE3X_PATH).read_text(encoding='utf-8')
        self.assertIn("run(key(des, 'double_coins'), function () { call(callback, []); }, function (r) { if (r && "
                      "r.status === 'cancelled' && typeof cancel === 'function') call(cancel, []); else "
                      "call(fail, [r.message]); }, false);", bridge)
        self.assertIn('globalThis as any).TikTokKit', bridge)

    def test_13_giant_web_branch_rewired(self):
        """奔跑吧巨人: GameLogic.pay's last else grants callback(null) with no ad -> rewired, err-first kept."""
        root = self._v3({'assets/script/framework/gameLogic.ts': self.GIANT})
        ad = [r for r in R.plan(root)['rewire_todo'] if r['kind'] == 'ad']
        self.assertEqual([(r['function'], r['auto'], r['grant_line']) for r in ad], [('pay', True, 13)])
        R.rewire(root)
        gl = (root / 'assets/script/framework/gameLogic.ts').read_text(encoding='utf-8')
        self.assertNotIn('callback && callback(null)', gl)
        bridge = (root / R.BRIDGE3X_PATH).read_text(encoding='utf-8')
        self.assertIn("function () { call(callback, [null]); }, function (r) { call(callback, ['fail', r]); }", bridge)

    def test_14_pinball_missing_handler(self):
        """弹球传奇: the home button names BallGameHall.showVideoCallBack, which does not exist -> ad_handler row;
        an existing handler is not listed; old code had no such row."""
        root = project(self.tmp / 'pin', {'assets/BallMaster/BallScene/BallGameHall.fire': self.PIN_FIRE.encode(),
                                          'assets/BallMaster/BallScript/BallGameHall.js': self.PIN_JS.encode()})
        rows = [r for r in R.plan(root)['rewire_todo'] if r['kind'] == 'ad_handler']
        self.assertEqual([(r['component'], r['function']) for r in rows], [('BallGameHall', 'showVideoCallBack')])
        (root / 'assets/BallMaster/BallScript/BallGameHall.js').write_text(
            self.PIN_JS.replace('showVideoTip', 'showVideoCallBack'))
        self.assertEqual([r for r in R.plan(root)['rewire_todo'] if r['kind'] == 'ad_handler'], [])

    def test_15_overlay_canvas(self):
        """X goes to the visible Canvas whose camera has the highest priority (合成进化恐龙: 4 Canvas, CanvasBg is
        first and lowest), not the first one found; inactive canvases and disabled cameras are skipped."""
        js = R.BRIDGE3X_HEAD.split('// BEGIN pickOverlayCanvas', 1)[1].split('// END pickOverlayCanvas', 1)[0]
        js = js.split('\n', 1)[1].replace('export function', 'function')
        probe = js + r"""
function cv(name, prio, opts) { opts = opts || {}; return {name: name, enabled: true, node: {activeInHierarchy: opts.active !== false},
  cameraComponent: {priority: prio, enabled: opts.cam !== false, node: {activeInHierarchy: true}}}; }
var four = [cv('CanvasBg', 0), cv('Canvas', 1), cv('CanvasUI', 3), cv('CanvasTop', 5, {active: false})];
var out = [pickOverlayCanvas(four).name, pickOverlayCanvas([cv('A', 2), cv('B', 2)]).name,
  pickOverlayCanvas([cv('A', 4, {cam: false}), cv('B', 1)]).name, String(pickOverlayCanvas([]))];
console.log(JSON.stringify(out));
"""
        r = subprocess.run(['node', '-e', probe], capture_output=True, text=True, timeout=20)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), ['CanvasUI', 'B', 'B', 'null'])

    # ------------------------------------------------------------ R4P2: conditional / logical branches (terser)
    TERN24 = ("var SdkMgr = cc.Class({ extends: cc.Component,\n"
              "    showRewardVideo: function (key, cb) {\n"
              "        cc.sys.isBrowser ? (this.log('web'), cb && cb(true))\n"
              "            : tt.createRewardedVideoAd({adUnitId: key}).onClose(function (r) { cb(r && r.isEnded); });\n"
              "    }\n});\nmodule.exports = SdkMgr;\n")
    OR3X = ("export class Ads {\n    public static showVideoAd(cb: Function) {\n"
            "        if (sys.platform === sys.Platform.BYTEDANCE_MINI_GAME) {\n"
            "            return void tt.createRewardedVideoAd({adUnitId: 'x'}).show();\n        }\n"
            "        sys.isNative || (this.busy = false, cb(null));\n    }\n}\n")
    GOOD = ("var A = cc.Class({ extends: cc.Component,\n"
            "    showRewardAd: function (key, ok) {\n"
            "        window.tt ? (this.ad = tt.createRewardedVideoAd({adUnitId: key}),\n"
            "            this.ad.onClose(function (r) { r && r.isEnded ? ok && ok(true) : ok && ok(false); }),\n"
            "            this.ad.show()) : ok && ok(false);\n"
            "    },\n    showVideo: function (cb) { cc.sys.isBrowser && cb && cb(!1, 'no ad'); }\n});\n")

    def _grant_line(self, text, name):
        masked = R.mask(text)
        f = [g for g in R.functions(text, masked) if g['name'] == name][0]
        return R.direct_grant(text, masked, f)

    def test_16_terser_branches(self):
        """R4P2: `p ? (x, cb(true)) : ad()` (2.4) and `p || (x, cb(null))` (3.x) are non-platform grants; the same
        minified as terser writes them too. Old code read if/else/switch only and missed all four."""
        self.assertEqual(self._grant_line(self.TERN24, 'showRewardVideo'), 3)
        self.assertEqual(self._grant_line(self.OR3X, 'showVideoAd'), 6)
        mini24 = ('var o=cc.Class({showRewardAd:function(t,e,i,n){1===this.channel?tt.createRewardedVideoAd?'
                  'this.ttShow(e,i,n):n&&n():e&&e()}});')
        mini3 = ('class G{static pay(s,c){AudioManager.instance.pauseAll(),"ios"!==this.platform||!window.bondSDK?'
                 '"cocosPlay"===this.platform||(this.isWatchVideoAd=!1,c&&c(null)):window.bondSDK.pay({shareId:s,'
                 'success:()=>{c(null)},fail:e=>{c("fail",e)}})}}')
        self.assertIsNotNone(self._grant_line(mini24, 'showRewardAd'))
        self.assertIsNotNone(self._grant_line(mini3, 'pay'))
        root = project(self.tmp / 't24', {'assets/scripts/SdkMgr.js': self.TERN24.encode()})
        rows = [r for r in R.plan(root)['rewire_todo'] if r['kind'] == 'ad' and r.get('nonplatform_grant')]
        self.assertEqual([(r['function'], r.get('nonplatform_grant'), r.get('grant_line')) for r in rows],
                         [('showRewardVideo', True, 3)])
        root = self._v3({'assets/scripts/Ads.ts': self.OR3X})
        rows = [r for r in R.plan(root)['rewire_todo'] if r['kind'] == 'ad' and r.get('nonplatform_grant')]
        self.assertEqual([(r['function'], r.get('nonplatform_grant')) for r in rows], [('showVideoAd', True)])

    def test_17_terser_good_shapes(self):
        """R4P2: the reward only in the watched callback of the platform branch, failure calls on the other side
        (`ok(false)`, `cb(!1, 'no ad')`), a result test `r.isEnded ? ...` -> no non-platform grant."""
        self.assertIsNone(self._grant_line(self.GOOD, 'showRewardAd'))
        self.assertIsNone(self._grant_line(self.GOOD, 'showVideo'))
        root = project(self.tmp / 'good', {'assets/scripts/A.js': self.GOOD.encode()})
        self.assertEqual([r for r in R.plan(root)['rewire_todo'] if r.get('nonplatform_grant')], [])

    def test_9_speed(self):
        files = {'assets/scripts/a/TTSdk.js': fixture('dqiao/TTSdk.js'), 'assets/scripts/a/sdk.ts': fixture('dqiao/sdk.ts'),
                 'assets/scripts/HexPlatform.js': fixture('egypt/HexPlatform.js'),
                 'assets/scripts/HomeUI.js': fixture('fruitslice/HomeUI.js'), 'assets/scripts/Data.js': SAVES.encode()}
        root = project(self.tmp / 'p', files)
        t0 = time.time()
        R.plan(root)
        R.rewire(root)
        self.assertLess(time.time() - t0, 3.0)


if __name__ == '__main__':
    result = unittest.main(exit=False, verbosity=2).result
    sys.exit(0 if result.wasSuccessful() else 1)

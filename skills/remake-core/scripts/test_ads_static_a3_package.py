#!/usr/bin/env python3
"""R4O6: package-level test for package_gates/ads_static.py A3_nonplatform_grant (R4N2, 补查2 第 4 组).
A fake 3.x mini-game ZIP whose GameLogic.pay grants `callback(null)` on the last else (奔跑吧巨人) is written to disk,
read back like a package and run through check(view) and package_gates.run(): a new game blocks, a game on the frozen
legacy list only warns, the rewired module (calls AdBridge3x) passes. Same for a 2.4 cc.Class bundle (合成进化恐龙's
SdkMgr.showRewardAd default channel). R4P2: terser builds that turn the branch into `p?(c,d(null)):ad()`,
`p||(c,d(null))` or `p&&d(!0)` are caught too (2.4 and 3.x); the reward paid only in the platform branch or the
watched callback, with failure calls (`d("fail")`, `d(!1)`) on the other side, passes.
Run: python3 -B test_ads_static_a3_package.py   (well under a second)"""
import io
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_gates as gates  # noqa: E402
from package_gates import ads_static  # noqa: E402
import test_package_gates_content as T  # noqa: E402

HEAD3 = ('System.register("chunks:///_virtual/gameLogic.ts",["cc"],function(e){"use strict";var t;return{setters:'
         '[function(e){t=e.cclegacy}],execute:function(){t._RF.push({},"abc","GameLogic",void 0);')
TAIL3 = 't._RF.pop()}}});'
# 奔跑吧巨人 GameLogic.pay as the 3.x build writes it (readable)
GIANT = HEAD3 + ('e("GameLogic", class GameLogic {\n  static pay(shareId, callback) {\n'
                 '    AudioManager.instance.pauseAll();\n    this.isWatchVideoAd = true;\n'
                 "    if ((this.platform === 'ios' || this.platform === 'wx') && window.bondSDK) {\n"
                 '      window.bondSDK.pay({ shareId: shareId, success: () => { this.isWatchVideoAd = false; callback(null); },'
                 ' fail: (err) => { this.isWatchVideoAd = false; callback("fail", err); } });\n'
                 "    } else if (this.platform === 'cocosPlay') {\n    } else {\n      this.isWatchVideoAd = false;\n"
                 '      AudioManager.instance.resumeAll();\n      callback && callback(null);\n    }\n  }\n});\n') + TAIL3
# the same, minified with the if/else kept
GIANT_MIN = HEAD3 + ('e("GameLogic",class{static pay(s,c){if(AudioManager.instance.pauseAll(),this.isWatchVideoAd=!0,'
                     '("ios"===this.platform||"wx"===this.platform)&&window.bondSDK)window.bondSDK.pay({shareId:s,success:'
                     '()=>{this.isWatchVideoAd=!1,c(null)},fail:e=>{this.isWatchVideoAd=!1,c("fail",e)}});else if("cocosPlay"'
                     '===this.platform);else{this.isWatchVideoAd=!1,AudioManager.instance.resumeAll(),c&&c(null)}}}),') + TAIL3
# terser's usual form: the if/else became a conditional expression
GIANT_TERNARY = HEAD3 + ('e("GameLogic",class{static pay(s,c){AudioManager.instance.pauseAll(),this.isWatchVideoAd=!0,'
                         '"ios"!==this.platform&&"wx"!==this.platform||!window.bondSDK?"cocosPlay"===this.platform||'
                         '(this.isWatchVideoAd=!1,AudioManager.instance.resumeAll(),c&&c(null)):window.bondSDK.pay({shareId:s,'
                         'success:()=>{this.isWatchVideoAd=!1,c(null)},fail:e=>{this.isWatchVideoAd=!1,c("fail",e)}})}}),') + TAIL3
# R4P2: terser turned the else into `p || (...)` after an early return
GIANT_OR = HEAD3 + ('e("GameLogic",class{static pay(s,c){if(AudioManager.instance.pauseAll(),this.isWatchVideoAd=!0,'
                    '("ios"===this.platform||"wx"===this.platform)&&window.bondSDK)return void window.bondSDK.pay({'
                    'shareId:s,success:()=>{this.isWatchVideoAd=!1,c(null)},fail:e=>{this.isWatchVideoAd=!1,'
                    'c("fail",e)}});"cocosPlay"===this.platform||(this.isWatchVideoAd=!1,c&&c(null))}}),') + TAIL3
# R4P2 must pass: the reward is paid only in the watched callback of the platform branch, the other side fails
GOOD3_TERNARY = HEAD3 + ('e("GameLogic",class{static showVideo(c){window.tt?(this.ad=tt.createRewardedVideoAd({adUnitId:'
                         '"x"}),this.ad.onClose(r=>{r&&r.isEnded?c(null):c("fail")}),this.ad.show()):c("fail")}}),'
                         ) + TAIL3
# after tiktok_finalize.py rewire-ads: the entry calls the bridge, no direct grant left
GIANT_REWIRED = HEAD3 + ('e("GameLogic",class{static pay(s,c){return __TikTokAdBridge3x["GameLogic.pay"].call(this,s,c)}}),'
                         ) + TAIL3
# 合成进化恐龙 SdkMgr.showRewardAd as a 2.4 cc.Class module: the default channel calls the callback with no ad
DINO24 = ('var o=cc.Class({extends:cc.Component,showRewardAd:function(t,e,i,n){switch(this.channel){case 1:'
          'tt.createRewardedVideoAd?this.ttShow(e,i,n):n&&n();break;default:e&&e()}}});e.exports=o')
# R4P2: the same switch after terser (nested conditional; the default channel is the last operand)
DINO24_TERNARY = ('var o=cc.Class({extends:cc.Component,showRewardAd:function(t,e,i,n){1===this.channel?'
                  'tt.createRewardedVideoAd?this.ttShow(e,i,n):n&&n():e&&e()}});e.exports=o')
BROWSER24_AND = ('var o=cc.Class({extends:cc.Component,showRewardVideo:function(t){cc.sys.isBrowser&&t&&t(!0),'
                 'cc.sys.isBrowser||tt.createRewardedVideoAd({adUnitId:"x"}).show()}});e.exports=o')
GOOD24_TERNARY = ('var o=cc.Class({extends:cc.Component,showRewardAd:function(t,e){cc.sys.platform===cc.sys.BYTEDANCE_GAME?'
                  '(this.ad=tt.createRewardedVideoAd({adUnitId:t}),this.ad.onClose(function(t){t&&t.isEnded?e&&e(!0):'
                  'e&&e(!1)}),this.ad.show()):e&&e(!1)}});e.exports=o')
GOOD24_AND = ('var o=cc.Class({extends:cc.Component,showRewardVideo:function(t){cc.sys.isBrowser&&t&&t(!1,"no ad"),'
              'cc.sys.isBrowser||(this.v=tt.createRewardedVideoAd({adUnitId:"x"}),this.v.onClose(function(e){t&&t(!!e&&'
              'e.isEnded)}),this.v.show())}});e.exports=o')
DINO24_OK = ('var o=cc.Class({extends:cc.Component,showRewardAd:function(t,e,i,n){return window.__TikTokAdBridge'
             '["SdkMgr.showRewardAd"].call(this,t,e,i,n)}});e.exports=o')


def zip_bytes(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


def from_zip(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        return {n: z.read(n) for n in z.namelist() if not n.endswith('/')}


def pkg3x(game_code):
    return from_zip(zip_bytes(T.pkg3x(extra={'assets/main/index.js': (T.MISSIONS + game_code).encode()})))


def pkg24(module_body):
    return from_zip(zip_bytes(T.pkg24(index_js=T.MISSIONS + T.bundle(('SdkMgr', module_body)))))


def a3(files, policy):
    view = gates.PackageView(files, None, 'localize', policy=policy)
    return [(f['id'], f['level']) for f in ads_static.check(view) if f['id'] == 'A3_nonplatform_grant']


class A3Package(unittest.TestCase):
    def assert_new_blocks_legacy_warns(self, files, hit):
        self.assertEqual(a3(files, 'new'), [('A3_nonplatform_grant', 'block')])
        self.assertEqual(a3(files, 'legacy'), [('A3_nonplatform_grant', 'warn')])
        view = gates.PackageView(files, None, 'localize', policy='new')
        found = [f for f in ads_static.check(view) if f['id'] == 'A3_nonplatform_grant'][0]
        self.assertIn(hit, found['evidence']['hits'])
        self.assertIn('rewire-ads', found['message'])
        # through the gate runner the writer and check_package.py use
        res = gates.run(files, None, 'localize', modules=('ads_static',), policy='new')
        self.assertIn('A3_nonplatform_grant', [f['id'] for f in res['blocks']])
        res = gates.run(files, None, 'localize', modules=('ads_static',), policy='legacy')
        self.assertNotIn('A3_nonplatform_grant', [f['id'] for f in res['blocks']])
        self.assertIn('A3_nonplatform_grant', [f['id'] for f in res['warnings']])

    def test_3x_readable_bundle(self):
        self.assert_new_blocks_legacy_warns(pkg3x(GIANT), 'gameLogic/pay')

    def test_3x_minified_bundle(self):
        self.assert_new_blocks_legacy_warns(pkg3x(GIANT_MIN), 'gameLogic/pay')

    def test_24_minified_cc_class_bundle(self):
        self.assert_new_blocks_legacy_warns(pkg24(DINO24), 'SdkMgr/showRewardAd')

    def test_rewired_packages_pass(self):
        for files in (pkg3x(GIANT_REWIRED), pkg24(DINO24_OK)):
            self.assertEqual(a3(files, 'new'), [])

    def test_3x_terser_ternary(self):
        """R4P2 (was the R4O6 expectedFailure): `p ? (x, cb(null)) : platform()` is caught."""
        self.assert_new_blocks_legacy_warns(pkg3x(GIANT_TERNARY), 'gameLogic/pay')

    def test_3x_terser_or(self):
        """R4P2: `if (p) return void platform(); q || (x, c && c(null))`."""
        self.assert_new_blocks_legacy_warns(pkg3x(GIANT_OR), 'gameLogic/pay')

    def test_24_terser_ternary(self):
        """R4P2: 合成进化恐龙's switch as terser writes it: `1===this.channel ? tt... : e && e()`."""
        self.assert_new_blocks_legacy_warns(pkg24(DINO24_TERNARY), 'SdkMgr/showRewardAd')

    def test_24_terser_and(self):
        """R4P2: `cc.sys.isBrowser && t && t(!0), cc.sys.isBrowser || tt.createRewardedVideoAd(...)`."""
        self.assert_new_blocks_legacy_warns(pkg24(BROWSER24_AND), 'SdkMgr/showRewardVideo')

    def test_terser_good_shapes_pass(self):
        """R4P2: the reward only in the platform branch / the watched callback; failure callbacks elsewhere."""
        for files in (pkg3x(GOOD3_TERNARY), pkg24(GOOD24_TERNARY), pkg24(GOOD24_AND)):
            self.assertEqual(a3(files, 'new'), [])


if __name__ == '__main__':
    unittest.main()

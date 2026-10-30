#!/usr/bin/env python3
"""Synthetic bad/good fixtures for the v7.5 content gates (package_gates: mission, startup, webp, ads_static).
No game ZIP needed. Run: python3 -B test_package_gates_content.py"""
import json
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_gates as gates  # noqa: E402
from package_gates import ads_static, mission, startup, webp  # noqa: E402

MISSIONS = 'tt.addShortcut();tt.getShortcutMissionReward();tt.startEntranceMission();' \
           'tt.getEntranceMissionReward();x.canReceiveReward;tt.login({});'


def webp_bytes(kind, payload=b'\x00' * 10):
    tag = b'VP8L' if kind == 'lossless' else b'VP8 '
    chunk = tag + struct.pack('<I', len(payload)) + payload
    return b'RIFF' + struct.pack('<I', 4 + len(chunk)) + b'WEBP' + chunk


def pkg24(extra=None, subpackages=None, game_js='', main_js='', index_js=MISSIONS):
    files = {
        'game.json': json.dumps({'subpackages': subpackages or []}).encode(),
        'project.config.json': b'{}',
        'cocos/cocos2d-js-min.js': b'/* engine */ var cc={};',
        'adapter-min.js': b'/* adapter */',
        'game.js': game_js.encode(),
        'main.js': main_js.encode(),
        'assets/main/index.js': index_js.encode(),
    }
    files.update(extra or {})
    return files


def pkg3x(extra=None, subpackages=None, settings=None, game_js='', index_js=MISSIONS):
    files = {
        'game.json': json.dumps({'subpackages': subpackages or []}).encode(),
        'project.config.json': b'{}',
        'cocos-js/cc.js': b'/* engine */',
        'web-adapter.js': b'/* adapter */',
        'game.js': game_js.encode(),
        'src/settings.json': json.dumps(settings or {'assets': {'preloadBundles': []},
                                                     'splashScreen': {'totalTime': 0}}).encode(),
        'assets/main/index.js': index_js.encode(),
    }
    files.update(extra or {})
    return files


def ids(module, files, board=None, level=None, policy=None):
    view = gates.PackageView(files, None, board, policy=policy)
    return sorted({f['id'] for f in module.check(view) if level is None or f['level'] == level})


def kit_module(name):
    """The kit's own 2.4 module text (assets/tiktok-platform/<name>.js)."""
    kit = Path(__file__).resolve().parent.parent / 'assets' / 'platform-kit' / 'assets' / 'tiktok-platform'
    return (kit / (name + '.js')).read_text(encoding='utf-8')


def kit_missions(login=True):
    """v7.7 (G1k): a new game reaches the five growth APIs only through the kit TikTokMissionService / MissionFlow."""
    return bundle(('TikTokMissionService', kit_module('TikTokMissionService')),
                  ('MissionFlow', kit_module('MissionFlow'))) + ('tt.login({});' if login else '')


class Mission(unittest.TestCase):
    def test_missing_reward_queries_block(self):
        files = pkg24(index_js='tt.addShortcut();tt.startEntranceMission();tt.login({})')
        self.assertEqual(ids(mission, files, level='block', policy='legacy'), ['G1_growth_apis'])
        # v7.7: a new game calling the SDK itself also gets G1k
        self.assertEqual(ids(mission, files, level='block', policy='new'), ['G1_growth_apis', 'G1k_growth_outside_kit'])

    def test_engine_and_adapter_do_not_count(self):
        files = pkg24(index_js='tt.login({})', extra={'adapter-min.js': MISSIONS.encode()})
        self.assertIn('G1_growth_apis', ids(mission, files, level='block'))

    def test_all_five_pass_and_login_warns_only(self):
        # v7.7: through the kit modules a new game has no mission finding at all
        self.assertEqual(ids(mission, pkg24(index_js=kit_missions()), policy='new'), [])
        no_login = pkg24(index_js=kit_missions(login=False))
        self.assertEqual(ids(mission, no_login, level='block', policy='new'), [])
        self.assertEqual(ids(mission, no_login, level='warn', policy='new'), ['W2_login'])

    def test_own_growth_calls_block_new_warn_legacy(self):
        # the v7.5 fixture (game code calls tt.* itself): all five present (no G1), G1k by policy
        self.assertEqual(ids(mission, pkg24(), level='block', policy='new'), ['G1k_growth_outside_kit'])
        self.assertEqual(ids(mission, pkg24(), level='block', policy='legacy'), [])
        self.assertEqual(ids(mission, pkg24(), level='warn', policy='legacy'), ['G1k_growth_outside_kit'])


class Startup(unittest.TestCase):
    BIG = {'subpackages/resources/big.bin': b'\x00' * 4000001}
    SUB = [{'name': 'resources', 'root': 'subpackages/resources/'}]
    STALL = 'if(Date.now()-guard.lastProgress>=15000)guard.fail();'

    def test_g3_watchdog_without_progress_blocks(self):
        files = pkg24(self.BIG, self.SUB, game_js=self.STALL, main_js='tt.loadSubpackage({name:"resources"})')
        self.assertEqual(ids(startup, files, level='block'), ['G3_progress'])

    def test_g3_progress_hook_passes(self):
        files = pkg24(self.BIG, self.SUB, game_js=self.STALL,
                      main_js='cc.assetManager.loadBundle("resources",{onFileProgress:function(){}},cb)')
        self.assertEqual(ids(startup, files, level='block'), [])

    def test_g3_small_subpackage_passes(self):
        files = pkg24({'subpackages/resources/a.bin': b'\x00' * 1000}, self.SUB, game_js=self.STALL)
        self.assertEqual(ids(startup, files, level='block'), [])

    GAME3 = ("var rec=require('./native-recovery');\nSystem.import('cc').then((cc)=>{return application.init(cc);})"
             "%s.then(() => { return application.start(); });")

    def test_g5_awaited_subpackage_blocks(self):
        files = pkg3x({'native-recovery.js': b"exports.ensureResources=function(){return new Promise(function(r){"
                                              b"tt.loadSubpackage({name:'resources',success:r});});};"},
                      game_js=self.GAME3 % '.then(() => rec.ensureResources())')
        self.assertEqual(ids(startup, files, level='block'), ['G5_3x_presubpackage'])

    def test_g5_delegate_registration_passes(self):
        files = pkg3x({'boot.js': b"exports.configure=function(cc){tt.loadSubpackage({name:'resources'});};"},
                      game_js=("var boot=require('./boot');\nSystem.import('cc').then((cc)=>{"
                               "cc.game.onPostBaseInitDelegate.add(() => boot.configure(cc));return application.init(cc);})"
                               ".then(() => { return application.start(); });"))
        self.assertEqual(ids(startup, files, level='block'), [])

    def test_g5_preload_and_g6_splash_block_on_remake_warn_elsewhere(self):
        settings = {'assets': {'preloadBundles': [{'bundle': 'resources'}, {'bundle': 'main'}]},
                    'splashScreen': {'totalTime': 2000}}
        files = pkg3x({'subpackages/resources/big.bin': b'\x00' * (3 * 1024 * 1024)}, self.SUB, settings)
        self.assertEqual(ids(startup, files, 'remake', 'block'), ['G5_3x_presubpackage', 'G6_3x_splash'])
        self.assertEqual(ids(startup, files, None, 'block'), [])
        self.assertIn('G6_3x_splash', ids(startup, files, None, 'warn'))

    def test_g5_g6_loading_page_takeover_passes(self):
        settings = {'assets': {'preloadBundles': [{'bundle': 'resources'}]}, 'splashScreen': {'totalTime': 2000}}
        boot = (b"s.overrideSettings('assets', 'preloadBundles', []);"
                b"s.overrideSettings('splashScreen', 'totalTime', 0);")
        files = pkg3x({'subpackages/resources/big.bin': b'\x00' * (3 * 1024 * 1024), 'boot-loading.js': boot},
                      self.SUB, settings)
        self.assertEqual(ids(startup, files, 'remake', 'block'), [])

    V81 = ("module.exports=function(cc,api){var downloader=cc.assetManager.downloader;downloader.maxRetryCount=0;"
           "['.png'].forEach(function(ext){var original=downloader._downloaders[ext];downloader.register(ext,"
           "function(url,o,complete){var done=false,idle=0,budget=ext==='.ttf'?3000:8000;function finish(e,v){"
           "if(done){return;}done=true;complete(e,v);}function frame(){if(idle>=budget){finish(new Error('x'));return;}"
           "requestAnimationFrame(frame);}original(url,o,finish);});});};")
    V82 = ("module.exports=function(cc,api){function bounded(l,original,r,policy){return function(url,o,complete){"
           "var attempts=0;function attempt(){++attempts;original.call(r,url,o,complete);}"
           "if(policy.parallelAfter&&attempts===1)attempt();};}var downloader=cc.assetManager.downloader;"
           "downloader.maxRetryCount=0;var FILE={attempts:2,parallelAfter:10000,giveUp:30000};"
           "downloader.register('.png',bounded('file',downloader._downloaders['.png'],downloader,FILE));"
           "downloader.register('bundle',bounded('bundle',downloader._downloaders.bundle,downloader,"
           "{attempts:1,parallelAfter:0,giveUp:12000}));};")

    def test_g7_short_fatal_guard_warns(self):
        files = pkg24({'native-load-guard.js': self.V81.encode()})
        self.assertEqual(ids(startup, files, level='block'), [])
        self.assertEqual(ids(startup, files, level='warn'), ['G7_file_load_guard'])

    def test_g7_retrying_long_guard_passes(self):
        files = pkg24({'native-load-guard.js': self.V82.encode()})
        self.assertEqual(ids(startup, files, level='block'), [])

    # G9 (Finger Mahjong v57, 10-30). V57 is the shape of its startupMonitor: document.hidden clock, DOM Retry.
    V57 = ("var idle=0,last=Date.now(),wasHidden=document.hidden;setInterval(function(){var now=Date.now();"
           "if(!wasHidden&&!document.hidden)idle+=now-last;last=now;wasHidden=document.hidden;if(idle>=1e4)fail()},500);"
           "function fail(){var p=document.createElement('div'),b=document.createElement('button');b.textContent='Retry';"
           "p.appendChild(b);document.body.appendChild(p)}")
    V58 = ("var idle=0,last=Date.now(),appHidden=false;cc.game.on(cc.game.EVENT_HIDE,function(){appHidden=true});"
           "setInterval(function(){var now=Date.now();if(!appHidden&&!document.hidden)idle+=Math.min(1e3,Math.max(0,now-last));"
           "last=now},500);function fail(){if(tt.showModal)return tt.showModal({confirmText:'Retry'});var p=document.createElement('div');"
           "p.textContent='Retry';document.body.appendChild(p)}")

    def test_g9_v57_blocks_and_v58_passes(self):
        self.assertEqual(sorted(ids(startup, pkg24({'monitor.js': self.V57.encode()}), level='block')),
                         ['G9_doc_hidden_clock', 'G9_dom_retry'])
        self.assertEqual([i for i in ids(startup, pkg24({'monitor.js': self.V58.encode()})) if i.startswith('G9')], [])

    def test_g9_capped_clock_and_dead_dom_branch_pass(self):
        capped = "var n=Date.now();cc.director.on('u',function(){var e=Date.now(),t=Math.min((e-n)/1e3,1);n=e;document.hidden||go(t)})"
        dead = "if (false) { var r=document.createElement('div');r.textContent='RETRY';document.body.appendChild(r); } else { native(); }"
        files = pkg24({'a.js': capped.encode(), 'b.js': dead.encode()})
        self.assertEqual([i for i in ids(startup, files) if i.startswith('G9')], [])

    def test_w8_prehome_bytes(self):
        big = pkg24({'subpackages/resources/big.bin': b'\x00' * 16000000}, self.SUB)
        self.assertEqual(ids(startup, big, level='warn'), ['W8_prehome_bytes'])
        self.assertEqual(ids(startup, big, level='block'), [])
        later = pkg24({'subpackages/levels/big.bin': b'\x00' * 16000000}, [{'name': 'levels', 'root': 'subpackages/levels/'}])
        self.assertEqual(ids(startup, later), [])
        info = startup.pre_home_bytes(gates.PackageView(big))
        self.assertEqual(info['subpackages'], {'subpackages/resources/': 16000000})


PROBE24 = ("module.exports=function(root,ready){var caps=root.cc.sys.capabilities;var image=root.tt.createImage();"
           "image.onload=function(){caps.webp=image.width>0;ready();};image.src=%s;};")
GAME24 = "require('./webp-decode-probe')(root,function(){});"


class WebP(unittest.TestCase):
    ART = {'assets/main/native/a.webp': webp_bytes('lossy')}

    def run24(self, src, extra=None, subs=None):
        files = pkg24(dict(self.ART, **{'webp-decode-probe.js': (PROBE24 % src).encode()}, **(extra or {})),
                      subs, game_js=GAME24)
        view = gates.PackageView(files)
        return [(f['id'], f['level']) for f in webp.check(view)]

    def test_no_webp_no_finding(self):
        self.assertEqual(ids(webp, pkg24()), [])

    def test_no_probe_blocks(self):
        self.assertEqual(ids(webp, pkg24(self.ART), level='block'), ['G4_webp_probe'])

    def test_data_uri_probe_blocks(self):
        self.assertEqual(self.run24("'data:image/webp;base64,UklGRigAAABXRUJQ'"), [('G4_webp_probe', 'block')])

    def test_main_package_file_passes(self):
        self.assertEqual(self.run24("'loading/webp-probe.webp'", {'loading/webp-probe.webp': webp_bytes('lossy')}), [])

    def test_probe_file_in_subpackage_or_missing_blocks(self):
        sub = [{'name': 'res', 'root': 'subpackages/res/'}]
        self.assertEqual(self.run24("'subpackages/res/p.webp'", {'subpackages/res/p.webp': webp_bytes('lossy')}, sub),
                         [('G4_webp_probe', 'block')])
        self.assertEqual(self.run24("'loading/none.webp'"), [('G4_webp_probe', 'block')])

    def test_probe_not_called_by_startup_blocks(self):
        files = pkg24(dict(self.ART, **{'webp-decode-probe.js': (PROBE24 % "'p.webp'").encode(),
                                        'p.webp': webp_bytes('lossy')}))
        self.assertEqual(ids(webp, files, level='block'), ['G4_webp_probe'])

    def test_forced_true_blocks(self):
        files = pkg24(dict(self.ART, **{'webp-decode-probe.js': (PROBE24 % "'p.webp'").encode(),
                                        'p.webp': webp_bytes('lossy')}), game_js=GAME24,
                      index_js=MISSIONS + 'cc.sys.capabilities.webp=true;')
        self.assertEqual(ids(webp, files, level='block'), ['G4_webp_probe'])

    PROBE3 = ("var SAMPLE_FILE=%s;exports.check=function(cc,sdk,t,done){var img=sdk.createImage();img.src=SAMPLE_FILE;};"
              "exports.apply=function(cc,ok){var o=cc.sys.hasFeature;cc.sys.hasFeature=function(f){"
              "if(f===cc.sys.Feature.WEBP&&ok)return true;return o.call(this,f);};};")

    def run3(self, sample_kind, art_kind='lossless', extra_probe=''):
        files = pkg3x({'assets/main/native/a.webp': webp_bytes(art_kind),
                       'webp-check.webp': webp_bytes(sample_kind),
                       'webp-probe.js': ((self.PROBE3 % "'webp-check.webp'") + extra_probe).encode(),
                       'boot-loading.js': b"var webp=require('./webp-probe');"})
        return [(f['id'], f['level']) for f in webp.check(gates.PackageView(files))]

    def test_3x_lossless_sample_passes(self):
        self.assertEqual(self.run3('lossless'), [])

    def test_3x_no_boot_probe_warns_only(self):
        files = pkg3x({'assets/main/native/a.webp': webp_bytes('lossless')})
        self.assertEqual(ids(webp, files, level='block'), [])
        self.assertEqual(ids(webp, files, level='warn'), ['G4_webp_probe'])

    def test_3x_lossy_sample_for_lossless_art_blocks(self):
        self.assertEqual(self.run3('lossy'), [('G4_webp_probe', 'block')])

    def test_3x_data_uri_fallback_warns(self):
        self.assertEqual(self.run3('lossless', extra_probe="var SAMPLE='data:image/webp;base64,UklGRigAAABXRUJQ';"),
                         [('G4_webp_probe', 'warn')])

    def test_3x_unconditional_true_blocks(self):
        files = pkg3x({'assets/main/native/a.webp': webp_bytes('lossless'),
                       'webp-probe.js': b"var s='webp-check.webp';sdk.createImage();cc.sys.hasFeature=function(f){return true};",
                       'webp-check.webp': webp_bytes('lossless'), 'boot-loading.js': b"require('./webp-probe');"})
        self.assertEqual(ids(webp, files, level='block'), ['G4_webp_probe'])

    def test_webp_kind(self):
        self.assertEqual(webp.webp_kind(webp_bytes('lossless')), 'lossless')
        self.assertEqual(webp.webp_kind(webp_bytes('lossy')), 'lossy')
        vp8x = b'VP8X' + struct.pack('<I', 10) + b'\x10' + b'\x00' * 9
        alph = b'ALPH' + struct.pack('<I', 1) + b'\x00\x00'
        body = vp8x + alph + b'VP8 ' + struct.pack('<I', 2) + b'\x00\x00'
        self.assertEqual(webp.webp_kind(b'RIFF' + struct.pack('<I', 4 + len(body)) + b'WEBP' + body), 'lossy')


def bundle(*modules):
    parts = ['window.__require=function(){}({']
    for name, body in modules:
        parts.append('%s:[function(t,e,i){"use strict";cc._RF.push(e,"uuid%s","%s");%s;cc._RF.pop()},{}],'
                     % (name, name, name, body))
    parts.append('},{},[])')
    return ''.join(parts)


KIT = ('function RewardedService(){}RewardedService.prototype.request=function(){var sdk=this.getSDK('
       '"createRewardedVideoAd");s.ad=sdk.createRewardedVideoAd({adUnitId:u});};'
       'RewardedService.prototype.onHide=function(){this.hidden=!0;this.session&&this.session.ad.destroy()}')
PLATFORM_OWN = ('e.show=function(n){var r=tt;var a={done:!1};this.pending=a;a.finish=function(t){a.ad&&a.ad.destroy()};'
                'a.ad=r.createRewardedVideoAd({adUnitId:o});},e.cancel=function(){this.pending&&this.pending.finish("cancel")},'
                'e.appHide=function(){this.pending&&(this.pending.hiddenAt=Date.now())}')


class Ads(unittest.TestCase):
    def test_kit_module_passes(self):
        files = pkg24(index_js=MISSIONS + bundle(('RewardedService', KIT), ('App', 'cc.game.on(cc.game.EVENT_HIDE,'
                                                                              'function(){t.svc.onHide()},this)')))
        self.assertEqual(ids(ads_static, files, 'remake'), [])

    def test_own_module_blocks_new_warns_legacy_on_every_board(self):
        # v7.7: A1 blocks a new game and warns a game on the frozen legacy list (v7.5: warning everywhere)
        files = pkg24(index_js=MISSIONS + bundle(('Platform', PLATFORM_OWN)))
        for board in ('remake', None):
            self.assertEqual(ids(ads_static, files, board, 'block', 'new'), ['A1_rewarded_outside_kit'])
            self.assertEqual(ids(ads_static, files, board, 'block', 'legacy'), [])
            self.assertEqual(ids(ads_static, files, board, 'warn', 'legacy'), ['A1_rewarded_outside_kit'])
        self.assertEqual(ids(ads_static, files, 'remake', 'block'), ['A1_rewarded_outside_kit'])   # not listed: new

    def test_a1_level_follows_policy(self):
        files = pkg24(index_js=MISSIONS + bundle(('Platform', PLATFORM_OWN)))
        saved = dict(ads_static.A1_LEVELS)
        try:
            ads_static.A1_LEVELS['legacy'] = 'block'
            self.assertEqual(ids(ads_static, files, 'remake', 'block', 'legacy'), ['A1_rewarded_outside_kit'])
        finally:
            ads_static.A1_LEVELS.clear()
            ads_static.A1_LEVELS.update(saved)

    def test_fake_kit_name_and_call_form_detected(self):
        fake = 'var r=c("createRewardedVideoAd");f=r.createRewardedVideoAd({adUnitId:s})'
        files = pkg24(index_js=MISSIONS + bundle(('RewardedService', fake)))
        self.assertEqual(ids(ads_static, files, 'remake', 'warn', 'legacy'), ['A1_rewarded_outside_kit'])
        self.assertEqual(ids(ads_static, files, 'remake', 'block', 'new'), ['A1_rewarded_outside_kit'])
        call = 'record.ad=sdk.createRewardedVideoAd.call(sdk,{adUnitId:u})'
        files = pkg24(index_js=MISSIONS + bundle(('MeadowPlatform', call)))
        self.assertEqual(ids(ads_static, files, 'remake', 'warn', 'legacy'), ['A1_rewarded_outside_kit'])
        self.assertEqual(ids(ads_static, files, 'remake', 'block', 'new'), ['A1_rewarded_outside_kit'])

    def test_hide_cancels_ad_blocks(self):
        app = 'cc.game.on(cc.game.EVENT_HIDE,function(){t.drag=null,t.g.save(),t.platform.cancel()},this)'
        files = pkg24(index_js=MISSIONS + bundle(('Platform', PLATFORM_OWN), ('App', app)))
        self.assertIn('A2_hide_kills_ad', ids(ads_static, files, 'remake', 'block'))

    def test_hide_pauses_ad_timer_passes(self):
        app = 'cc.game.on(cc.game.EVENT_HIDE,function(){t.drag=null,t.g.save(),t.platform.appHide()},this)'
        files = pkg24(index_js=MISSIONS + bundle(('Platform', PLATFORM_OWN), ('App', app)))
        self.assertNotIn('A2_hide_kills_ad', ids(ads_static, files, 'remake'))

    def test_hide_destroying_a_node_is_not_an_ad(self):
        main = (PLATFORM_OWN + ',onLoad:function(){cc.game.on(cc.game.EVENT_HIDE,this.hide,this)},'
                'hide:function(){this.hidden=!0,this.clearAim()},clearAim:function(){this.aim&&this.aim.destroy()}')
        files = pkg24(index_js=MISSIONS + bundle(('MainSc', main)))
        self.assertNotIn('A2_hide_kills_ad', ids(ads_static, files, 'remake'))


class Runner(unittest.TestCase):
    def test_modules_load_through_run_without_gate_errors(self):
        result = gates.run(pkg24(), None, 'remake')
        for name in ('mission', 'startup', 'webp', 'ads_static'):
            self.assertIn(name, result['gates'])
        self.assertFalse([b for b in result['blocks'] if b['id'].startswith('GATE_')])


if __name__ == '__main__':
    unittest.main(verbosity=1)

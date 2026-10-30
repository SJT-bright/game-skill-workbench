"""Synthetic bad/good fixtures for the v7.5 W1a gates: package_gates.network (H12/H13/H14), the collect-all
package_gates.run, and package_gates.adapter_fix (writers rewrite old adapter forms, check() only warns).
No game ZIP needed. Run: python3 -B test_package_gates_network.py"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_gates as gates  # noqa: E402
from package_gates import adapter_fix, network  # noqa: E402

MISSIONS = 'tt.addShortcut();tt.getShortcutMissionReward();tt.startEntranceMission();' \
           'tt.getEntranceMissionReward();x.canReceiveReward;tt.login({});'
OWN_APPID = 'tt0011223344556677'
FOREIGN_APPID = 'tt8899aabbccddeeff'


def pkg(index_js='', subpackages=None, extra=None):
    files = {
        'game.json': json.dumps({'subpackages': subpackages or []}).encode(),
        'project.config.json': json.dumps({'appid': OWN_APPID}).encode(),
        'cocos/cocos2d-js-min.js': b'/* engine */ var cc={};',
        'adapter-min.js': b'/* adapter */',
        'game.js': b'',
        'main.js': b'',
        'assets/main/index.js': (MISSIONS + index_js).encode(),
    }
    files.update(extra or {})
    return files


def ids(module, files, board=None, level=None):
    view = gates.PackageView(files, None, board)
    return sorted({f['id'] for f in module.check(view) if level is None or f['level'] == level})


class BundleNames(unittest.TestCase):
    def test_unknown_subpackage_blocks(self):
        files = pkg("tt.loadSubpackage({name:'general',success:f})")
        self.assertEqual(ids(network, files, level='block'), ['H12_bundle_name'])

    def test_declared_builtin_or_shipped_bundle_passes(self):
        sub = [{'name': 'general', 'root': 'subpackages/general/'}]
        js = "tt.loadSubpackage({name:'general'});cc.assetManager.loadBundle('resources',f);" \
             "cc.assetManager.loadBundle('levels',f)"
        files = pkg(js, subpackages=sub, extra={'assets/levels/config.json': b'{}'})
        self.assertEqual(ids(network, files), [])

    def test_adapter_and_engine_files_are_not_scanned(self):
        extra = {'adapter-min.js': b"tt.loadSubpackage({name:'ghost'});var u='https://pas.qq.com/r';"
                                   b"tt.navigateToMiniProgram({})",
                 'cocos/cocos2d-js-min.js': b"tt.loadSubpackage({name:'ghost2'});tt.showMoreGamesModal({})"}
        self.assertEqual(ids(network, pkg('', extra=extra)), [])


class Analytics(unittest.TestCase):
    def test_cn_analytics_hosts_block(self):
        for host in ('pas.qq.com', 'mta.qq.com', 'hm.baidu.com', 'sdk.umeng.com'):
            files = pkg('var u="https://%s/report";' % host)
            self.assertEqual(ids(network, files, level='block'), ['H13_analytics_domain'], host)

    def test_documentation_link_and_lookalike_host_pass(self):
        files = pkg('var d="https://doc.aldwx.com/api";var e="https://notpas.qq.community/";')
        self.assertEqual(ids(network, files), [])


class CrossPromo(unittest.TestCase):
    def test_jump_calls_and_foreign_app_id_block(self):
        for js in ('tt.navigateToMiniProgram({appId:a})', 'tt.showMoreGamesModal({})',
                   'var list=["%s"]' % FOREIGN_APPID):
            self.assertEqual(ids(network, pkg(js), level='block'), ['H14_cross_promo'], js)

    def test_own_app_id_and_emptied_component_pass(self):
        js = 'var me="%s";cc.Class({properties:{moreGamesBtn:cc.Node,promoList:[]},onLoad:function(){}})' % OWN_APPID
        self.assertEqual(ids(network, pkg(js)), [])


class CollectAll(unittest.TestCase):
    def test_run_lists_every_network_reason_together(self):
        js = "tt.loadSubpackage({name:'general'});var u='https://pas.qq.com/r';tt.navigateToMiniProgram({})"
        found = {f['id'] for f in gates.run(pkg(js), None, 'localize')['blocks']}
        self.assertTrue({'H12_bundle_name', 'H13_analytics_domain', 'H14_cross_promo'} <= found, found)


ENGINE_24 = b'/* engine */ cc.ENGINE_VERSION="2.4.15";'
SDK_OLD = 'if(Number.parseInt(t.SDKVersion[0])<2){x()}'
SUB_OLD = 'r.isSubContext=void 0===tt.getOpenDataContext;'
FS_OLD = 'function N(t,e,n){c(t,function(e){e?n(null,t):n(new Error("file ".concat(t," does not exist!")))})}'
ALL_OLD = SDK_OLD + SUB_OLD + FS_OLD


def native24(adapter, engine=ENGINE_24):
    return {'game.js': b'require("adapter-min.js");', 'game.json': b'{}', 'project.config.json': b'{}',
            'cocos/cocos2d-js-min.js': engine, 'adapter-min.js': ('tt.getSystemInfoSync();' + adapter).encode()}


def write(folder, files):
    for name, data in files.items():
        path = Path(folder) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def read(folder):
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in Path(folder).rglob('*') if p.is_file()}


class AdapterFix(unittest.TestCase):
    def test_detect_old_forms(self):
        self.assertEqual(adapter_fix.detect(native24(ALL_OLD))['rules'],
                         {'sdk_version': 'old', 'sub_context': 'old', 'pkg_fs_access': 'old'})

    def test_apply_rewrites_each_old_form_once_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, native24(ALL_OLD))
            first = adapter_fix.apply(d)
            self.assertEqual(first['blocks'], [])
            self.assertEqual(sorted(c['rule'] for c in first['changed']), ['pkg_fs_access', 'sdk_version', 'sub_context'])
            text = (Path(d) / 'adapter-min.js').read_text()
            self.assertIn('SDKVersion.split(".")[0]', text)
            self.assertNotIn('SDKVersion[0]', text)
            self.assertEqual(adapter_fix.detect(read(d))['rules'], {r: 'fixed' for r in adapter_fix.RULES})
            second = adapter_fix.apply(d)
            self.assertEqual((second['changed'], second['blocks']), ([], []))
            self.assertEqual((Path(d) / 'adapter-min.js').read_text(), text)

    def test_unrecognised_form_blocks_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, native24(SUB_OLD + FS_OLD))          # no SDKVersion check in any known form
            before = (Path(d) / 'adapter-min.js').read_bytes()
            out = adapter_fix.apply(d)
            self.assertEqual([f['id'] for f in out['blocks']], ['ADAPTER_FIX_sdk_version'])
            self.assertEqual(out['changed'], [])
            self.assertEqual((Path(d) / 'adapter-min.js').read_bytes(), before)

    def test_old_form_twice_is_ambiguous_and_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, native24(SDK_OLD + SDK_OLD + SUB_OLD + FS_OLD))
            out = adapter_fix.apply(d)
            self.assertEqual([f['id'] for f in out['blocks']], ['ADAPTER_FIX_sdk_version'])
            self.assertEqual(out['changed'], [])

    def test_other_engine_versions_are_left_alone(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, native24(ALL_OLD, engine=b'cc.ENGINE_VERSION="2.3.4";'))
            out = adapter_fix.apply(d)
            self.assertEqual((out['target'], out['changed'], out['blocks']), ([], [], []))

    def test_read_only_check_only_warns(self):
        found = adapter_fix.check(gates.PackageView(native24(ALL_OLD), None, 'remake'))
        self.assertEqual(sorted(f['id'] for f in found),
                         ['W_adapter_pkg_fs_access', 'W_adapter_sdk_version', 'W_adapter_sub_context'])
        self.assertEqual({f['level'] for f in found}, {'warn'})


if __name__ == '__main__':
    unittest.main()

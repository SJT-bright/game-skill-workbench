"""Calibrate the Cocos 2.4 startup dependency on the builtin resources bundle."""
import json
import unittest

from audit_upload_startup import audit_files


STARTUP = b"""
window.boot = function () {
  function start() {
    var loadResources = guarded('resources', function () {
      loadBundle(cc.AssetManager.BuiltinBundleName.RESOURCES, loadEngine);
    });
    var loadSubpackage = guarded('resources subpackage', function () {
      SKIP_ABSENT
      loadResources();
    });
    loadSubpackage();
  }
  start();
};
"""
SKIP_ABSENT = b'if (settings.hasResourcesBundle === false) { loadEngine(); return; }'
MAIN_ENTRY = 'assets/resources/index.js'
SUB_CONFIG = 'subpackages/resources/config.abcde.json'


def fixture(*, declared=False, fixed=True, subpackage=False, registered=True):
    settings = {'hasResourcesBundle': declared, 'subpackages': ['resources' if subpackage else 'MainScene'],
                'bundleVers': {'resources': 'abcde'} if declared else {}}
    name = settings['subpackages'][0]
    root = 'subpackages/' + name
    files = {
        'game.js': b"require('./adapter-min');require('./src/settings');require('./ccRequire');require('./main');window.boot();",
        'game.json': json.dumps({'subpackages': [{'name': name, 'root': root}]}).encode(),
        'project.config.json': b'{}',
        'adapter-min.js': b"function load(name) { return __cocos_require__('assets/' + name + '/index.js') || 'subpackages/' + name; }",
        'src/settings.js': b'window._CCSettings = ' + json.dumps(settings).encode() + b';',
        'main.js': STARTUP.replace(b'SKIP_ABSENT', SKIP_ABSENT if fixed else b''),
        'ccRequire.js': b'var moduleMap = {};',
        root + '/game.js': b'// subpackage entry',
    }
    if subpackage and declared:
        files[SUB_CONFIG] = b'{}'
    if declared and not subpackage:
        files[MAIN_ENTRY] = b'// scriptless bundle'
        files['assets/resources/config.abcde.json'] = b'{}'
        if registered:
            files['ccRequire.js'] = b"var moduleMap = {'assets/resources/index.js'() { return require('assets/resources/index.js'); }};"
    return files


class StartupResourcesTests(unittest.TestCase):
    def test_legacy_kit_rejects_absent_resources(self):
        report = audit_files(fixture(fixed=False))
        self.assertFalse(report['passed'])
        self.assertIn('despite hasResourcesBundle=false', '\n'.join(report['errors']))

    def test_fixed_kit_accepts_custom_subpackage_without_resources(self):
        self.assertTrue(audit_files(fixture())['passed'])

    def test_stock_startup_accepts_absent_resources(self):
        files = fixture()
        files['main.js'] = b'window.boot = function () { if (settings.hasResourcesBundle) loadBundle(RESOURCES); };'
        self.assertTrue(audit_files(files)['passed'])

    def test_contradictory_engine_settings_are_rejected(self):
        report = audit_files(fixture(subpackage=True))
        self.assertFalse(report['passed'])
        self.assertIn('hasResourcesBundle=false conflicts', '\n'.join(report['errors']))

    def test_subpackage_accepts_versioned_config_and_rejects_wrong_version(self):
        files = fixture(declared=True, subpackage=True)
        self.assertTrue(audit_files(files)['passed'])
        files['subpackages/resources/config.json'] = files.pop(SUB_CONFIG)
        report = audit_files(files)
        self.assertFalse(report['passed'])
        self.assertIn(SUB_CONFIG, '\n'.join(report['errors']))

    def test_renamed_startup_and_custom_subpackage_still_block(self):
        files = fixture(fixed=False)
        files['game.js'] = files['game.js'].replace(b'./main', b'./boot/entry')
        files['boot/entry.js'] = files.pop('main.js')
        files['game.json'] = files['game.json'].replace(b'MainScene', b'Gameplay')
        files['src/settings.js'] = files['src/settings.js'].replace(b'MainScene', b'Gameplay')
        files['subpackages/Gameplay/game.js'] = files.pop('subpackages/MainScene/game.js')
        report = audit_files(files)
        self.assertFalse(report['passed'])
        self.assertIn('boot/entry.js loads assets/resources/index.js', '\n'.join(report['errors']))

    def test_direct_load_in_renamed_nested_entry_blocks(self):
        files = fixture()
        files['game.js'] = files['game.js'].replace(b'./main', b'./boot/start')
        files['boot/start.js'] = b"require('./launch');"
        files['boot/launch.js'] = b"window.boot = () => cc.assetManager.loadBundle('resources', ready);"
        files.pop('main.js')
        report = audit_files(files)
        self.assertFalse(report['passed'])
        self.assertIn('boot/launch.js loads assets/resources/index.js', '\n'.join(report['errors']))

    def test_direct_builtin_enum_in_game_entry_blocks(self):
        files = fixture()
        files['game.js'] += b'cc.assetManager.loadBundle(cc.AssetManager.BuiltinBundleName.RESOURCES, ready);'
        self.assertFalse(audit_files(files)['passed'])

    def test_guarded_or_uninvoked_direct_load_is_not_inferred(self):
        direct = b"cc.assetManager.loadBundle('resources', ready);"
        cases = {
            'condition': (b'window.boot = () => { if (settings.hasResourcesBundle) ' + direct + b'};', True),
            'early return': (b'window.boot = () => { if (!settings.hasResourcesBundle) return; ' + direct + b'};', True),
            'dormant callback': (b'window.boot = () => { function later() { ' + direct + b'} };', True),
            'not invoked': (b'window.boot = () => { ' + direct + b'};', False),
        }
        for label, (source, invokes) in cases.items():
            with self.subTest(label=label):
                files = fixture()
                files['main.js'] = source
                if not invokes:
                    files['game.js'] = files['game.js'].replace(b'window.boot();', b'')
                self.assertTrue(audit_files(files)['passed'])

    def test_delayed_subpackage_request_is_not_inferred_at_startup(self):
        files = fixture()
        files['subpackages/MainScene/game.js'] = b"cc.assetManager.loadBundle('resources', ready);"
        self.assertTrue(audit_files(files)['passed'])

    def test_declared_bundle_checks_missing_entry_without_main_js(self):
        files = fixture(declared=True)
        files['game.js'] = files['game.js'].replace(b'./main', b'./custom-entry')
        files['custom-entry.js'] = files.pop('main.js')
        files.pop(MAIN_ENTRY)
        self.assertIn('Cocos2 resources: missing startup dependency: ' + MAIN_ENTRY, audit_files(files)['errors'])

    def test_main_bundle_checks_entry_and_module_registration(self):
        files = fixture(declared=True)
        files['src/settings.js'] = files['src/settings.js'].replace(b': true', b': !\t0')
        self.assertTrue(audit_files(files)['passed'])
        report = audit_files(fixture(declared=True, registered=False))
        self.assertIn('ccRequire.js does not register ' + MAIN_ENTRY, report['errors'][0])
        files.pop(MAIN_ENTRY)
        report = audit_files(files)
        self.assertFalse(report['passed'])
        self.assertIn('Cocos2 resources: missing startup dependency: ' + MAIN_ENTRY, report['errors'])


if __name__ == '__main__':
    unittest.main()

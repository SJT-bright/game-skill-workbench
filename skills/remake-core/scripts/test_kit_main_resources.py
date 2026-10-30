"""v7.7 W-G2: the static resource manifest reads the platform-kit main.js.

Only main.js bytes equal to a KIT_MANIFEST.json hash (current or previous_sha256, read at run time) get their
cc.assetManager.loadScript(settings.jsList) call expanded into required script files (plus webp-decode-probe.js,
which the kit main.js requires). Every other main.js and every other loader call stays unsupported."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_runtime_resources as resources

KIT = resources.HERE.parent / 'assets' / 'platform-kit'
KIT_MAIN = (KIT / 'build-templates' / 'bytedance' / 'main.js').read_bytes()
EDITOR_MAIN_2415 = Path('/Applications/Cocos/Creator/2.4.15/CocosCreator.app/Contents/Resources/static/'
                        'build-templates/shares/main.js')
# The 2.4 editor template's own line (Creator 2.4.15 build-templates/shares/main.js line 116).
EDITOR_MAIN = (b"window.boot = function () {\n    var settings = window._CCSettings;\n    window._CCSettings = undefined;\n"
               b"    var cb = function () {};\n"
               b"    cc.assetManager.loadScript(settings.jsList.map(function (x) { return 'src/' + x;}), cb);\n};\n")
SETTINGS = (b'window._CCSettings = {\n    platform: "bytedance",\n    subpackages: [],\n'
            b'    launchScene: "db://assets/start.fire",\n    jsList: ["assets/plugin-a.js", "plugin-b.js"]\n};\n')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def package(main=KIT_MAIN, settings=SETTINGS):
    """A finalized 2.4 package as the scan sees it: the kit main.js and parts, settings with two jsList plugins,
    and one business bundle with one literal request."""
    files = {
        'game.js': b"require('./adapter');\nrequire('./src/settings');\nrequire('./main');\nwindow.boot();\n",
        'main.js': main,
        'src/settings.js': settings,
        'src/assets/plugin-a.js': b'window.pluginA = 1;\n',
        'src/plugin-b.js': b'window.pluginB = 1;\n',
        'touch-coordinates.js': (KIT / 'build-templates/bytedance/touch-coordinates.js').read_bytes(),
        'storage-guard.js': (KIT / 'parts/storage-guard.js').read_bytes(),
        'webp-decode-probe.js': (KIT / 'webp-probe/cocos2.4/webp-decode-probe.js').read_bytes(),
        'assets/main/config.json': json.dumps({'name': 'main', 'types': ['cc.SpriteFrame'],
                                               'paths': {'0': ['icons/a', 0], '1': ['icons/b', 0]}}).encode(),
        'assets/main/index.js': b"cc.assetManager.getBundle('main').load('icons/a', cc.SpriteFrame, function () {});\n",
    }
    return files


def manifest_for(main):
    """KIT_MANIFEST.json as in the tree, with `main` as the current kit main.js (the old current moves to
    previous_sha256). W-G1 edits main.js in parallel, so the template bytes and the manifest can briefly differ."""
    manifest = json.loads((KIT / 'KIT_MANIFEST.json').read_bytes())
    for spec in (manifest['files']['build-templates/bytedance/main.js'], manifest['parts']['startup24']['file']):
        if spec['sha256'] != sha(main):
            spec['previous_sha256'] = [spec['sha256']] + [h for h in spec['previous_sha256'] if h != sha(main)]
            spec['sha256'] = sha(main)
    return manifest


class KitMainScripts(unittest.TestCase):
    def setUp(self):
        resources._CACHE.clear()
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name) / 'KIT_MANIFEST.json'
        path.write_text(json.dumps(manifest_for(KIT_MAIN)))
        self.kit_manifest = patch.object(resources, 'KIT_MANIFEST', path, create=True)
        self.kit_manifest.start()

    def tearDown(self):
        self.kit_manifest.stop()
        self.tmp.cleanup()
        resources._CACHE.clear()

    def test_tree_manifest_names_the_tree_main_js(self):
        self.kit_manifest.stop()
        try:
            identity = resources.kit_main_identity()
            self.assertIn('webp-decode-probe.js', identity['extra_files'])
            if sha(KIT_MAIN) not in identity['hashes']:
                self.skipTest('kit main.js template and KIT_MANIFEST differ right now (main.js being edited)')
            resources._CACHE.clear()
            self.assertEqual(len(resources.generate(package())['script_files']), 3)
        finally:
            self.kit_manifest.start()

    def test_kit_main_gives_static_manifest_with_jslist_scripts(self):
        files = package()
        manifest = resources.generate(files)
        self.assertEqual(manifest['resources'], [{'bundle': 'main', 'path': 'icons/a', 'type': 'cc.SpriteFrame'}])
        listed = {r['path']: r['sha256'] for r in manifest['script_files']}
        self.assertEqual(listed, {p: sha(files[p]) for p in ('src/assets/plugin-a.js', 'src/plugin-b.js', 'webp-decode-probe.js')})
        result = resources.audit(files, manifest)
        self.assertTrue(result['passed'])
        self.assertEqual(len(result['kit_script_files']), 3)
        self.assertNotIn('main.js', {s['source'] for s in result['resource_call_sites']})

    def test_empty_jslist_still_requires_the_probe(self):
        files = package(settings=SETTINGS.replace(b'["assets/plugin-a.js", "plugin-b.js"]', b'[]'))
        manifest = resources.generate(files)
        self.assertEqual([r['path'] for r in manifest['script_files']], ['webp-decode-probe.js'])
        no_list = package(settings=SETTINGS.replace(b',\n    jsList: ["assets/plugin-a.js", "plugin-b.js"]', b''))
        resources._CACHE.clear()
        self.assertEqual([r['path'] for r in resources.generate(no_list)['script_files']], ['webp-decode-probe.js'])

    def test_deleted_or_empty_script_is_refused(self):
        for name in ('src/assets/plugin-a.js', 'src/plugin-b.js', 'webp-decode-probe.js'):
            with self.subTest(name=name):
                files = package(); del files[name]
                with self.assertRaisesRegex(ValueError, 'kit main.js script file missing or empty: ' + name):
                    resources.generate(files)
                files = package(); files[name] = b''
                with self.assertRaisesRegex(ValueError, 'missing or empty: ' + name):
                    resources.generate(files)

    def test_deleted_script_refused_by_audit_of_an_earlier_manifest(self):
        files = package()
        manifest = resources.generate(files)
        del files['src/plugin-b.js']
        with self.assertRaisesRegex(ValueError, 'missing or empty: src/plugin-b.js'):
            resources.audit(files, manifest)

    def test_manifest_must_list_every_script_with_current_bytes(self):
        files = package()
        manifest = resources.generate(files)
        short = copy.deepcopy(manifest); short['script_files'] = short['script_files'][1:]
        with self.assertRaisesRegex(ValueError, 'omitted kit main.js script files'):
            resources.audit(files, short)
        none = copy.deepcopy(manifest); del none['script_files']
        with self.assertRaisesRegex(ValueError, 'omitted kit main.js script files'):
            resources.audit(files, none)
        files['src/plugin-b.js'] = b'window.pluginB = 2;\n'
        with self.assertRaisesRegex(ValueError, 'script file bytes changed: src/plugin-b.js'):
            resources.audit(files, manifest)
        extra = copy.deepcopy(manifest)
        extra['script_files'].append({'path': 'src/other.js', 'sha256': '0' * 64})
        with self.assertRaisesRegex(ValueError, 'unknown or duplicate kit main.js script file'):
            resources.audit(package(), extra)

    def test_same_line_in_other_main_js_stays_unresolved(self):
        changed = KIT_MAIN + b'\n// one byte more than the kit file\n'
        with self.assertRaisesRegex(ValueError, 'unresolved dynamic resource calls.*loadScript'):
            resources.generate(package(main=changed))
        # the kit line copied into a business script is still a loader call there
        files = package()
        files['assets/main/index.js'] += (b"var settings = {jsList: []};\ncc.assetManager.loadScript((settings.jsList || [])"
                                          b".map(function (x) {\n  return 'src/' + x;\n}), function () {});\n")
        with self.assertRaisesRegex(ValueError, 'unresolved dynamic resource calls.*assets/main/index.js'):
            resources.generate(files)

    def test_editor_main_js_behaves_as_before(self):
        mains = [EDITOR_MAIN] + ([EDITOR_MAIN_2415.read_bytes()] if EDITOR_MAIN_2415.is_file() else [])
        for main in mains:
            with self.subTest(size=len(main)):
                resources._CACHE.clear()
                with self.assertRaisesRegex(ValueError, 'unresolved dynamic resource calls.*loadScript') as caught:
                    resources.generate(package(main=main))
                self.assertNotIn('kit main.js', str(caught.exception))

    def test_hashes_are_read_from_kit_manifest_at_run_time(self):
        manifest = manifest_for(KIT_MAIN)
        current = sha(KIT_MAIN)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'KIT_MANIFEST.json'
            with patch.object(resources, 'KIT_MANIFEST', path, create=True):
                # main.js moved to previous_sha256 (W-G1 ships a new main.js): still recognised
                moved = copy.deepcopy(manifest)
                for spec in (moved['files']['build-templates/bytedance/main.js'], moved['parts']['startup24']['file']):
                    spec['previous_sha256'] = [current] + [h for h in spec['previous_sha256'] if h != current]
                    spec['sha256'] = 'f' * 64
                path.write_text(json.dumps(moved))
                resources._CACHE.clear()
                self.assertEqual(len(resources.generate(package())['script_files']), 3)
                # hash no longer listed anywhere: the call is unsupported again
                gone = copy.deepcopy(moved)
                for spec in (gone['files']['build-templates/bytedance/main.js'], gone['parts']['startup24']['file']):
                    spec['previous_sha256'] = [h for h in spec['previous_sha256'] if h != current]
                path.write_text(json.dumps(gone))
                with self.assertRaisesRegex(ValueError, 'unresolved dynamic resource calls'):
                    resources.generate(package())
                # unreadable manifest recognises nothing
                path.write_text('{')
                with self.assertRaisesRegex(ValueError, 'unresolved dynamic resource calls'):
                    resources.generate(package())

    def test_unreadable_or_changed_jslist_is_not_expanded(self):
        cases = {
            'not an array of string literals': SETTINGS.replace(b'"plugin-b.js"', b'pluginName'),
            'expected exactly one top-level': SETTINGS + b'window._CCSettings = {jsList: []};\n',
            'spread or computed key': SETTINGS.replace(b'platform: "bytedance",', b'...base, platform: "bytedance",'),
            'unsafe settings.jsList entry': SETTINGS.replace(b'"plugin-b.js"', b'"../game.js"'),
        }
        for why, settings in cases.items():
            with self.subTest(why=why):
                resources._CACHE.clear()
                with self.assertRaisesRegex(ValueError, 'kit main.js jsList not expanded: .*' + why):
                    resources.generate(package(settings=settings))

    def test_writes_to_jslist_outside_kit_main_keep_the_call_unsupported(self):
        for write in ("window._CCSettings.jsList.push('src/extra.js');",
                      "var s = window._CCSettings; s.jsList = ['x.js'];",
                      "var l = window._CCSettings.jsList; l.push('x.js');",
                      "Object.assign(window._CCSettings, {jsList: ['x.js']});",
                      "window._CCSettings = {jsList: ['x.js']};"):
            with self.subTest(write=write):
                files = package(); files['game.js'] = write.encode() + b'\n' + files['game.js']
                resources._CACHE.clear()
                with self.assertRaisesRegex(ValueError, 'written outside the kit main.js'):
                    resources.generate(files)
        # reading jsList is not a write
        files = package(); files['game.js'] = b"console.log(window._CCSettings.jsList.length);\n" + files['game.js']
        resources._CACHE.clear()
        self.assertEqual(len(resources.generate(files)['script_files']), 3)

    def test_two_settings_scripts_are_not_guessed(self):
        files = package(); files['src/settings.0a1b2.js'] = SETTINGS
        with self.assertRaisesRegex(ValueError, 'expected one src/settings.js'):
            resources.generate(files)

    def test_package_without_kit_main_gets_no_script_rows(self):
        files = package(main=b'window.boot = function () {};\n')
        manifest = resources.generate(files)
        self.assertNotIn('script_files', manifest)
        bad = dict(manifest, script_files=[{'path': 'webp-decode-probe.js', 'sha256': sha(files['webp-decode-probe.js'])}])
        with self.assertRaisesRegex(ValueError, 'unknown or duplicate kit main.js script file'):
            resources.audit(files, bad)


if __name__ == '__main__':
    unittest.main(verbosity=2)

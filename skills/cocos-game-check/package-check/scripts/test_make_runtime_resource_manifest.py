#!/usr/bin/env python3
"""make_runtime_resource_manifest.py: observed host requests -> manifest; a request outside the package refuses."""
import json
from pathlib import Path
import tempfile
import unittest

import make_runtime_resource_manifest as m


class ObservedManifest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='rrm-'))
        self.native = self.tmp / 'pkg'
        for name, data in {'game.js': b'GAME', 'assets/main/config.json': b'{}', 'assets/resources/a.png': b'PNG'}.items():
            (self.native / name).parent.mkdir(parents=True, exist_ok=True)
            (self.native / name).write_bytes(data)

    def log(self, rows, name='host-log.jsonl'):
        path = self.tmp / name
        lines = [json.dumps({'kind': 'http-get', 'data': {'path': p, 'status': s, 'method': 'GET'}}) for p, s in rows]
        lines.insert(1, json.dumps({'t': 5, 'kind': 'net-request', 'data': {'url': 'https://x.example/'}}))
        lines.insert(2, '{"broken beacon')
        path.write_text('\n'.join(lines) + '\n')
        return path

    def test_observed_files_and_exclusions(self):
        log = self.log([('/game.js', 200), ('/assets/main/config.json', 200), ('/assets/resources/a.png', 200),
                        ('/assets/resources/a.png', 200), ('/favicon.ico', 404), ('/ttfile:/user/x.json', 404),
                        ('/__net_blocked', 404)])
        doc = m.build(self.native, [log])
        self.assertEqual(doc['schema'], m.SCHEMA)
        self.assertEqual([r['path'] for r in doc['observed_files']], ['assets/main/config.json', 'assets/resources/a.png', 'game.js'])
        self.assertEqual(doc['observed_files'][1]['requests'], 2)
        self.assertEqual(len(doc['excluded']), 3)
        files = m.package_files(self.native)
        self.assertTrue(m.verify(files, doc)['passed'])
        files['assets/resources/a.png'] = b'OTHER'
        with self.assertRaisesRegex(m.ManifestRefused, 'different package bytes'):
            m.verify(files, doc)

    def test_request_outside_package_refuses(self):
        log = self.log([('/game.js', 200), ('/assets/resources/missing.png', 404)])
        with self.assertRaisesRegex(m.ManifestRefused, 'request not in the package: /assets/resources/missing.png'):
            m.build(self.native, [log])

    def test_package_file_with_error_status_and_parent_paths_refuse(self):
        with self.assertRaisesRegex(m.ManifestRefused, 'status 500'):
            m.build(self.native, [self.log([('/game.js', 200), ('/assets/main/config.json', 500)])])
        with self.assertRaisesRegex(m.ManifestRefused, 'unusable request path'):
            m.build(self.native, [self.log([('/game.js', 200), ('/../secret', 404)])])

    def test_empty_or_foreign_logs_refuse(self):
        with self.assertRaisesRegex(m.ManifestRefused, 'at least one --log'):
            m.build(self.native, [])
        with self.assertRaisesRegex(m.ManifestRefused, 'game.js was never requested'):
            m.build(self.native, [self.log([('/assets/main/config.json', 200)])])

    def test_cli_refuses_output_inside_package_and_writes_once(self):
        log = self.log([('/game.js', 200)])
        self.assertEqual(m.main(['--native', str(self.native), '--log', str(log), '--out', str(self.native / 'm.json')]), 1)
        out = self.tmp / 'm.json'
        self.assertEqual(m.main(['--native', str(self.native), '--log', str(log), '--out', str(out)]), 0)
        self.assertEqual(m.main(['--native', str(self.native), '--log', str(log), '--out', str(out)]), 1)


class AuditAcceptsObserved(unittest.TestCase):
    """audit_runtime_resources.audit() takes the observed manifest (W3a R3) only where static expansion fails."""
    log = ObservedManifest.log

    def setUp(self):
        ObservedManifest.setUp(self)
        import importlib.util
        path = Path(__file__).resolve().parents[3] / 'remake-core/scripts/audit_runtime_resources.py'
        spec = importlib.util.spec_from_file_location('_shared_runtime_resources_test', path)
        self.resources = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.resources)
        log = self.log([('/game.js', 200), ('/assets/resources/a.png', 200)])
        self.doc = m.build(self.native, [log])
        self.files = m.package_files(self.native)

    def unresolved(self, *args, **kwargs):
        raise ValueError('unresolved dynamic resource calls')

    def test_observed_manifest_passes_when_static_expansion_fails(self):
        from unittest.mock import patch
        with patch.object(self.resources, 'required_requests', side_effect=self.unresolved):
            result = self.resources.audit(self.files, self.doc)
        self.assertEqual((result['passed'], result['source']), (True, 'observed'))

    def test_observed_manifest_for_other_bytes_refuses(self):
        from unittest.mock import patch
        self.files['assets/resources/a.png'] = b'OTHER'
        with patch.object(self.resources, 'required_requests', side_effect=self.unresolved):
            with self.assertRaisesRegex(ValueError, 'different package bytes'):
                self.resources.audit(self.files, self.doc)

    def test_observed_manifest_refused_when_static_expansion_works(self):
        from unittest.mock import patch
        with patch.object(self.resources, 'required_requests', return_value=(set(), {}, {})):
            with self.assertRaisesRegex(ValueError, 'expands statically'):
                self.resources.audit(self.files, self.doc)


class KitMainObserved(unittest.TestCase):
    """v7.7 W-G2, real scan (nothing patched in the auditor): the kit main.js alone no longer forces the observed
    manifest. A kit-main package whose business code expands gets the static one; one whose business code builds paths
    at run time still uses the observed one."""
    resources = None

    def setUp(self):
        import hashlib
        import importlib.util
        from unittest.mock import patch
        import sys
        root = Path(__file__).resolve().parents[3] / 'remake-core'
        if str(root / 'scripts') not in sys.path:  # the auditor imports project_qa for profile paths
            sys.path.insert(0, str(root / 'scripts'))
        spec = importlib.util.spec_from_file_location('_shared_runtime_resources_kit', root / 'scripts/audit_runtime_resources.py')
        self.resources = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.resources)
        kit = root / 'assets/platform-kit'
        main = (kit / 'build-templates/bytedance/main.js').read_bytes()
        # KIT_MANIFEST naming the template main.js as current (W-G1 edits main.js in parallel)
        manifest = json.loads((kit / 'KIT_MANIFEST.json').read_bytes())
        current = hashlib.sha256(main).hexdigest()
        for entry in (manifest['files']['build-templates/bytedance/main.js'], manifest['parts']['startup24']['file']):
            if entry['sha256'] != current:
                entry['previous_sha256'] = [entry['sha256']] + entry['previous_sha256']
                entry['sha256'] = current
        self.tmp = Path(tempfile.mkdtemp(prefix='rrm-kit-'))
        (self.tmp / 'KIT_MANIFEST.json').write_text(json.dumps(manifest))
        self.patch = patch.object(self.resources, 'KIT_MANIFEST', self.tmp / 'KIT_MANIFEST.json')
        self.patch.start()
        self.native = self.tmp / 'pkg'
        self.package = {
            'game.js': b"require('./src/settings');\nrequire('./main');\nwindow.boot();\n", 'main.js': main,
            'src/settings.js': b'window._CCSettings = {jsList: []};\n',
            'webp-decode-probe.js': (kit / 'webp-probe/cocos2.4/webp-decode-probe.js').read_bytes(),
            'assets/resources/config.json': json.dumps({'name': 'resources', 'types': ['cc.SpriteFrame'],
                                                        'paths': {'0': ['a', 0]}}).encode(),
            'assets/resources/index.js': b"cc.resources.load('a', cc.SpriteFrame, function () {});\n",
            'assets/resources/a.png': b'PNG'}

    def tearDown(self):
        self.patch.stop()

    def write(self):
        for name, data in self.package.items():
            (self.native / name).parent.mkdir(parents=True, exist_ok=True)
            (self.native / name).write_bytes(data)
        log = ObservedManifest.log(self, [('/' + n, 200) for n in sorted(self.package)])
        return m.build(self.native, [log]), m.package_files(self.native)

    def test_kit_main_with_static_business_code_refuses_observed(self):
        doc, files = self.write()
        static = self.resources.generate(files)
        self.assertEqual([r['path'] for r in static['script_files']], ['webp-decode-probe.js'])
        self.assertTrue(self.resources.audit(files, static)['passed'])
        with self.assertRaisesRegex(ValueError, 'expands statically'):
            self.resources.audit(files, doc)

    def test_kit_main_with_runtime_built_paths_uses_observed(self):
        self.package['assets/resources/index.js'] = b"cc.resources.load('a' + level, cc.SpriteFrame, function () {});\n"
        doc, files = self.write()
        with self.assertRaisesRegex(ValueError, 'unresolved dynamic resource calls') as caught:
            self.resources.generate(files)
        self.assertNotIn('main.js:', str(caught.exception))  # only the business call is unresolved
        result = self.resources.audit(files, doc)
        self.assertEqual((result['passed'], result['source']), (True, 'observed'))


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Only spelling is waived for runtime labels listed by their exact path and reason."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_copy_quality as audit  # noqa: E402


class DynamicRuntimeCopyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='copy-dynamic-label-'))
        self.project = self.tmp / 'game'
        (self.project / 'assets').mkdir(parents=True)
        (self.project / 'docs/text').mkdir(parents=True)
        self.dump = self.tmp / '000-ui-dump-league.json'

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def check(self, path, text, patterns):
        (self.project / 'docs/text/runtime-text.json').write_text(json.dumps({
            'labels': [{'path': pattern, 'why': 'Procedurally generated league rival name.'} for pattern in patterns]
        }))
        node = {'path': path, 'name': 'Dynamic label', 'opacity': 1,
                'rect': [0.1, 0.3, 0.6, 0.06],
                'comps': {'label': {'string': text, 'fontSize': 40, 'width': 300, 'height': 64,
                                    'overflow': 3, 'actualFontSize': 40}}}
        self.dump.write_text(json.dumps({'tool': 'ui_dump', 'schema': 1, 'screen': 'league',
                                         'canvas_css': [0, 0, 393, 852], 'page': {'dpr': 3}, 'nodes': [node]}))
        return audit.audit(self.project, [self.dump], None, None)

    def test_approved_dynamic_path_skips_only_spelling(self):
        result = self.check('Canvas/GameRoot/League rival name 0', 'ZippyKitty82',
                            ['*League rival name *'])
        self.assertNotIn('spelling', {x['kind'] for x in result['blocking']})
        self.assertEqual(result['runtime'], 1)

    def test_non_allowlisted_fixed_text_still_blocks(self):
        result = self.check('Canvas/GameRoot/Fixed league title', 'ZippyKitty82',
                            ['*League rival name *'])
        self.assertIn('spelling', {x['kind'] for x in result['blocking']})

    def test_other_copy_rules_still_apply_to_dynamic_labels(self):
        result = self.check('Canvas/GameRoot/League rival name 0', 'ZippyKitty82 ZippyKitty82',
                            ['*League rival name *'])
        self.assertIn('repeated_word', {x['kind'] for x in result['blocking']})
        self.assertNotIn('spelling', {x['kind'] for x in result['blocking']})


if __name__ == '__main__':
    unittest.main()

"""A legacy filename must not grant a capture a build identity."""
import json
from pathlib import Path
import tempfile
import unittest

from art_capture_batch import bootstrap
from art_round_check import run, artifact_hash


class CaptureRoundTests(unittest.TestCase):
    def test_changed_or_missing_referenced_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dumps = root/'docs/test/current'
            dumps.mkdir(parents=True)
            report = dumps.parent/'mask.json'
            (dumps/'page.json').write_text('{"render_mask_report":"docs/test/mask.json"}')
            report.write_text('{"visible":true}')
            before = artifact_hash(root, dumps)
            report.write_text('{"visible":false}')
            self.assertNotEqual(before, artifact_hash(root, dumps))
            report.unlink()
            with self.assertRaises(FileNotFoundError):
                artifact_hash(root, dumps)

    def test_legacy_capture_and_changed_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build = root/'build'
            dumps = root/'old'
            for directory in (build, dumps, root/'assets', root/'docs/art'):
                directory.mkdir(parents=True)
            (build/'index.html').write_text('<html><head></head></html>')
            (dumps/'capture-ui-dump-home.json').write_text(json.dumps(dict(
                screen='home', kind='home', viewport={'width':375,'height':667}, page={'dpr':2})))
            matrix = root/'docs/art/capture-plan.json'
            bootstrap(dumps, matrix)
            policy = json.loads(matrix.read_text())
            row = policy['cases'][0]
            self.assertFalse(row['stable'])
            row.update(recipe='open home', environment='fixture', stable=True, witness=[{'path':'Canvas/Home'}])
            matrix.write_text(json.dumps(policy))
            self.assertIn('id', run('start', root, build))
            plan = run('verify', root, build, dumps)
            self.assertFalse(plan['ready'])
            self.assertEqual(plan['cases'][0]['action'], 'recapture')
            (root/'assets/layout.json').write_text('{}')
            self.assertIn('rebuild', run('start', root, build)['error'])


if __name__ == '__main__':
    unittest.main()

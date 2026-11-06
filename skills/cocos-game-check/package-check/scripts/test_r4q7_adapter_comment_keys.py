"""11.17 R4Q7 item 1 (SLS16-3): an ad/runtime regression adapter with a "_scope" comment key was refused as
"unknown keys". Keys starting with "_" are comments; a real typo is still refused."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True
import ad_regression  # noqa: E402
import runtime_regression  # noqa: E402


class AdapterCommentKeys(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, data):
        path = self.root / 'adapter.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def test_underscore_comment_key_accepted_by_both_loaders(self):
        # SLS16-3 wrote this shape: real keys plus a "_scope" note.
        path = self.write({'request': 'grant();', '_scope': 'home x2 and revive only', '_note2': 1})
        self.assertEqual(ad_regression.load_adapter(path)['request'], 'grant();')
        runtime_regression.load_adapter(path)

    def test_real_typo_still_refused(self):
        path = self.write({'request': 'grant();', 'scope': 'typo without underscore'})
        with self.assertRaises(ad_regression.RegressionRefused):
            ad_regression.load_adapter(path)
        with self.assertRaises(runtime_regression.RuntimeRefused):
            runtime_regression.load_adapter(path)


if __name__ == '__main__':
    unittest.main()

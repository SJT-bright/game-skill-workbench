"""Filesystem input boundaries; no browser/service and no game files."""
from pathlib import Path
import importlib.util
import json
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('fixture_prepare', HERE / 'prepare_ui_engine_fixture.py')
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class FixturePreparation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.engine = self.root / 'engine-input.js'
        self.engine.write_text('/* input-only engine fixture bytes */')
        self.candidate = self.root / 'candidate'
        self.baseline = self.root / 'baseline'
        for root in (self.candidate, self.baseline):
            (root / 'parts').mkdir(parents=True)
            for name in M.PARTS:
                (root / 'parts' / name).write_text(root.name + name)

    def test_exact_bytes_and_optional_baseline(self):
        out = self.root / 'output'
        result = M.prepare(self.engine, self.candidate, out, self.baseline)
        self.assertTrue(result['baseline_supplied'])
        self.assertEqual((out / 'engine.js').read_bytes(), self.engine.read_bytes())
        self.assertEqual((out / 'after-GameUIKit.js').read_bytes(), (self.candidate / 'parts/GameUIKit.js').read_bytes())
        self.assertEqual((out / 'before-ScreenFit.js').read_bytes(), (self.baseline / 'parts/ScreenFit.js').read_bytes())
        self.assertFalse(result['starts_service_or_browser'])
        second = self.root / 'candidate-only'
        M.prepare(self.engine, self.candidate, second)
        self.assertFalse((second / 'before-GameUIKit.js').exists())
        self.assertFalse(json.loads((second / 'fixture-inputs.json').read_text())['baseline_supplied'])

    def test_existing_output_is_not_overwritten(self):
        out = self.root / 'existing'
        out.mkdir()
        sentinel = out / 'preserve'
        sentinel.write_text('keep')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            M.prepare(self.engine, self.candidate, out)
        self.assertEqual(sentinel.read_text(), 'keep')

    def test_output_inside_each_input_tree_is_rejected(self):
        for root in (self.candidate, self.baseline, M.KIT):
            with self.assertRaisesRegex(ValueError, 'outside'):
                M.prepare(self.engine, self.candidate, root / 'forbidden-output', self.baseline)
            self.assertFalse((root / 'forbidden-output').exists())

    def test_missing_inputs_do_not_create_output(self):
        out = self.root / 'not-created'
        with self.assertRaisesRegex(ValueError, 'engine bundle'):
            M.prepare(self.root / 'missing.js', self.candidate, out)
        (self.candidate / 'parts/GameUIKit.js').unlink()
        with self.assertRaisesRegex(ValueError, 'missing shared component'):
            M.prepare(self.engine, self.candidate, out)
        self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()

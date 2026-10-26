"""Synthetic boundary regression: refusal must occur before either writer opens output."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_no_ad_simulator as guard
import make_tiktok_zip as full_writer
import verify_native_zip as verifier
spec = importlib.util.spec_from_file_location('final_package_check', HERE.parents[1] / 'cocos-tiktok-package-check/scripts/check_package.py')
light_writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(light_writer)


class NoAdSimulator(unittest.TestCase):
    def files(self):
        return {'game.js': b'// production ad adapter; mock is mentioned in a comment only',
                'game.json': b'{"subpackages":[]}',
                'project.config.json': b'{"appid":"test-app"}'}

    def test_known_tool_renamed_disabled_and_setup_are_refused(self):
        script = (HERE.parent / 'assets/ad-simulator.js').read_bytes()
        for name, content in [('ad-simulator.js', b'/* empty */'),
                              ('assets/renamed.js', script),
                              ('assets/main.js', b'if(false){window.__adSimulator={};}'),
                              ('assets/data.bin', b'/__local_ad_simulator_setup.js')]:
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'simulator'):
                guard.enforce_files({name: content})

    def test_both_writers_refuse_without_output_and_accept_clean_control(self):
        for writer in ('full', 'light'):
            for dirty in (True, False):
                with self.subTest(writer=writer, dirty=dirty), tempfile.TemporaryDirectory() as folder:
                    root = Path(folder); output = root / 'upload.zip'; native = root / 'native'; native.mkdir()
                    files = self.files()
                    if dirty: files['game.js'] += b';window.__adSimulator={};'
                    for name, data in files.items(): (native / name).write_bytes(data)
                    def run():
                        if writer == 'full': full_writer.write_zip(native, list(files), output)
                        else: light_writer.write_archive(output, files)
                    if dirty:
                        with self.assertRaisesRegex(ValueError, 'simulator'): run()
                        self.assertFalse(output.exists())
                    else:
                        run()
                        with zipfile.ZipFile(output) as z:
                            self.assertEqual({n:z.read(n) for n in z.namelist()}, files)

    def test_existing_zip_verifier_rejects_residue(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'candidate.zip'
            for dirty in (False, True):
                files = self.files()
                if dirty: files['assets/renamed.js'] = b'window.__adSimulator={};'
                with zipfile.ZipFile(path, 'w') as z:
                    for name, data in files.items(): z.writestr(name, data)
                # Startup is orthogonal to this synthetic byte-residue test.
                with patch('audit_upload_startup.audit_files', return_value={'passed': True, 'errors': []}):
                    if dirty:
                        with self.assertRaisesRegex(ValueError, 'simulator'): verifier.verify(path)
                    else: self.assertTrue(verifier.verify(path)['no_local_ad_simulator'])


if __name__ == '__main__': unittest.main()

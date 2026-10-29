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
spec = importlib.util.spec_from_file_location('final_package_check', HERE.parents[1] / 'cocos-game-check/package-check/scripts/check_package.py')
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


class ForbiddenWindows(unittest.TestCase):
    def test_cocos_spriteframe_art_name_is_not_a_player_label(self):
        frame = [1, ['texture-uuid'], ['_textureSetter'], ['cc.SpriteFrame'], 0,
                 [{'name': 'credits', 'rect': [0,0,451,261], 'offset': [0,0],
                   'originalSize': [451,261], 'capInsets': [0,0,0,0]}], [0], 0, [0], [0], [0]]
        guard.check_entry('assets/ui/import/art.json', json.dumps(frame).encode())
        for field, value in [('label', 'Credits'), ('name', '__adSimulator')]:
            dirty = json.loads(json.dumps(frame)); dirty[5][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                guard.check_entry('assets/ui/import/art.json', json.dumps(dirty).encode())
        with self.assertRaises(ValueError):
            guard.check_entry('assets/ui/import/ui.json', b'{"__type__":"cc.Label","_string":"Credits"}')

    dirty = [
        ('assets/renamed.bin', b'Local test ad'),
        ('assets/main.js', b'if(false){show("Complete test ad")}'),
        ('preview-ads.js', b'// disabled'),
        ('assets/main.js', b'this.button(body, template, "Credits / About", 0, 50, 460, 110, callback)'),
        ('assets/main.js', b'openCredits()'),
        ('assets/main.js', b'label("Local\\u0020test ad")'),
        ('assets/main.js', b'label("\\u0043redits")'),
        ('assets/main.json', b'{"__type__":"cc.Label","_string":"Credits"}'),
        ('settings.html', b'<button>Credits / About</button>'),
    ]
    def test_signatures_and_normal_controls(self):
        for name,data in self.dirty:
            with self.subTest(name=name,data=data), self.assertRaises(ValueError):
                guard.enforce_files({name:data})
        guard.enforce_files({'game.js':b'const credits=50; const settingsNodeName="about"; ad.onClose(r=>r.isEnded===true && award()); // "Credits" is not displayed',
                             'LICENSE.txt':b'Credits and authors, SIL OFL',
                             'assets/settings-credits-about.png':b'opaque unused texture'})
    def test_native_preflight_refuses_before_startup(self):
        for name,data in self.dirty:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                root=Path(folder);files=NoAdSimulator().files();files[name]=data
                for rel,raw in files.items():
                    p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
                with patch('audit_upload_startup.audit_files') as startup:
                    errors,_,_=full_writer.native_problems(root)
                    self.assertTrue(errors);startup.assert_not_called()
    def test_both_writers_and_final_verifier_reject_each_window(self):
        for name,data in self.dirty:
            for writer in ('full','light','final'):
                with self.subTest(name=name,writer=writer), tempfile.TemporaryDirectory() as folder:
                    root=Path(folder); native=root/'native';native.mkdir();output=root/'upload.zip'
                    files=NoAdSimulator().files();files[name]=data
                    for rel,raw in files.items():
                        target=native/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
                    if writer=='full':
                        with self.assertRaises(ValueError):full_writer.write_zip(native,list(files),output)
                    elif writer=='light':
                        with self.assertRaises(ValueError):light_writer.write_archive(output,files)
                    else:
                        with zipfile.ZipFile(output,'w') as z:
                            for rel,raw in files.items():z.writestr(rel,raw)
                        with patch('audit_upload_startup.audit_files',return_value={'passed':True,'errors':[]}):
                            with self.assertRaises(ValueError):verifier.verify(output)
                        continue
                    self.assertFalse(output.exists())

if __name__ == '__main__': unittest.main()

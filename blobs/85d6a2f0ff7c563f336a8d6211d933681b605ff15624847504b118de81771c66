#!/usr/bin/env python3
"""v7.8 (总表 B32 b): after a package is written, older packages of the same game go into 旧包/ (with their receipts and
reports) and 最新.txt names the file to upload; source ZIPs, other games' packages (same test App ID), unreadable ZIPs and
everything else stay where they are; nothing is overwritten (remake-core/scripts/delivery_folder.py).
Bad: a folder like 剪刀达人's (many versions next to each other) must end with one package; good: other files untouched.
The light writer (build_checked_zip.build) runs it after publishing; --keep-old-packages leaves the folder alone.
Run: python3 -B test_delivery_folder.py
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'remake-core' / 'scripts'))
import delivery_folder as D  # noqa: E402

APP = '7683427172773644296'


def pkg(path, app=APP, own=('assets/main/import/aa/aa1.json', 'assets/main/native/bb/bb2.png', 'subpackages/s1/game.js'),
        root=True, extra=()):
    with zipfile.ZipFile(path, 'w') as z:
        if root:
            z.writestr('game.js', 'require("./main")')
            z.writestr('game.json', '{"deviceOrientation":"portrait"}')
            z.writestr('project.config.json', json.dumps({'appid': app}))
        z.writestr('cocos/cocos2d-js-min.js', 'engine')
        z.writestr('assets/internal/import/00/internal.json', '{}')
        for name in list(own) + list(extra):
            z.writestr(name, name)
    return path


class Plan(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='delivery folder ')
        self.dir = Path(self.temp.name) / '交付'
        self.dir.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def scissors_like(self):
        for v in range(26, 30):
            pkg(self.dir / ('剪刀达人_TikTok测试包_v%d.zip' % v), extra=('assets/main/import/v%d.json' % v,))
            (self.dir / ('剪刀达人_TikTok测试包_v%d.zip.receipt.json' % v)).write_text('{}')
        (self.dir / '剪刀达人_TikTok测试包_v28.report.json').write_text('{}')
        pkg(self.dir / '剪刀达人_源码_v29.zip', root=False)                         # source ZIP: not a package
        pkg(self.dir / 'OtherGame_TikTok.zip', own=('assets/main/import/zz/zz9.json', 'assets/x/y.png', 'assets/q/r.json'))
        pkg(self.dir / 'OtherApp.zip', app='7000000000000000001')
        (self.dir / 'broken.zip').write_bytes(b'not a zip')
        (self.dir / 'notes.md').write_text('keep me')
        (self.dir / 'delivery_receipt_v29.json').write_text('{}')
        return pkg(self.dir / '剪刀达人_TikTok测试包_v30.zip')

    def test_plan_lists_only_same_game_packages(self):
        new = self.scissors_like()
        p = D.plan(new, APP)
        self.assertEqual([m['zip'] for m in p['move']], ['剪刀达人_TikTok测试包_v%d.zip' % v for v in range(26, 30)])
        self.assertEqual(p['move'][2]['with'], ['剪刀达人_TikTok测试包_v28.zip.receipt.json', '剪刀达人_TikTok测试包_v28.report.json'])
        left = {x['file']: x['why'] for x in p['left']}
        self.assertIn('not a TikTok upload package', left['剪刀达人_源码_v29.zip'])
        self.assertIn('another game', left['OtherGame_TikTok.zip'])
        self.assertIn('other App ID', left['OtherApp.zip'])
        self.assertIn('broken.zip', left)
        self.assertTrue((self.dir / '剪刀达人_TikTok测试包_v26.zip').exists())      # plan is read only

    def test_tidy_moves_them_writes_latest_and_touches_nothing_else(self):
        new = self.scissors_like()
        before = {p.name for p in self.dir.iterdir()}
        r = D.tidy(new, APP, 'build_checked_zip', 'f' * 64)
        self.assertEqual(r['errors'], [])
        now = {p.name for p in self.dir.iterdir()}
        moved = {Path(m['from']).name for m in r['moved']}
        self.assertEqual(now, (before - moved) | {D.OLD_DIR, D.LATEST})
        self.assertEqual(sorted(p.name for p in (self.dir / D.OLD_DIR).iterdir()), sorted(moved))
        self.assertEqual(len([n for n in now if n.endswith('.zip') and 'TikTok测试包' in n]), 1)
        text = (self.dir / D.LATEST).read_text(encoding='utf-8')
        self.assertTrue(text.startswith(D.MARK))
        self.assertIn('上传 TikTok 用这个：%s' % new, text)
        self.assertIn('sha256：' + 'f' * 64, text)
        self.assertIn('剪刀达人_TikTok测试包_v26.zip', text)
        for keep in ('notes.md', 'delivery_receipt_v29.json', '剪刀达人_源码_v29.zip', 'OtherGame_TikTok.zip', 'broken.zip'):
            self.assertIn(keep, now)
        self.assertTrue(any('挪进 旧包/' in line for line in D.describe(r)))

    def test_names_taken_in_old_folder_are_never_overwritten(self):
        pkg(self.dir / 'Game_v1.zip')
        (self.dir / D.OLD_DIR).mkdir()
        (self.dir / D.OLD_DIR / 'Game_v1.zip').write_bytes(b'older copy')
        new = pkg(self.dir / 'Game_v2.zip')
        D.tidy(new, APP)
        self.assertEqual((self.dir / D.OLD_DIR / 'Game_v1.zip').read_bytes(), b'older copy')
        self.assertTrue((self.dir / D.OLD_DIR / 'Game_v1 (2).zip').is_file())

    def test_own_latest_txt_and_keep_flag(self):
        pkg(self.dir / 'Game_v1.zip')
        (self.dir / D.LATEST).write_text('my own notes', encoding='utf-8')
        new = pkg(self.dir / 'Game_v2.zip')
        r = D.tidy(new, APP, keep=True)
        self.assertTrue(r['skipped'])
        self.assertTrue((self.dir / 'Game_v1.zip').exists())
        with patch.dict('os.environ', {D.ENV_KEEP: '1'}):
            self.assertTrue(D.tidy(new, APP)['skipped'])
        r = D.tidy(new, APP)
        self.assertFalse((self.dir / 'Game_v1.zip').exists())
        self.assertEqual((self.dir / D.LATEST).read_text(encoding='utf-8'), 'my own notes')
        self.assertTrue(any('not written by the writer' in e for e in r['errors']))

    def test_new_file_must_be_a_package(self):
        bad = pkg(self.dir / 'source.zip', root=False)
        self.assertTrue(D.tidy(bad, APP)['errors'])


class Writer(unittest.TestCase):
    """build_checked_zip.build() tidies its output folder after publishing (and leaves it with keep_old_packages)."""

    def setUp(self):
        from test_resource_and_issue_obligations import KitMainStaticManifest
        self.case = KitMainStaticManifest('test_light_writer_writes_zip_with_the_static_manifest')
        self.case.setUp()

    def tearDown(self):
        self.case.tearDown()

    def run_build(self, out, **kw):
        import check_package
        from build_checked_zip import build
        manifest = self.case.setup_package()
        with patch('build_checked_zip.audit_final_startup', return_value={'passed': True, 'patched': True}), \
                patch.object(check_package, 'rewarded_ad_gate', return_value={'status': 'patched_in_unit_test'}), \
                patch('check_package.runtime_gate', return_value={'id': 'runtime_regression', 'status': 'patched'}):
            return build(self.case.native, APP, out, resource_manifest=manifest, project=self.case.project, **kw)

    def test_writer_moves_the_older_package(self):
        from check_package import native_files, write_archive
        folder = self.case.root / '交付'
        folder.mkdir()
        self.case.setup_package()
        write_archive(folder / 'Game_v1.zip', native_files(self.case.native))
        (folder / 'Game_v1.zip.receipt.json').write_text('{}')
        (folder / 'Game_源码_v1.zip').write_bytes(b'PK\x05\x06' + b'\0' * 18)
        result = self.run_build(folder / 'Game_v2.zip')
        self.assertEqual(sorted(p.name for p in folder.iterdir()),
                         sorted(['Game_v2.zip', 'Game_v2.zip.receipt.json', 'Game_源码_v1.zip', D.OLD_DIR, D.LATEST]))
        self.assertEqual(sorted(p.name for p in (folder / D.OLD_DIR).iterdir()), ['Game_v1.zip', 'Game_v1.zip.receipt.json'])
        self.assertEqual(result['delivery_folder']['latest'], str(folder / D.LATEST))
        self.assertIn(result['sha256'], (folder / D.LATEST).read_text(encoding='utf-8'))

    def test_writer_keep_old_packages(self):
        from check_package import native_files, write_archive
        folder = self.case.root / '交付'
        folder.mkdir()
        self.case.setup_package()
        write_archive(folder / 'Game_v1.zip', native_files(self.case.native))
        result = self.run_build(folder / 'Game_v2.zip', keep_old_packages=True)
        self.assertTrue((folder / 'Game_v1.zip').exists())
        self.assertFalse((folder / D.LATEST).exists())
        self.assertTrue(result['delivery_folder']['skipped'])

    def test_formal_writer_is_wired(self):
        text = (HERE.parents[2] / 'remake-core' / 'scripts' / 'make_tiktok_zip.py').read_text(encoding='utf-8')
        self.assertIn("delivery_folder.tidy(out, a.app_id, 'make_tiktok_zip', report['zip_sha256'],", text)
        self.assertIn("'--keep-old-packages'", text)


if __name__ == '__main__':
    unittest.main(verbosity=1)

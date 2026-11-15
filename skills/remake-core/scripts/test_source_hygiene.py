#!/usr/bin/env python3
"""简化.11.6 source hygiene (Saul 2026-11-04, 91 SLS11: the seller ZIP's .git kept app_desc.txt with an account and a
password). source_hygiene.py finds version-control / IDE folders and credentials; make_source_zip.py leaves the folders
out and refuses credentials; package_gates/secrets.py blocks both in an upload package; prepare_delivery.py --source
refuses an unclean source before anything else. Good inputs pass, bad ones are refused for their own reason.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_source_hygiene.py"""
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import source_hygiene as H  # noqa: E402
import package_gates  # noqa: E402

SETTINGS = '{\n  "appid": "123",\n  "appSecret": "%s"\n}\n'
BUILDER = '{\n  "keystorePassword": "",\n  "keystoreAliasPassword": "",\n  "secretIncluded": false\n}\n'


def project(extra=None):
    root = Path(tempfile.mkdtemp(prefix='hyg-'))
    files = {'assets/scripts/Game.ts': 'export const a = 1;\n', 'assets/scripts/build/levels.json': '{"n": 3}\n',
             'settings/project.json': SETTINGS % '', 'local/builder.json': BUILDER, 'project.json': '{}\n',
             'library/imports/x.json': '{}', 'temp/a.txt': 'x', '.git/HEAD': 'ref: refs/heads/master\n',
             '.git/objects/ab/cdef': 'blob', '.idea/workspace.xml': '<x/>', '.DS_Store': 'x'}
    files.update(extra or {})
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    return root


def zip_of(root, top='Game'):
    out = Path(tempfile.mkdtemp(prefix='hygz-')) / 'src.zip'
    with zipfile.ZipFile(out, 'w') as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():
                z.write(p, '%s/%s' % (top, p.relative_to(root).as_posix()))
        z.writestr('__MACOSX/Game/._x', 'junk')
    return out


class Scan(unittest.TestCase):
    def test_sls11_shape_is_found(self):
        r = H.audit(zip_of(project()))
        self.assertFalse(r['passed'])
        kinds = {v['path']: v['kind'] for v in r['vcs_ide']}
        self.assertEqual(kinds.get('Game/.git'), 'vcs')
        self.assertEqual(kinds.get('Game/.idea'), 'ide')
        self.assertEqual(kinds.get('__MACOSX'), 'junk')
        self.assertEqual(r['secrets'], [], 'empty keystorePassword and secretIncluded false are not credentials')

    def test_credentials(self):
        cases = {'app_desc.txt': ('app_desc.txt', '账号：dev@example.com\n密码：Abc12345\n'),
                 'appSecret': ('settings/project.json', SETTINGS % '959b3ac0037d0f3c'),
                 'password line': ('docs/notes.md', 'test login password: hunter22\n'),
                 'keystore': ('build-templates/key/release.keystore', 'binary'),
                 'cn label': ('docs/上架.txt', '后台账号 = studio_01\n')}
        for name, (rel, text) in cases.items():
            r = H.audit(project({rel: text, '.git/HEAD': '', '.idea/workspace.xml': ''}))
            self.assertIn(rel, [s['path'] for s in r['secrets']], name)

    def test_clean_project_without_vcs_passes(self):
        root = project()
        for d in ('.git', '.idea'):
            subprocess.run(['rm', '-rf', str(root / d)], check=True)
        (root / '.DS_Store').unlink()
        self.assertTrue(H.audit(root)['passed'])

    def test_nested_build_folder_is_not_a_cache(self):
        r = H.audit(project({'assets/scripts/build/conf.json': '{"apiKey": "abcdef123"}'}))
        self.assertIn('assets/scripts/build/conf.json', [s['path'] for s in r['secrets']])


class SourceZipWriter(unittest.TestCase):
    def run_writer(self, root):
        out = Path(tempfile.mkdtemp(prefix='hygo-')) / 'Game_Source.zip'
        r = subprocess.run([sys.executable, '-B', str(HERE / 'make_source_zip.py'), '--project', str(root), '--out', str(out)],
                           capture_output=True, text=True)
        return r.returncode, json.loads(r.stdout), out

    def test_written_zip_has_no_vcs_ide_or_caches(self):
        code, r, out = self.run_writer(project())
        self.assertEqual(code, 0, r)
        names = zipfile.ZipFile(out).namelist()
        for bad in ('/.git/', '/.idea/', '/library/', '/temp/', '/local/', '.DS_Store'):
            self.assertFalse([n for n in names if bad in n], bad)
        self.assertTrue(any(n.endswith('assets/scripts/build/levels.json') for n in names), 'nested build folder kept')
        self.assertTrue(H.audit(out)['passed'])
        self.assertTrue(Path(str(out) + '.sha256').is_file())
        self.assertEqual(sorted(r['left_out_vcs_ide']), ['.git', '.idea'])

    def test_credentials_refuse_and_nothing_is_written(self):
        for rel, text in {'app_desc.txt': '密码：Abc12345\n', 'settings/project.json': SETTINGS % '959b3ac0037d0f3c'}.items():
            code, r, out = self.run_writer(project({rel: text}))
            self.assertEqual(code, 1, rel)
            self.assertFalse(out.exists(), rel)
            self.assertIn(rel, ' '.join(r['problems']))


class UploadGate(unittest.TestCase):
    def files(self, extra):
        base = {'game.json': b'{}', 'game.js': b'', 'project.config.json': b'{}', 'assets/main/index.js': b'var a=1;'}
        base.update(extra)
        return base

    def ids(self, files, policy='new'):
        return {f['id'] for f in package_gates.run(files, None, 'localize', modules=('secrets',), policy=policy)['blocks']}

    def test_blocks_vcs_and_credentials_for_every_policy(self):
        for policy in ('new', 'legacy'):
            self.assertEqual(self.ids(self.files({'.git/HEAD': b'ref'}), policy), {'H1_vcs_ide_in_package'})
            self.assertEqual(self.ids(self.files({'app_desc.txt': b'x'}), policy), {'H2_credentials_in_package'})
        self.assertEqual(self.ids(self.files({})), set())

    def test_every_entry_runs_it(self):
        self.assertIn('secrets', package_gates.GATE_MODULES)
        result = package_gates.run(self.files({'.svn/entries': b'x'}), None, 'remake', policy='new')
        self.assertIn('secrets', result['gates'])
        self.assertIn('H1_vcs_ide_in_package', [f['id'] for f in result['blocks']])


class DeliveryRefusesUncleanSource(unittest.TestCase):
    def test_source_with_git_is_refused_before_the_package_check(self):
        sys.path.insert(0, str(HERE.parents[1] / 'cocos-game-check' / 'package-check' / 'scripts'))
        import prepare_delivery as P
        work = Path(tempfile.mkdtemp(prefix='hygd-'))
        archive, native, record = work / 'Game.zip', work / 'native', work / 'out' / 'record.json'
        native.mkdir()
        with zipfile.ZipFile(archive, 'w') as z:
            # A valid game ZIP must pass the fresh size gate before source hygiene.
            z.writestr('game.js', 'boot();')
            z.writestr('game.json', '{}')
            z.writestr('project.config.json', '{"appid":"123"}')
        source = zip_of(project())
        # Only the external CLI boundary is synthetic; final ZIP inspection remains real.
        digest = __import__('hashlib').sha256(archive.read_bytes()).hexdigest()
        def cli_boundary(actual_archive, expected_sha):
            self.assertEqual(Path(actual_archive).resolve(), archive.resolve())
            self.assertEqual(expected_sha, digest)
            self.assertEqual(__import__('hashlib').sha256(Path(actual_archive).read_bytes()).hexdigest(), digest)
            return {'passed': True, 'errors': [], 'version': 'synthetic-cli-boundary'}
        with mock.patch('tiktok_cli_gate.verify', side_effect=cli_boundary) as cli, \
                mock.patch.object(P.tempfile, 'gettempdir', return_value='/nonexistent-temp'), \
                mock.patch.object(P, 'check', side_effect=AssertionError('the package check must not run first')):
            with self.assertRaises(ValueError) as cm:
                P.prepare(archive, native, '123', record, source=source)
        self.assertIn('source_hygiene', str(cm.exception))
        self.assertIn('.git', str(cm.exception))
        self.assertFalse(record.exists())
        cli.assert_called_once_with(str(archive.resolve()), digest)
        size = json.loads(Path(str(record.resolve()) + '.size.json').read_text())
        self.assertTrue(size['size_passed'])
        self.assertEqual(size['sha256'], digest)


if __name__ == '__main__':
    unittest.main()

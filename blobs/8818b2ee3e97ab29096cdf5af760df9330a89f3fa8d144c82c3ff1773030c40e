#!/usr/bin/env python3
"""v7.9 (指尖麻将 v42-v57): a problem seen on a phone closes only when the phone's own package fails on the computer.

The phone report is registered with the ZIP that ran on the phone, what was seen, the phone's error line and, per case,
what the phone screen showed ("phone" assertions). The retest must run that very ZIP as the failing side; the "phone"
assertions must hold there; when the phone showed an error line, the failing run must print it and the fixed run must
not. `check` gives the plain line the delivery reply repeats. Not reproduced: it blocks, and only Saul's words
(defer-external, device_not_reproduced) let a test package out, with a line saying it is not fixed.
Run: python3 -B test_device_issue_repro.py
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'remake-core' / 'scripts'))
import package_issue_gate as issues  # noqa: E402

SCRIPT = HERE.parents[2] / 'remake-core' / 'scripts' / 'package_issue_gate.py'
PHONE_LINE = '[Mahjong loading] No loading progress for 10 foreground seconds.'
OTHER_LINE = 'UI asset made no loading progress: outers/mainmenu/images/item_bg'
V78_CHECKER = 'f15395aa873bb3b8763b12befad6f1b8190a6b31cdbfc80b3d0c651da711a0be'
# The runner reads what it "saw" from a side file next to the tree: the same package bytes can fail in different ways
# under different test conditions (on v57 a clock jump printed a UiKit error, a 12 s JS pause printed the phone's line).
RUNNER = ("import argparse,json\nfrom pathlib import Path\np=argparse.ArgumentParser();p.add_argument('--native');"
          "p.add_argument('--case');a=p.parse_args();n=Path(a.native);side=n.parent/(n.name+'.errors.json')\n"
          "print(json.dumps({'observed':json.loads((n/'state.json').read_text()),"
          "'errors':json.loads(side.read_text()) if side.exists() else []}))\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        issues.initialize(self.project)
        self.phone_zip = self.root / '指尖麻将.zip'
        with zipfile.ZipFile(self.phone_zip, 'w') as z:
            z.writestr('game.js', 'require("main.js")')
            z.writestr('state.json', json.dumps({'home_play_works': False, 'home_visible': True}))
            z.writestr('__MACOSX/._game.js', 'junk')
        self.negative = self.unzip(self.phone_zip, 'phone')
        self.native = self.tree('fixed', True)
        self.normal = self.tree('normal', True)
        self.runner = self.root / 'runner.py'
        self.runner.write_text(RUNNER)
        self.local_cases = [{'id': 'pause_while_loading',
                             'assertions': [{'path': ['home_play_works'], 'op': 'eq', 'value': True}]}]
        # The phone showed the home page with dead buttons: home_visible must hold when the phone package runs.
        self.cases = [dict(self.local_cases[0], phone=[{'path': ['home_visible'], 'op': 'eq', 'value': True}])]
        self.errors(self.negative, [PHONE_LINE])

    def tearDown(self):
        self.temp.cleanup()

    def unzip(self, archive, name):
        out = self.root / name
        with zipfile.ZipFile(archive) as z:
            z.extractall(out)
        shutil.rmtree(out / '__MACOSX')
        (out / '.DS_Store').write_text('finder')          # junk Finder adds later must not matter
        return out

    def tree(self, name, works):
        out = self.root / name
        out.mkdir()
        (out / 'game.js').write_text('require("main.js") // fixed')
        (out / 'state.json').write_text(json.dumps({'home_play_works': works, 'home_visible': True}))
        return out

    def errors(self, tree, lines):
        (tree.parent / (tree.name + '.errors.json')).write_text(json.dumps(lines))

    def report(self, phone_error=PHONE_LINE, issue='home-lock'):
        device = issues.device_record(self.phone_zip, '首页所有按钮点不动', phone_error)
        issues.register(self.project, self.native, issue, '扫码进去后首页按钮全都点不动', ['state.json'], self.cases,
                        self.runner, device=device)

    def retest(self, negative=None, out='retest', issue='home-lock'):
        return issues.retest(self.project, self.native, issue, negative or self.negative, self.normal, self.root / out)

    def authorize(self, issue='home-lock', requirement='device_not_reproduced', quote='先出测试包，我拿手机看'):
        path = self.root / ('auth-%s.json' % issue)
        path.write_text(json.dumps({'schema': 'external_test_scope.v1', 'issue_id': issue, 'user_quote': quote,
                                    'authority': 'explicit_current_user_instruction', 'scope': 'local_test_candidate_only',
                                    'external_requirement': requirement, 'reason': '电脑上复现不出来'}, ensure_ascii=False))
        return path


class PhoneReports(Base):
    def test_phone_package_with_the_phone_error_closes_and_says_so(self):
        self.report()
        self.retest()
        result = issues.audit(self.project, self.native)
        [device] = result['device_issues']
        self.assertEqual(device['status'], 'phone_error_matched')
        self.assertIn('同一行报错', device['line'])
        self.assertIn(PHONE_LINE, device['line'])

    def test_open_phone_report_blocks_with_a_plain_reason(self):
        self.report()
        with self.assertRaisesRegex(ValueError, 'not reproduced on the computer yet.*指尖麻将.zip'):
            issues.audit(self.project, self.native)

    def test_made_up_failing_copy_is_not_the_phone(self):
        self.report()
        made_up = self.tree('made_up', False)            # fails the same assertion, but it is not what ran on the phone
        self.errors(made_up, [PHONE_LINE])
        with self.assertRaisesRegex(ValueError, 'very package that ran on the phone'):
            self.retest(made_up)
        with self.assertRaisesRegex(ValueError, 'not reproduced'):
            issues.audit(self.project, self.native)

    def test_a_different_failure_on_the_phone_package_does_not_close_it(self):
        self.report()
        self.errors(self.negative, [OTHER_LINE])         # same package, different condition, different failure
        with self.assertRaisesRegex(ValueError, 'no case printed it on the phone package'):
            self.retest()

    def test_same_error_line_on_a_black_screen_is_not_the_phone(self):
        (self.negative / 'state.json').write_text(json.dumps({'home_play_works': False, 'home_visible': False}))
        self.phone_zip.unlink()                          # the phone package itself shows a black screen here
        with zipfile.ZipFile(self.phone_zip, 'w') as z:
            for name in ('game.js', 'state.json'):
                z.write(self.negative / name, name)
        self.report()
        with self.assertRaisesRegex(ValueError, 'not the way the phone did'):
            self.retest()

    def test_phone_report_needs_what_the_screen_showed(self):
        device = issues.device_record(self.phone_zip, '首页所有按钮点不动', PHONE_LINE)
        with self.assertRaisesRegex(ValueError, 'at least one case with "phone"'):
            issues.register(self.project, self.native, 'no-screen', '首页点不动', ['state.json'], self.local_cases,
                            self.runner, device=device)
        with self.assertRaisesRegex(ValueError, 'belong to a phone report'):
            issues.register(self.project, self.native, 'local-with-phone', 'x', ['state.json'], self.cases, self.runner)

    def test_fixed_package_still_printing_the_error_is_refused(self):
        self.report()
        self.errors(self.native, ['x ' + PHONE_LINE.upper()])  # case and spacing do not hide it
        with self.assertRaisesRegex(ValueError, 'fixed package still prints'):
            self.retest()

    def test_without_a_phone_error_the_line_says_not_certain(self):
        self.report(phone_error='')
        self.errors(self.negative, [])
        self.retest()
        [device] = issues.audit(self.project, self.native)['device_issues']
        self.assertEqual(device['status'], 'symptom_only')
        self.assertIn('不能完全确定是同一个原因', device['line'])

    def test_phone_package_edited_after_closing_reopens(self):
        self.report()
        self.retest()
        (self.negative / 'game.js').write_text('edited')
        with self.assertRaisesRegex(ValueError, 'very package that ran on the phone'):
            issues.audit(self.project, self.native)

    def test_not_reproduced_needs_sauls_words_and_says_not_fixed(self):
        self.report()
        with self.assertRaisesRegex(ValueError, 'device-only local test scope'):
            issues.defer_external(self.project, self.native, 'home-lock', self.authorize(quote='  '))
        issues.defer_external(self.project, self.native, 'home-lock', self.authorize())
        result = issues.audit(self.project, self.native)
        [device] = result['device_issues']
        self.assertEqual(device['status'], 'not_reproduced')
        self.assertIn('电脑上没复现，不能说修好了', device['line'])

    def test_local_issue_cannot_use_the_phone_deferral(self):
        issues.register(self.project, self.native, 'local-one', 'found on the computer', ['state.json'], self.local_cases,
                        self.runner)
        with self.assertRaisesRegex(ValueError, 'device-only local test scope'):
            issues.defer_external(self.project, self.native, 'local-one', self.authorize('local-one'))

    def test_device_record_needs_the_phone_zip_and_what_was_seen(self):
        with self.assertRaisesRegex(ValueError, 'device-zip'):
            issues.device_record(self.root / 'missing.zip', '首页按钮点不动')
        with self.assertRaisesRegex(ValueError, 'symptom'):
            issues.device_record(self.phone_zip, ' 卡 ')
        source = self.root / 'source.zip'
        with zipfile.ZipFile(source, 'w') as z:
            z.writestr('assets/a.js', '1')
        with self.assertRaisesRegex(ValueError, 'no game.js'):
            issues.device_record(source, '首页按钮点不动')

    def test_scope_update_cannot_drop_the_phone_binding(self):
        self.report()
        events, _ = issues.load(self.project)
        original = events[1]['payload']
        updated = {k: v for k, v in original.items() if k != 'device'}
        issues.append(self.project, 'scope_updated', {'id': 'home-lock', 'reason': 'x',
                      'previous_contract_signature': issues.digest(original), 'contract': updated})
        with self.assertRaisesRegex(ValueError, 'may not erase'):
            issues.audit(self.project, self.native)


class CommandLine(Base):
    def run_cli(self, *extra):
        cases = self.root / 'cases.json'
        cases.write_text(json.dumps(self.cases))
        base = [sys.executable, '-B', str(SCRIPT), 'report', '--project', str(self.project), '--native', str(self.native),
                '--id', 'cli-one', '--message', '首页点不动', '--targets', 'state.json', '--cases', str(cases),
                '--runner', str(self.runner)]
        return subprocess.run(base + list(extra), capture_output=True, text=True)

    def test_report_must_say_where_it_was_seen(self):
        bad = self.run_cli()
        self.assertEqual(bad.returncode, 1)
        self.assertIn('--source device|local', bad.stdout)
        no_zip = self.run_cli('--source', 'device', '--symptom', '首页按钮点不动')
        self.assertIn('device-zip', no_zip.stdout)
        mixed = self.run_cli('--source', 'local', '--symptom', '首页按钮点不动')
        self.assertIn('belong to --source device', mixed.stdout)
        ok = self.run_cli('--source', 'device', '--device-zip', str(self.phone_zip), '--symptom', '首页按钮点不动',
                          '--phone-error', PHONE_LINE)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.assertEqual(json.loads(ok.stdout)['result']['payload']['device']['phone_error'], PHONE_LINE)


class OldProofs(Base):
    def test_proof_written_by_the_v78_checker_stays_valid_for_local_issues(self):
        issues.register(self.project, self.native, 'local-one', 'found on the computer', ['state.json'], self.local_cases,
                        self.runner)
        proof = issues.read_ref(issues.retest(self.project, self.native, 'local-one', self.tree('broken', False),
                                              self.normal, self.root / 'retest-local'))
        proof['checker_sha256'] = V78_CHECKER
        path = self.root / 'proof-v78.json'
        path.write_text(json.dumps(proof))
        issues.append(self.project, 'retested', {'id': 'local-one', 'proof': {'path': str(path), 'sha256': issues.sha(path)}})
        result = issues.audit(self.project, self.native)
        self.assertEqual([c['id'] for c in result['checked_issues']], ['local-one'])
        self.assertNotIn('device_issues', result)


if __name__ == '__main__':
    unittest.main(verbosity=1)

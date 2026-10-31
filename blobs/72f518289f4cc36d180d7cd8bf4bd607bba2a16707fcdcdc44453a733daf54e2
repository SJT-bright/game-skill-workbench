#!/usr/bin/env python3
"""v7.8 (总表 B32 a): supersede-by-design in the reported-issue gate (remake-core/scripts/package_issue_gate.py).

Saul changed the design, so an old issue's cases no longer apply: the issue for the new design is registered first, then
`supersede` records Saul's own words, the date and the new issue ID. Without any of the three (or with a new ID that is
not registered, the issue itself, or an issue that is itself superseded) it is refused, and a hand-written event like
that makes the whole ledger refuse. The old report stays in the history; the old issue stops blocking, the new one
blocks until its own retest passes. Proofs written by the v7 - v7.7.5 checker stay valid (same proof rules).
Run: python3 -B test_issue_supersede.py
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'remake-core' / 'scripts'))
import package_issue_gate as issues  # noqa: E402

QUOTE = '这个结算页改成两屏，原来的同屏用例不要了'
OLD_CHECKER = 'edaad58253327c1794e55b8b13154f9ce26b0d422d5c3b45d276bdd8c087ad2f'


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        issues.initialize(self.project)
        self.native, self.negative, self.normal = self.root / 'native', self.root / 'negative', self.root / 'normal'
        for path, delta in [(self.native, 1), (self.negative, 2), (self.normal, 1)]:
            path.mkdir()
            (path / 'state.json').write_text(json.dumps({'delta': delta}))
        self.runner = self.root / 'runner.py'
        self.runner.write_text("import argparse,json\nfrom pathlib import Path\np=argparse.ArgumentParser();p.add_argument('--native');"
                               "p.add_argument('--case');a=p.parse_args();print(json.dumps({'observed':json.loads((Path(a.native)/'state.json').read_text())}))\n")
        self.cases = [{'id': 'reward_once', 'assertions': [{'path': ['delta'], 'op': 'eq', 'value': 1}]}]
        issues.register(self.project, self.native, 'x2-same-screen', 'x2 和复活在同一屏', ['state.json'], self.cases, self.runner)

    def tearDown(self):
        self.temp.cleanup()

    def new_issue(self, name='x2-own-screen'):
        issues.register(self.project, self.native, name, '结算 x2 单独一屏', ['state.json'], self.cases, self.runner)

    def retest(self, name, out):
        return issues.retest(self.project, self.native, name, self.negative, self.normal, self.root / out)


class Supersede(Base):
    def test_old_issue_blocks_until_superseded_then_the_new_one_blocks(self):
        with self.assertRaisesRegex(ValueError, 'no passed retest: x2-same-screen'):
            issues.audit(self.project, self.native)
        self.new_issue()
        issues.supersede(self.project, 'x2-same-screen', 'x2-own-screen', QUOTE, '2026-10-30', '复活和 x2 分两屏')
        with self.assertRaisesRegex(ValueError, 'no passed retest: x2-own-screen'):
            issues.audit(self.project, self.native)
        self.retest('x2-own-screen', 'retest-new')
        result = issues.audit(self.project, self.native)
        self.assertEqual([c['id'] for c in result['checked_issues']], ['x2-own-screen'])
        self.assertEqual(result['superseded_issues'], [{'id': 'x2-same-screen', 'by': 'x2-own-screen', 'user_quote': QUOTE,
                                                        'date': '2026-10-30', 'reason': '复活和 x2 分两屏'}])
        events, _ = issues.load(self.project)
        self.assertEqual(events[1]['payload']['message'], 'x2 和复活在同一屏')       # the old report is kept

    def test_without_quote_date_or_registered_new_issue_refused(self):
        with self.assertRaisesRegex(ValueError, 'not registered'):
            issues.supersede(self.project, 'x2-same-screen', 'x2-own-screen', QUOTE, '2026-10-30')
        self.new_issue()
        for quote, date, why in (('', '2026-10-30', 'own words'), ('  ok ', '2026-10-30', 'own words'),
                                 (QUOTE, '', 'YYYY-MM-DD'), (QUOTE, '10/30', 'YYYY-MM-DD'), (QUOTE, '2026-02-30', 'YYYY-MM-DD'),
                                 (QUOTE, '2999-01-01', 'future')):
            with self.assertRaisesRegex(ValueError, why):
                issues.supersede(self.project, 'x2-same-screen', 'x2-own-screen', quote, date)
        with self.assertRaisesRegex(ValueError, 'cannot supersede itself'):
            issues.supersede(self.project, 'x2-same-screen', 'x2-same-screen', QUOTE, '2026-10-30')
        with self.assertRaisesRegex(ValueError, 'unknown'):
            issues.supersede(self.project, 'nope', 'x2-own-screen', QUOTE, '2026-10-30')
        with self.assertRaisesRegex(ValueError, 'no passed retest: x2-same-screen'):
            issues.audit(self.project, self.native)                       # nothing was recorded

    def test_superseded_issue_cannot_be_retested_or_superseded_again(self):
        self.new_issue()
        self.new_issue('third')
        issues.supersede(self.project, 'x2-same-screen', 'x2-own-screen', QUOTE, '2026-10-30')
        with self.assertRaisesRegex(ValueError, 'superseded by x2-own-screen'):
            self.retest('x2-same-screen', 'retest-old')
        with self.assertRaisesRegex(ValueError, 'already superseded'):
            issues.supersede(self.project, 'x2-same-screen', 'third', QUOTE, '2026-10-30')
        with self.assertRaisesRegex(ValueError, 'itself superseded'):
            issues.supersede(self.project, 'third', 'x2-same-screen', QUOTE, '2026-10-30')
        issues.supersede(self.project, 'x2-own-screen', 'third', '再改：一屏只一个看广告按钮', '2026-10-31')   # a chain is fine

    def test_hand_written_event_without_the_words_makes_the_ledger_refuse(self):
        self.new_issue()
        issues.append(self.project, 'superseded', {'id': 'x2-same-screen', 'by': 'x2-own-screen', 'user_quote': '',
                                                   'date': '2026-10-30', 'reason': ''})
        with self.assertRaisesRegex(ValueError, 'invalid supersede-by-design event'):
            issues.audit(self.project, self.native)

    def test_cli(self):
        self.new_issue()
        script = HERE.parents[2] / 'remake-core' / 'scripts' / 'package_issue_gate.py'
        base = [sys.executable, '-B', str(script), 'supersede', '--project', str(self.project), '--id', 'x2-same-screen',
                '--by', 'x2-own-screen', '--date', '2026-10-30']
        bad = subprocess.run(base, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertIn('own words', bad.stdout)
        ok = subprocess.run(base + ['--quote', QUOTE, '--message', '分两屏'], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.assertEqual(json.loads(ok.stdout)['result']['payload']['user_quote'], QUOTE)


class OldProofs(Base):
    """A Skill update must not make every game retest its closed issues: proofs of the v7 - v7.7.5 checker stay valid."""

    def rewrite_checker(self, checker):
        ref = self.retest('x2-same-screen', 'retest-%s' % checker[:6])
        proof = issues.read_ref(ref)
        proof['checker_sha256'] = checker
        path = self.root / ('proof-%s.json' % checker[:6])
        path.write_text(json.dumps(proof))
        issues.append(self.project, 'retested', {'id': 'x2-same-screen', 'proof': {'path': str(path), 'sha256': issues.sha(path)}})

    def test_previous_checker_accepted_other_refused(self):
        self.rewrite_checker(OLD_CHECKER)
        self.assertTrue(issues.audit(self.project, self.native)['passed'])
        self.rewrite_checker('0' * 64)
        with self.assertRaisesRegex(ValueError, 'checker changed'):
            issues.audit(self.project, self.native)


if __name__ == '__main__':
    unittest.main(verbosity=1)

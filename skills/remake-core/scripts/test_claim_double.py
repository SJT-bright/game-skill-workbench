#!/usr/bin/env python3
"""audit_claim_double.py (v7.8, Saul 2026-10-31): check-in / spin result / gift pack claim windows may carry one
"watch ad x2" checkbox, ticked by default; unticked CLAIM pays 1x for free. Two ad entries or "must watch to claim"
stay forbidden. Synthetic dumps in the chrome_touch dump_ui format."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_claim_double as A  # noqa: E402


def node(path, order, rect, **comps):
    return {'path': path, 'name': path.rsplit('/', 1)[-1], 'order': order, 'rect': rect, 'opacity': 1, 'comps': comps}


def label(s):
    return {'string': s, 'fontSize': 28}


def sprite(frame):
    return {'frame': frame}


def btn():
    return {'interactable': True, 'enabled': True}


def home_under_modal():
    """The home page behind the popup: its own gift box video button must not count."""
    return [node('Canvas/Home', 1, [0, 0, 1, 1], sprite=sprite('home_bg')),
            node('Canvas/Home/Gift', 2, [0.05, 0.3, 0.15, 0.08], button=btn(), sprite=sprite('gift_00')),
            node('Canvas/Home/Gift/Video', 3, [0.05, 0.3, 0.05, 0.03], sprite=sprite('icon_video')),
            node('Canvas/Modal', 10, [0, 0, 1, 1], block_input=True)]


def checkin(ticked=True, extra_ad=False, claim_frame='btn_claim', checkbox=True, claim=True, purpose='checkin'):
    n = home_under_modal() + [node('Canvas/Modal/Panel', 11, [0.1, 0.2, 0.8, 0.6], sprite=sprite('panel_daily'))]
    if checkbox:
        n += [node('Canvas/Modal/Panel/DoubleToggle', 20, [0.2, 0.62, 0.08, 0.04], button=btn(), sprite=sprite('checkbox_bg')),
              node('Canvas/Modal/Panel/DoubleToggle/Label', 21, [0.3, 0.62, 0.3, 0.04], label=label('Watch ad x2'))]
        mark = node('Canvas/Modal/Panel/DoubleToggle/checkmark', 22, [0.2, 0.62, 0.08, 0.04])
        if ticked:
            mark['comps']['sprite'] = sprite('checkmark')
        n.append(mark)
    if claim:
        n += [node('Canvas/Modal/Panel/Claim', 30, [0.3, 0.7, 0.4, 0.07], button=btn(), sprite=sprite(claim_frame))]
    if extra_ad:
        n += [node('Canvas/Modal/Panel/WatchAd', 40, [0.3, 0.78, 0.4, 0.07], button=btn(), sprite=sprite('btn_watch_ad'))]
    return {'tool': 'ui_dump', 'producer': 'chrome_touch.dump_ui', 'schema': 1, 'purpose': purpose, 'nodes': n}


class ClaimDouble(unittest.TestCase):
    def run_audit(self, *dumps):
        for i, d in enumerate(dumps):
            d.setdefault('_file', '%03d-ui-dump-%s.json' % (i, d.get('purpose')))
        return A.audit(list(dumps))

    def test_ticked_checkbox_with_claim_passes(self):
        rows, problems = self.run_audit(checkin())
        self.assertEqual(problems, [])
        self.assertEqual(rows[0]['checkboxes'], ['Canvas/Modal/Panel/DoubleToggle'])
        self.assertEqual(rows[0]['ticked'], rows[0]['checkboxes'])
        self.assertNotIn('Canvas/Home/Gift', rows[0]['ad_entries'])          # covered home page not counted

    def test_claim_with_video_icon_next_to_checkbox_is_the_free_claim(self):
        """64 MusicSlice: CLAIM shows a video icon while the box is ticked; unticked it pays 1x for free."""
        rows, problems = self.run_audit(checkin(claim_frame='btn_claim_video'))
        self.assertEqual(problems, [])
        self.assertEqual(rows[0]['free_claim'], ['Canvas/Modal/Panel/Claim'])

    def test_spin_result_and_gift_pack_use_the_same_rule(self):
        for purpose in ('wheel_result', 'spin_result', 'gift_pack'):
            self.assertEqual(self.run_audit(checkin(purpose=purpose))[1], [], purpose)

    def test_two_ad_entries_refused(self):
        problems = self.run_audit(checkin(extra_ad=True))[1]
        self.assertTrue(any(p.startswith('claim_two_ads:') for p in problems), problems)

    def test_must_watch_to_claim_refused(self):
        d = checkin(checkbox=False, claim=False, extra_ad=True)
        problems = self.run_audit(d)[1]
        self.assertTrue(any(p.startswith('claim_ad_only:') for p in problems), problems)

    def test_checkbox_without_claim_refused(self):
        problems = self.run_audit(checkin(claim=False))[1]
        self.assertTrue(any(p.startswith('claim_no_claim:') for p in problems), problems)

    def test_unticked_by_default_refused_unless_some_dump_shows_it_ticked(self):
        problems = self.run_audit(checkin(ticked=False))[1]
        self.assertTrue(any(p.startswith('claim_double_unchecked:') for p in problems), problems)
        self.assertEqual(self.run_audit(checkin(ticked=True), checkin(ticked=False))[1], [])   # opened ticked, then unticked

    def test_old_designs_still_pass(self):
        """No ad entry on the check-in (v7.7.5 default) and the x2 button + free Claim link pair both pass."""
        self.assertEqual(self.run_audit(checkin(checkbox=False))[1], [])
        d = checkin(checkbox=False, claim=False, extra_ad=True)
        d['nodes'].append(node('Canvas/Modal/Panel/LinkClaim', 50, [0.4, 0.86, 0.2, 0.04], button=btn(), sprite=sprite('link_claim')))
        self.assertEqual(self.run_audit(d)[1], [])

    def test_home_gift_box_popup_is_not_a_claim_screen(self):
        """Home gift box: watch ad -> 5B, no checkbox (Saul 10-31: unchanged)."""
        d = checkin(checkbox=False, claim=False, extra_ad=True, purpose='gift')
        self.assertEqual(self.run_audit(d), ([], []))

    def test_cli(self):
        with tempfile.TemporaryDirectory(prefix='claim double ') as tmp:
            root = Path(tmp)
            (root / 'docs' / 'test').mkdir(parents=True)
            (root / 'docs' / 'test' / '001-ui-dump-checkin.json').write_text(json.dumps(checkin(ticked=False)))
            out = root / 'report.json'
            r = subprocess.run([sys.executable, '-B', str(HERE / 'audit_claim_double.py'), '--project', str(root), '--out', str(out)],
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 1, r.stderr)
            self.assertIn('claim_double_unchecked', json.loads(out.read_text())['problems'][0])
            (root / 'docs' / 'test' / '001-ui-dump-checkin.json').write_text(json.dumps(checkin()))
            r = subprocess.run([sys.executable, '-B', str(HERE / 'audit_claim_double.py'), '--project', str(root), '--out', str(out)],
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main()

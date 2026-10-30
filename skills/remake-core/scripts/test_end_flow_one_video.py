#!/usr/bin/env python3
"""One video button per end screen (D8 item 4, user 2026-10-28): 方块迷阵 v6 put the revive WATCH AD and the result
WATCH AD x2 in one end popup; v6.1 splits it into a revive page and a result page."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_page_richness as audit  # noqa: E402


def btn(path, rect, label='', frame='main/bnt01'):
    nodes = [{'name': path.rsplit('/', 1)[-1], 'path': path, 'rect': rect, 'comps': {'button': {'interactable': True},
                                                                                       'sprite': {'frame': frame}}}]
    if label:
        nodes.append({'name': path.rsplit('/', 1)[-1] + 'Label', 'path': path + '/Label', 'rect': rect,
                      'comps': {'label': {'string': label}}})
    return nodes


ROOT = 'Canvas/RankSmallDlgs/dlgContent/'
# shapes taken from 方块迷阵 RankSmallDlgs.ts (v6: one popup, v6.1: two steps)
V6_END = (btn(ROOT + 'ReviveWatchAd', [0.2, 0.55, 0.6, 0.08], 'WATCH AD') +
          btn(ROOT + 'DoubleWatchAd', [0.2, 0.65, 0.6, 0.09], 'WATCH AD x2') +
          btn(ROOT + 'Restart', [0.2, 0.76, 0.28, 0.06], 'RESTART') + btn(ROOT + 'Home', [0.52, 0.76, 0.28, 0.06], 'HOME'))
V61_REVIVE = btn(ROOT + 'ReviveWatchAd', [0.2, 0.55, 0.6, 0.08], 'WATCH AD') + btn(ROOT + 'NoThanks', [0.35, 0.66, 0.3, 0.04], 'NO THANKS')
V61_RESULT = (btn(ROOT + 'DoubleWatchAd', [0.2, 0.6, 0.6, 0.09], 'WATCH AD x2') +
              btn(ROOT + 'Restart', [0.2, 0.72, 0.28, 0.06], 'RESTART') + btn(ROOT + 'Home', [0.52, 0.72, 0.28, 0.06], 'HOME'))


def run(purpose, nodes):
    return audit.video_button_problems(purpose, nodes, nodes)


class OneVideoPerScreen(unittest.TestCase):
    def test_v6_end_popup_fails_whatever_its_purpose(self):
        for purpose in ('result_fail', 'revive', 'other'):
            p = run(purpose, V6_END)
            self.assertEqual(len(p), 1, (purpose, p))
            self.assertTrue(p[0].startswith('two_video_buttons:'))
            self.assertIn('ReviveWatchAd=revive', p[0])
            self.assertIn('DoubleWatchAd=x2', p[0])

    def test_v61_two_steps_pass(self):
        self.assertEqual(run('revive', V61_REVIVE), [])
        self.assertEqual(run('result_fail', V61_RESULT), [])

    def test_two_plain_video_buttons_on_an_end_page_fail(self):
        nodes = btn(ROOT + 'BtnWatchAd', [0.2, 0.6, 0.6, 0.08], 'WATCH AD') + btn(ROOT + 'BtnVideoSkin', [0.2, 0.7, 0.6, 0.08], '', 'btn_video_skin')
        self.assertTrue(run('result_win', nodes))
        self.assertEqual(run('home', nodes), [])        # other pages: only revive + x2 together is refused

    def test_claim_link_and_add_to_home_are_not_videos(self):
        nodes = V61_RESULT + btn(ROOT + 'LinkClaim', [0.4, 0.70, 0.2, 0.02], '', 'link_claim') + \
            btn(ROOT + 'BtnAddToHome', [0.1, 0.9, 0.1, 0.05], 'ADD TO HOME') + btn(ROOT + 'BtnShadow', [0.8, 0.9, 0.1, 0.05])
        self.assertEqual(run('result_win', nodes), [])

    def test_through_check(self):
        d = {'kind': 'popup', 'purpose': 'result_fail', 'nodes': V6_END, '_file': '/nonexistent/ui-dump-end.json'}
        problems, _ = audit.check(d)
        self.assertTrue(any(x.startswith('two_video_buttons:') for x in problems), problems)
        d = {'kind': 'popup', 'purpose': 'result_fail', 'nodes': V61_RESULT, '_file': '/nonexistent/ui-dump-end.json'}
        problems, _ = audit.check(d)
        self.assertFalse(any(x.startswith('two_video_buttons:') for x in problems), problems)


if __name__ == '__main__':
    unittest.main()

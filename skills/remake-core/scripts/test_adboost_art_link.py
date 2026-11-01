#!/usr/bin/env python3
"""Saul 2026-11-01 「广告skill做新的转盘的时候，你就要去做这个转盘的美工」: ad-boost boards copied into a game must
reach the art Skill. (1) their pictures need generation records (art_records H10); (2) their panels must be dumped at
two phone sizes so the page checks run on them (art_check capture_inventory); (3) the page check knows their pages."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import art_check            # noqa: E402

PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x08\x00\x00\x00\x08\x08\x06\x00\x00\x00\xc4\x0f\xbe\x8b'
       b'\x00\x00\x00\x0bIDATx\x9cc`\x18\x05\x00\x00\x00\x08\x00\x01\xd3\x17\x9c\xab\x00\x00\x00\x00IEND\xaeB`\x82')
VIEWPORTS = [{'name': 'a', 'width': 390, 'height': 844}, {'name': 'b', 'width': 375, 'height': 667}]


class AdBoostCapture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / 'project'
        (self.project / 'docs' / 'art').mkdir(parents=True)
        self.dumps = self.project / 'docs' / 'test'
        self.dumps.mkdir()
        self.screens = [{'id': 'home', 'name': 'Home'}, {'id': 'play', 'name': 'Play'}]
        self.write_manifest()
        for screen in ('home', 'play'):
            for i, vp in enumerate(VIEWPORTS):
                self.dump(screen, i, vp, ['bg_home'] if screen == 'home' else ['tile'])

    def tearDown(self):
        self.tmp.cleanup()

    def write_manifest(self):
        (self.project / 'docs/art/screens.json').write_text(json.dumps(
            {'runtime_verified': True, 'screens': self.screens, 'required_viewports': VIEWPORTS}))

    def dump(self, screen, i, vp, frames):
        shot = '%s-ui-shot-%d.png' % (screen, i)
        (self.dumps / shot).write_bytes(b'fixture')
        nodes = [{'path': 'Canvas/%s/%s' % (screen, f), 'opacity': 1, 'rect': [0.2, 0.2, 0.3, 0.2],
                  'comps': {'sprite': {'frame': f}}} for f in frames]
        (self.dumps / ('%s-ui-dump-%d.json' % (screen, i))).write_text(json.dumps(
            {'screen': screen, 'kind': 'gameplay' if screen == 'play' else 'page', 'viewport': vp, 'screenshot': shot,
             'nodes': nodes}))

    def add_board(self, board, names):
        d = self.project / 'assets' / 'resources' / 'adboost' / board
        d.mkdir(parents=True, exist_ok=True)
        for n in names:
            (d / (n + '.png')).write_bytes(PNG)

    def errors(self):
        return art_check.capture_inventory(self.project, self.dumps)['errors']

    def test_game_without_adboost_is_unchanged(self):
        self.assertEqual(self.errors(), [])

    def test_unrecorded_adboost_pictures_name_the_record_step(self):
        import art_records
        self.add_board('wheel', ['wheel_disc', 'btn_spin'])
        for f in (self.project / 'assets/resources/adboost/wheel').glob('*.png'):
            Path(str(f) + '.meta').write_text(json.dumps({'ver': '2.3.7', 'uuid': 'u-' + f.stem, 'subMetas': {}}))
        (self.project / 'docs/art/base-assets.json').write_text(json.dumps(
            {'kind': 'base-assets', 'schema': 1, 'base': 'none', 'why': 'made from scratch'}))
        (self.project / 'docs/board.txt').write_text('remake\n')
        res = art_records.check_generated(self.project, 'remake')
        self.assertFalse(res['ok'])
        self.assertEqual(res.get('adboost_boards'), ['wheel'])
        self.assertIn('skill_link.py record', res['message'])

    def test_wheel_pictures_never_dumped_block_the_art_check(self):
        self.add_board('wheel', ['wheel_disc', 'btn_spin', 'panel_result'])
        errs = self.errors()
        self.assertEqual(len(errs), 1, errs)
        self.assertIn('wheel', errs[0])
        self.assertIn('没有出现在任何页面采集里', errs[0])

    def test_wheel_dumped_at_one_size_only_is_still_missing(self):
        self.add_board('wheel', ['wheel_disc', 'btn_spin'])
        self.screens.append({'id': 'wheel', 'name': 'Lucky spin', 'purpose': 'wheel'})
        self.write_manifest()
        self.dump('wheel', 0, VIEWPORTS[0], ['wheel_disc', 'btn_spin'])
        errs = [e for e in self.errors() if 'ad-boost' in e]
        self.assertEqual(len(errs), 1, errs)
        self.assertIn('390x844', errs[0])

    def test_wheel_dumped_at_both_sizes_passes_and_shared_art_is_skipped(self):
        self.add_board('wheel', ['wheel_disc', 'btn_spin'])
        self.add_board('shared', ['check_box', 'check_tick'])        # shared kit art is drawn inside the boards
        self.screens.append({'id': 'wheel', 'name': 'Lucky spin', 'purpose': 'wheel'})
        self.write_manifest()
        for i, vp in enumerate(VIEWPORTS):
            self.dump('wheel', i, vp, ['wheel_disc', 'btn_spin'])
        self.assertEqual(self.errors(), [])

    def test_frame_names_match_case_insensitively_and_hidden_nodes_do_not_count(self):
        self.add_board('gift', ['gift_panel'])
        self.screens.append({'id': 'gift', 'name': 'Gift', 'purpose': 'gift'})
        self.write_manifest()
        self.dump('gift', 0, VIEWPORTS[0], ['Gift_Panel'])
        hidden = json.loads((self.dumps / 'gift-ui-dump-0.json').read_text())
        hidden['viewport'] = VIEWPORTS[1]
        hidden['nodes'][0]['opacity'] = 0
        (self.dumps / 'gift-ui-shot-1.png').write_bytes(b'fixture')
        hidden['screenshot'] = 'gift-ui-shot-1.png'
        (self.dumps / 'gift-ui-dump-1.json').write_text(json.dumps(hidden))
        errs = [e for e in self.errors() if 'ad-boost' in e]
        self.assertEqual(len(errs), 1, errs)                    # only the 390x844 one is visible


def adboost_checkin_nodes(with_rewards=True):
    """Nodes like ad-boost CheckinPanel.js: Day1..Day7, card picture Bg, DayLabel picture, digits, Rewards/coins, CLAIM."""
    nodes = [{'path': 'Canvas/AdBoostCheckinPopup', 'name': 'AdBoostCheckinPopup', 'id': 'p', 'depth': 1, 'order': 1,
              'opacity': 1, 'rect': [0, 0, 1, 1], 'comps': {'block_input': True}},
             {'path': 'Canvas/AdBoostCheckinPopup/Body', 'name': 'Body', 'id': 'b', 'depth': 2, 'order': 2, 'opacity': 1,
              'rect': [0.07, 0.15, 0.86, 0.7], 'comps': {'sprite': {'frame': 'checkin_panel'}}}]
    o = 3
    for i in range(7):
        big = i == 6
        x, y = (0.12, 0.62) if big else (0.12 + (i % 3) * 0.26, 0.25 + (i // 3) * 0.18)
        w, h = (0.76, 0.16) if big else (0.24, 0.16)
        root = 'Canvas/AdBoostCheckinPopup/Body/Day%d' % (i + 1)
        nodes.append({'path': root, 'name': 'Day%d' % (i + 1), 'id': 'd%d' % i, 'depth': 3, 'order': o, 'opacity': 1,
                      'rect': [x, y, w, h], 'comps': {}})
        nodes.append({'path': root + '/Bg', 'name': 'Bg', 'id': 'g%d' % i, 'depth': 4, 'order': o + 1, 'opacity': 1,
                      'rect': [x, y, w, h], 'comps': {'sprite': {'frame': 'cell_big' if big else 'cell_bg'}}})
        nodes.append({'path': root + '/DayLabel', 'name': 'DayLabel', 'id': 'l%d' % i, 'depth': 4, 'order': o + 2,
                      'opacity': 1, 'rect': [x + 0.02, y + 0.01, w * 0.4, 0.03], 'comps': {'sprite': {'frame': 'day_label'}}})
        if with_rewards:
            nodes.append({'path': root + '/Rewards/Coin', 'name': 'Coin', 'id': 'r%d' % i, 'depth': 5, 'order': o + 3,
                          'opacity': 1, 'rect': [x + w * 0.25, y + h * 0.3, w * 0.5, h * 0.5],
                          'comps': {'sprite': {'frame': 'item_coins'}}})
        o += 4
    nodes.append({'path': 'Canvas/AdBoostCheckinPopup/Body/Claim', 'name': 'Claim', 'id': 'c', 'depth': 3, 'order': o,
                  'opacity': 1, 'rect': [0.3, 0.8, 0.4, 0.07],
                  'comps': {'button': {'interactable': True}, 'sprite': {'frame': 'btn_claim'}}})
    return nodes                                   # ancestors come from depth, as in a real dump without ancestor_ids


class AdBoostCheckin(unittest.TestCase):
    def check(self, nodes):
        import audit_page_richness as apr
        d = {'kind': 'popup', 'purpose': 'checkin', 'canvas_css': [0, 0, 390, 844], 'nodes': nodes,
             '_file': str(Path(tempfile.gettempdir()) / 'none-ui-dump-checkin.json')}
        problems, _ = apr.check(d, None, None)
        return [p for p in problems if p.startswith('checkin_page')]

    def test_adboost_checkin_panel_passes_the_checkin_page_check(self):
        self.assertEqual(self.check(adboost_checkin_nodes()), [])

    def test_adboost_checkin_panel_without_rewards_is_still_caught(self):
        probs = self.check(adboost_checkin_nodes(with_rewards=False))
        self.assertEqual(len(probs), 1, probs)
        self.assertIn('no visible reward content', probs[0])


class AdBoostPurposes(unittest.TestCase):
    def test_page_check_knows_the_adboost_pages(self):
        import audit_page_richness as apr
        for purpose in ('wheel', 'gift', 'offline', 'energy', 'hint', 'coin_ad', 'quest', 'bonus_level', 'shop_free',
                        'prestart_boost', 'booster_refill', 'skin_ad'):
            self.assertIn(purpose, apr.ADBOOST_PURPOSES)
        self.assertTrue({'checkin', 'trial', 'revive'} <= set(apr.FUNCTION_PAGES) | set(apr.OWN_POPUP_RULES))

    def test_wheel_page_without_wheel_parts_is_reported(self):
        import audit_page_richness as apr
        nodes = [{'path': 'Canvas/WheelPanel/panel', 'name': 'panel', 'opacity': 1, 'rect': [0.1, 0.2, 0.8, 0.6],
                  'comps': {'sprite': {'frame': 'panel_wheel'}}}]
        probs = apr.adboost_page_problems('wheel', nodes)
        self.assertEqual([p.split(':')[0] for p in probs], ['adboost_page'])
        self.assertIn('pointer', probs[0])
        nodes += [{'path': 'Canvas/WheelPanel/disc', 'name': 'disc', 'opacity': 1, 'rect': [0.2, 0.3, 0.6, 0.3],
                   'comps': {'sprite': {'frame': 'wheel_disc'}}},
                  {'path': 'Canvas/WheelPanel/pointer', 'name': 'pointer', 'opacity': 1, 'rect': [0.45, 0.28, 0.1, 0.06],
                   'comps': {'sprite': {'frame': 'wheel_pointer'}}},
                  {'path': 'Canvas/WheelPanel/spin', 'name': 'spin', 'opacity': 1, 'rect': [0.4, 0.4, 0.2, 0.1],
                   'comps': {'button': {'interactable': True}, 'sprite': {'frame': 'btn_spin'}}}]
        self.assertEqual(apr.adboost_page_problems('wheel', nodes), [])


if __name__ == '__main__':
    unittest.main()

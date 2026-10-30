#!/usr/bin/env python3
"""Tests for audit_ad_entry_reachability.py (v7.5, Germ2048 item 8.1). Run: python3 -B test_ad_entry_reachability.py"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_ad_entry_reachability as ad  # noqa: E402

UUID = '27cfc3cd-85c9-4962-e7ec-2fe22188a22a'
WRAPPER = ('export default class WeChatCom {\n    static async checkRewardedVideoAd(): Promise<boolean> {\n'
           '        const ad = wx.createRewardedVideoAd({adUnitId: "x"}); return await ad.show();\n    }\n}\n')
BUTTON = ('export default class VideoAwardButtonSc extends cc.Component {\n    onLoad() { this.node.active = true; }\n'
          '    async onclick_self() { if (await WeChatCom.checkRewardedVideoAd()) this.give(); }\n}\n')


def prefab(active):
    return json.dumps([
        {'__type__': 'cc.Prefab', 'data': {'__id__': 1}},
        {'__type__': 'cc.Node', '_name': 'ui Start', '_active': True, '_children': [{'__id__': 2}], '_components': []},
        {'__type__': 'cc.Node', '_name': 'btn_video', '_active': active, '_children': [], '_components': [{'__id__': 3}]},
        {'__type__': ad.compress(UUID)}])


def project(root, active, extra=None):
    files = {'assets/Script/wx/WeChatCom.ts': WRAPPER, 'assets/Script/VideoAwardButtonSc.ts': BUTTON,
             'assets/Script/VideoAwardButtonSc.ts.meta': json.dumps({'uuid': UUID}), 'assets/PreFab/ui Start.prefab': prefab(active)}
    files.update(extra or {})
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    return root


class AdEntry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_entry_saved_inactive_refused(self):
        r = ad.audit(project(self.root / 'a', False))
        self.assertEqual(r['status'], 'needs_fix', r)
        self.assertIn('btn_video', r['problems'][0])
        self.assertEqual(sorted(r['ad_scripts']), ['VideoAwardButtonSc'], 'the wrapper file is the layer, not an entry')

    def test_active_entry_passes(self):
        self.assertEqual(ad.audit(project(self.root / 'b', True))['status'], 'pass')

    def test_turned_on_by_another_script_passes(self):
        r = ad.audit(project(self.root / 'c', False, {'assets/Script/StartUISc.ts': 'show() { this.btn_video.active = true; }\n'}))
        self.assertEqual(r['status'], 'pass', r)

    def test_code_built_buttons_are_review_not_refusal(self):
        root = self.root / 'd'
        (root / 'assets' / 'Script').mkdir(parents=True)
        (root / 'assets' / 'Script' / 'Game.ts').write_text('onAd() { tt.createRewardedVideoAd({adUnitId: "x"}).show(); }\n')
        r = ad.audit(root)
        self.assertEqual(r['status'], 'review', r)

    def test_compressed_uuid(self):
        self.assertEqual(ad.compress('27cfc3cd-85c9-4962-e7ec-2fe22188a22a')[:5], '27cfc')
        self.assertEqual(len(ad.compress(UUID)), 23)


if __name__ == '__main__':
    unittest.main()

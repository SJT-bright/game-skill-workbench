#!/usr/bin/env python3
"""Tests for audit_share_entries.py (v7.5, Germ2048 item 7). Run: python3 -B test_share_entries.py"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_share_entries as share  # noqa: E402

WRAPPER = ('export default class WeChatCom {\n'
           '    static async Share(...args: any[]): Promise<boolean> {\n'
           '        UI.toast("Sharing rewards are unavailable on this platform.");\n        return false;\n    }\n}\n')
REVIVE = 'export class ReviveUISc { async onClaim() { let ret = await WeChatCom.Share(); if (ret) this.revive(); } }\n'


def project(root, files):
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    return root


class ShareEntries(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_germ_original_shape_refused(self):
        p = project(self.root / 'a', {'assets/Script/wx/WeChatCom.ts': WRAPPER, 'assets/Script/subUI/ReviveUISc.ts': REVIVE,
                                      'assets/Script/MainUISc.ts': 'onRank() { UI.toast("Leaderboard unavailable."); }\n'})
        r = share.audit(p)
        self.assertEqual(r['status'], 'needs_fix')
        text = ' '.join(r['problems'])
        self.assertIn('WeChatCom.ts:3', text)
        self.assertIn('MainUISc.ts:1', text)
        self.assertIn('ReviveUISc.ts:1', text)
        self.assertFalse(any('WeChatCom.ts:2' in x for x in r['problems']), 'the wrapper definition is not a call site')

    def test_recorded_conversion_passes(self):
        p = project(self.root / 'b', {'assets/Script/subUI/ReviveUISc.ts': REVIVE,
                                      'docs/fix.md': '| 复活 | 分享改成看完激励视频才复活 | `ReviveUISc` |\n'})
        self.assertEqual(share.audit(p)['status'], 'pass')

    def test_json_record_passes(self):
        p = project(self.root / 'c', {'assets/Script/subUI/ReviveUISc.ts': REVIVE, 'docs/share-entries.json': json.dumps(
            {'entries': [{'file': 'assets/Script/subUI/ReviveUISc.ts', 'decision': 'rewarded_video'}]})})
        self.assertEqual(share.audit(p)['status'], 'pass')

    def test_ordinary_error_messages_pass(self):
        p = project(self.root / 'd', {'assets/Script/Ads.ts': 'toast("Video unavailable. Please try again later.");\n'
                                                              'toast("Sharing is unavailable in this test build.");\n',
                                      'assets/Script/Mode.ts': 'label.string = "Coming soon";\n'})
        r = share.audit(p)
        self.assertEqual(r['status'], 'pass', r['problems'])
        self.assertTrue(r['review_text'], 'coming soon is listed for review')

    def test_prefab_label_refused(self):
        p = project(self.root / 'e', {'assets/ui.prefab': '[{"__type__": "cc.Label", "_N$string": "Invite friends is not available on TikTok"}]'})
        self.assertEqual(share.audit(p)['status'], 'needs_fix')


if __name__ == '__main__':
    unittest.main()

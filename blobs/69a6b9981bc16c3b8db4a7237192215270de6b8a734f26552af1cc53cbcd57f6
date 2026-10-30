#!/usr/bin/env python3
"""v7.7.4 (总表 B16): audit_dev_text tells a session how to fix the old platform-kit text.

A new game that copied the v7.7.3 kit holds MissionFlow.js / MissionFlow.plugin.js with
'LOCAL PREVIEW: open the game inside TikTok to use this.'. The kit file must not be edited by hand
(tiktok_finalize puts the kit bytes back), so the hit carries a hint to re-run the source step instead.
The same words in the game's own code are still a plain hit without that hint.
The kit itself passing the content checks is test_kit_passes_own_checks.py.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

import audit_dev_text as D

OLD_TEXT = "  preview: 'LOCAL PREVIEW: open the game inside TikTok to use this.'\n"


class OldKitTextHint(unittest.TestCase):
    def setUp(self):
        self.project = Path(tempfile.mkdtemp(prefix='dev_text_hint_')) / 'game'
        self.addCleanup(shutil.rmtree, self.project.parent, True)
        (self.project / 'assets' / 'tiktok-platform').mkdir(parents=True)

    def hits_for(self, name):
        (self.project / 'assets' / 'tiktok-platform' / name).write_text('var T = {\n' + OLD_TEXT + '};\n',
                                                                       encoding='utf-8')
        hits, _ = D.scan(self.project, True)
        return hits

    def test_old_kit_files_get_the_source_hint(self):
        for name in ('MissionFlow.js', 'MissionFlow.plugin.js'):
            with self.subTest(file=name):
                hits = self.hits_for(name)
                self.assertEqual(len(hits), 1, hits)
                self.assertIn('tiktok_finalize.py source', hits[0].get('hint', ''))
                (self.project / 'assets' / 'tiktok-platform' / name).unlink()

    def test_game_code_gets_a_plain_hit(self):
        hits = self.hits_for('GameUI.js')
        self.assertEqual(len(hits), 1, hits)
        self.assertNotIn('hint', hits[0])


if __name__ == '__main__':
    unittest.main()

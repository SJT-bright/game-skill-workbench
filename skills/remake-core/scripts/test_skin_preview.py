"""R4O2 (补查2 第 7 组, SLS35): skin previews use their own previewFrame, no slot frame, no Sprite.color tint."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# shaped after SLS35's SkinStore before its fix: one slot picture for every skin, skin = a colour on the whole node
SLS35_STORE = '''
    const frame = this.tileFrame; // TileIn.png
    preview.getComponent(cc.Sprite).spriteFrame = frame;
    previewNode.color = cc.color(skin.tint[0], skin.tint[1], skin.tint[2]);
    this.skinIcon.node.color = new cc.Color(255, 255, 255);   // reset is fine
    label.node.color = cc.Color.BLACK;                        // not a preview
'''


class SkinPreview(unittest.TestCase):
    def test_new_table_has_own_preview_field_per_row(self):
        from make_skin_table import make
        t = make(50, 'levels', 60, True, 'hero')
        rows = [r for r in t['items'] if r['group'] in ('skin', 'background')]
        self.assertTrue(rows and all('previewFrame' in r for r in rows))
        self.assertEqual(len({r['previewFrame'] for r in rows}), len(rows))

    def test_frozen_policy_table_unchanged(self):
        from make_skin_table import make
        from product_contract import ECONOMY_POLICIES, SKIN_POLICY
        old = [p for p in ECONOMY_POLICIES if p != SKIN_POLICY][0]
        t = make(50, 'levels', 60, True, 'hero', economy_policy=old)
        self.assertFalse(any('previewFrame' in r for r in t['items']))

    def test_table_checks(self):
        from check_skin_preview import check_table
        rows = [{'id': 'a', 'group': 'skin'},
                {'id': 'b', 'group': 'skin', 'previewFrame': 'TODO: x'},
                {'id': 'c', 'group': 'skin', 'previewFrame': 'textures/TileIn.png'},
                {'id': 'd', 'group': 'skin', 'previewFrame': 'skins/d.png'},
                {'id': 'e', 'group': 'skin', 'previewFrame': 'skins/d.png'},
                {'id': 'f', 'group': 'background', 'previewFrame': 'skins/bg_f.png'}]
        kinds = sorted((f['kind'], f['id']) for f in check_table({'items': rows}))
        self.assertEqual(kinds, [('missing_preview_frame', 'a'), ('preview_frame_todo', 'b'),
                                 ('shared_preview_frame', 'd'), ('shared_preview_frame', 'e'),
                                 ('slot_art_as_preview', 'c')])

    def test_tint_as_skin_in_source(self):
        from check_skin_preview import check_source
        found = check_source(SLS35_STORE, 'SkinStore.ts')
        self.assertEqual([f['kind'] for f in found], ['tint_as_skin'])
        self.assertIn('previewNode.color', found[0]['line'])

    def test_cli_boards(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'assets' / 'scripts'
            src.mkdir(parents=True)
            (src / 'SkinStore.ts').write_text(SLS35_STORE, encoding='utf-8')
            table = Path(tmp) / 'unlock_table.json'
            table.write_text(json.dumps({'items': [{'id': 'h', 'group': 'skin', 'previewFrame': 'skins/h.png'}]}))
            cmd = [sys.executable, str(HERE / 'check_skin_preview.py'), '--table', str(table), '--src', str(src)]
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 1)
            r = subprocess.run(cmd + ['--board', 'localize'], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(json.loads(r.stdout)['level'], 'warning')
            (src / 'SkinStore.ts').write_text('previewSprite.spriteFrame = skin.previewFrame;\n', encoding='utf-8')
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()

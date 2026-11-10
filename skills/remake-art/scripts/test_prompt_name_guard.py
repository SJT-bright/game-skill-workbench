"""R4O2 (Saul 2026-11-05): no game name in image prompts; title/logo pieces become protagonist/pattern slots."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def project(tmp, folder='1香吉士-射击高手2048', name='MergeShot2048', allow=None):
    p = Path(tmp) / folder
    (p / 'settings').mkdir(parents=True)
    (p / 'settings' / 'project.json').write_text(json.dumps({'name': name}), encoding='utf-8')
    if allow is not None:
        (p / 'docs' / 'copy').mkdir(parents=True)
        (p / 'docs' / 'copy' / 'glossary.json').write_text(json.dumps({'allow': allow}), encoding='utf-8')
    return p


class PromptNameGuard(unittest.TestCase):
    def test_names_from_folder_and_settings(self):
        import prompt_name_guard as g
        with tempfile.TemporaryDirectory() as tmp:
            names = g.game_names(project(tmp))
        self.assertIn('射击高手2048', names)
        self.assertIn('MergeShot2048', names)
        self.assertNotIn('香吉士', names)                  # owner prefix of the folder is not a game name

    def test_prompt_with_name_or_title_logo_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = project(tmp)
            prompts = Path(tmp) / 'prompts.json'
            prompts.write_text(json.dumps({'home_title': 'A glossy game title logo reading "Merge Shot 2048"',
                                           'btn_play': 'Soft flat button, word PLAY'}), encoding='utf-8')
            r = subprocess.run([sys.executable, str(HERE / 'prompt_name_guard.py'), '--project', str(p),
                                '--file', str(prompts)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            kinds = {h['kind'] for h in json.loads(r.stdout)['hits']}
            self.assertEqual(kinds, {'game_name_in_prompt', 'title_logo_request'})
            ok = subprocess.run([sys.executable, str(HERE / 'prompt_name_guard.py'), '--project', str(p), '--text',
                                 'Home hero: the cannon protagonist with flying number balls, no text; word PLAY'],
                                capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stdout)

    def test_glossary_allow_does_not_hide_the_name(self):
        """美工skill 11-05: the English flow writes the game name into glossary.json "allow" (spelling check), so that
        list must not exempt it (RocketMatch-English allow ["Rocket Match"] left no names at all)."""
        import prompt_name_guard as g
        with tempfile.TemporaryDirectory() as tmp:
            p = project(tmp, folder='RocketMatch-English', name='', allow=['Rocket Match', 'Star Quest'])
            self.assertEqual(g.game_names(p), ['RocketMatch'], 'OLD WAY BUG: glossary allow hid the game name')
            (p / 'docs' / 'game_name.json').write_text(json.dumps({'allow_in_prompts': ['Rocket Match']}),
                                                       encoding='utf-8')
            self.assertEqual(g.game_names(p), [])           # the dedicated key still exempts a look-alike word

    def test_names_from_glossary_game_name(self):
        """美工skill 11-05: 11.16 has sessions write docs/copy/glossary.json "game_name" (game_name_scan reads it); the
        prompt guard has to look for the same names, the Chinese one included."""
        import prompt_name_guard as g
        with tempfile.TemporaryDirectory() as tmp:
            p = project(tmp, folder='RocketMatch-English', name='', allow=['Rocket Match'])
            gl = p / 'docs' / 'copy' / 'glossary.json'
            gl.write_text(json.dumps({'game_name': ['火箭三消', 'Rocket Match'], 'allow': ['Rocket Match']}),
                          encoding='utf-8')
            names = g.game_names(p)
            self.assertIn('火箭三消', names, 'OLD WAY BUG: glossary game_name was not read')
            self.assertTrue(g.scan('A shiny 火箭三消 title picture with the rocket', names))
            gl.write_text(json.dumps({'game_name': 'Rocket Match'}), encoding='utf-8')   # a plain string works too
            self.assertTrue(g.scan('Big ROCKET MATCH letters', g.game_names(p)))

    def test_negated_title_words_pass(self):
        """美工skill 11-05: a prompt written to the rule ("no game name") was reported as asking for the game name."""
        import prompt_name_guard as g
        names = ['RocketMatch']
        for ok in ('Hero illustration for the home top slot (no game name, Saul 2026-11-05): toy rocket, sparkles',
                   'Home background pattern without the game title, soft clouds',
                   'Do not draw a title logo; the rocket protagonist fills the top half',
                   '首页上半屏放主角大图，不写游戏名',
                   'no title logo, no text'):
            self.assertEqual(g.scan(ok, names), [], ok)
        for bad in ('A glossy game title logo at the top',
                    'the game name in gold letters',
                    'no text, game logo in the middle',
                    'a logo with no outline: the game name in gold letters',
                    'Big ROCKET MATCH letters over the rocket'):
            self.assertTrue(g.scan(bad, names), bad)

    def test_absolute_paths_with_spaces_are_metadata_but_prompt_text_is_checked(self):
        import prompt_name_guard as g
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'prompts.json'
            data = {'mac': '/Volumes/Another User/SushiDash/art ref.png',
                    'win': r'D:\新电脑 游戏\其他账号\SushiDash\art ref.png',
                    'prompt': 'Draw SushiDash as a title logo'}
            config.write_text(json.dumps(data), encoding='utf-8')
            hits = g.scan_file(config, ['SushiDash'])
            self.assertTrue(hits)
            self.assertTrue(all(hit['where'].endswith('#2') for hit in hits))
            changes = []
            fixed = g._fix_data(data, ['SushiDash'], changes, 'test')
            self.assertEqual(fixed['mac'], data['mac'])
            self.assertEqual(fixed['win'], data['win'])
            self.assertNotIn('SushiDash', fixed['prompt'])

    def test_greybox_legend_has_no_game_name(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            p = project(tmp, folder='SushiDash', name='SushiDash')
            art = Path(tmp) / 'art'
            art.mkdir()
            Image.new('RGBA', (60, 30), (200, 0, 0, 255)).save(art / 'SushiDash_title.png')
            Image.new('RGBA', (40, 40), (0, 200, 0, 255)).save(art / 'btn_play.png')
            Image.new('RGBA', (40, 40), (0, 0, 200, 255)).save(art / 'logo.png')
            out = Path(tmp) / 'ref.png'
            r = subprocess.run([sys.executable, str(HERE / 'make_greybox_reference.py'), '--folder', str(art), '--out',
                                str(out), '--project', str(p)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            legend = json.loads(Path(str(out) + '.json').read_text(encoding='utf-8'))
        text = json.dumps(legend, ensure_ascii=False)
        self.assertNotIn('SushiDash', text.replace(str(art), '').replace(str(Path(tmp)), ''))
        slots = [row for row in legend['items'] if row.get('title_slot')]
        self.assertEqual(len(slots), 2)                     # SushiDash_title.png and logo.png
        self.assertIn('btn_play.png', [row['name'] for row in legend['items']])
        self.assertIn('prompt_rule', legend)


if __name__ == '__main__':
    unittest.main()

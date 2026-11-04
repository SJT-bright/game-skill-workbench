#!/usr/bin/env python3
"""简化.11.3 audit_sound_settings_static.py schema 3 (CubeDigits 11-02 audio requirements, step 1).

  - sound controls but no audio file -> fail (case 2, CubeDigits 3.7.1 / NorisTidePins shape)
  - sound controls and audio files but only volume / save code, no play call -> fail (cases 1 and 12)
  - review is never passed (requirement 3.4) and preflight's final stage makes it 需处理
  - not_applicable only with docs/audio/silent_design.md AND no sound signal; a record that contradicts sound -> fail
  - no sound and no record -> review, not a silent pass
  - a complete game passes; the Germ2048 shape stays fail
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_audit_sound_settings_static.py"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_sound_settings_static as A  # noqa: E402

SETTINGS = ("export class Settings { musicVolume = 10; sfxVolume = 10;\n"
            "  save() { localStorage.setItem('musicVolume', String(this.musicVolume)); } }\n")
PLAYER = ("import { AudioSource } from 'cc';\n"
          "export class Sound { bgm: AudioSource = null;\n"
          "  start() { this.bgm.loop = true; this.bgm.play(); }\n"
          "  sfx(clip) { this.bgm.playOneShot(clip, 1); }\n"
          "  playMusic(c) { this.bgm.clip = c; this.bgm.play(); } }\n")


def project(files):
    root = Path(tempfile.mkdtemp(prefix='sound_static_'))
    (root / 'assets').mkdir()
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            p.write_bytes(text)
        else:
            p.write_text(text, encoding='utf-8')
    return root


class Status(unittest.TestCase):
    def test_complete_game_passes(self):
        r = A.audit(project({'assets/scripts/Settings.ts': SETTINGS, 'assets/scripts/Sound.ts': PLAYER,
                             'assets/audio/bgm.mp3': b'ID3', 'assets/audio/click.mp3': b'ID3'}))
        self.assertEqual((r['status'], r['passed'], r['applicable']), ('pass', True, True), r)

    def test_controls_without_audio_file_fail(self):
        r = A.audit(project({'assets/scripts/Settings.ts': SETTINGS, 'assets/scripts/Sound.ts': PLAYER}))
        self.assertEqual((r['status'], r['passed']), ('fail', False))
        self.assertIn('no audio file', r['problems'][0])

    def test_controls_and_audio_but_nothing_plays_fail(self):
        r = A.audit(project({'assets/scripts/Settings.ts': SETTINGS + 'this.bgm.volume = 0.5; this.playing = true;\n',
                             'assets/audio/bgm.mp3': b'ID3'}))
        self.assertEqual((r['status'], r['passed']), ('fail', False))
        self.assertIn('nothing plays them', r['problems'][0])

    def test_review_is_never_passed(self):
        # one music volume only: a gap that stays review, and review is not a pass
        r = A.audit(project({'assets/scripts/Sound.ts': PLAYER + 'let musicVolume = 1;\n', 'assets/audio/bgm.mp3': b'ID3'}))
        self.assertEqual(r['status'], 'review')
        self.assertFalse(r['passed'])

    def test_no_sound_and_no_record_is_review(self):
        r = A.audit(project({'assets/scripts/Game.ts': 'export const score = 0;\n'}))
        self.assertEqual((r['status'], r['passed'], r['applicable']), ('review', False, False))
        self.assertIn('silent_design.md', r['review'][0])

    def test_silent_record_without_sound_is_not_applicable(self):
        r = A.audit(project({'assets/scripts/Game.ts': 'export const score = 0;\n',
                             'docs/audio/silent_design.md': 'The game has no sound by design.\n'}))
        self.assertEqual((r['status'], r['passed']), ('not_applicable', True))

    def test_silent_record_contradicted_by_controls_fails(self):
        r = A.audit(project({'assets/scripts/Settings.ts': SETTINGS, 'assets/scripts/Sound.ts': PLAYER,
                             'assets/audio/bgm.mp3': b'ID3', 'docs/audio/silent_design.md': 'silent\n'}))
        self.assertEqual(r['status'], 'fail')
        self.assertIn('says the game is silent', r['problems'][0])

    def test_scene_label_is_a_control(self):
        r = A.audit(project({'assets/scene/Home.scene': json.dumps([{'__type__': 'cc.Label', '_string': 'Music'}])}))
        self.assertEqual(r['status'], 'fail')
        self.assertTrue(r['signals']['controls'])

    def test_germ2048_shape_stays_fail(self):
        r = A.audit(project({'assets/scripts/Menu.ts': 'let soundOn = true; function toggle(){ soundOn = !soundOn; }\n',
                             'assets/audio/click.mp3': b'ID3',
                             'assets/scripts/Sfx.ts': "cc.audioEngine.playEffect(clip, false);\n"}))
        self.assertEqual(r['status'], 'fail')

    def test_exit_codes(self):
        bad = project({'assets/scripts/Settings.ts': SETTINGS})
        silent = project({'assets/scripts/Game.ts': 'export const score = 0;\n', 'docs/audio/silent_design.md': 'x'})
        run = lambda p: subprocess.run([sys.executable, '-B', str(HERE / 'audit_sound_settings_static.py'), '--project',
                                        str(p)], capture_output=True, text=True).returncode
        self.assertEqual(run(bad), 1)
        self.assertEqual(run(silent), 0)


class Preflight(unittest.TestCase):
    def test_preflight_row_review_is_todo_at_final_stage(self):
        text = (HERE / 'preflight.py').read_text(encoding='utf-8')
        row = text[text.index("tool_row('声音设置'"):text.index("lc_args = ")]
        self.assertIn("('需处理' if a.stage == 'final' else '提示')", row)
        self.assertIn("in ('fail', 'needs_fix')", row)
        self.assertIn("'不适用'", row)


if __name__ == '__main__':
    unittest.main()

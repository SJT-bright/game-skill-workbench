#!/usr/bin/env python3
"""The platform kit must pass the Skill's own content checks (235 WynnsFireflyMeadow, 2026-10-30).

remake-game says "copy the kit unchanged", and tiktok_finalize puts the kit bytes back in every new game
(tiktok_finalize_steps/kit_sources.py). So a kit file that a content check rejects fails every game that follows
the rules, and no game session can fix it: v7.7.3 MissionFlow.js:39 / MissionFlow.plugin.js:58 showed
'LOCAL PREVIEW: ...' in the browser, which audit_dev_text.py rejects as developer wording.

This test copies the kit into a temporary project the way a game gets it (assets/ as is, the 3.x plugins into
assets/tiktok-platform/) and runs the project-level content checks on it. A new content check that games must pass
belongs in CHECKS. The negative control proves the test still catches the v7.7.3 text.

    python3 -m unittest test_kit_passes_own_checks
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent / 'assets' / 'platform-kit'
OLD_PREVIEW = "LOCAL PREVIEW: open the game inside TikTok to use this."

# (script, extra arguments); {p} is the project folder. Each must exit 0 on the kit.
CHECKS = [
    ('audit_dev_text.py', ['--project', '{p}', '--final']),
    ('audit_no_social_features.py', ['--project', '{p}']),
    ('audit_share_entries.py', ['--project', '{p}', '--docs', '{p}/docs']),
]


def kit_project(root):
    project = Path(root) / 'game'
    shutil.copytree(KIT / 'assets', project / 'assets')
    target = project / 'assets' / 'tiktok-platform'
    for plugin in sorted((KIT / 'plugins-3x').glob('*.plugin.js')):
        shutil.copy2(plugin, target / plugin.name)
    (project / 'docs').mkdir()
    return project


def run(script, args, project):
    cmd = [sys.executable, '-B', str(HERE / script)] + [a.replace('{p}', str(project)) for a in args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


class KitPassesOwnChecks(unittest.TestCase):
    def test_kit_files_pass_every_project_content_check(self):
        with tempfile.TemporaryDirectory() as root:
            project = kit_project(root)
            self.assertTrue(any((project / 'assets' / 'tiktok-platform').glob('*.plugin.js')), 'no 3.x plugins copied')
            for script, args in CHECKS:
                with self.subTest(check=script):
                    r = run(script, args, project)
                    self.assertEqual(r.returncode, 0, '%s rejects the platform kit itself:\n%s\n%s'
                                     % (script, r.stdout[-1500:], r.stderr[-800:]))

    def test_negative_control_v773_preview_text_is_caught(self):
        with tempfile.TemporaryDirectory() as root:
            project = kit_project(root)
            flow = project / 'assets' / 'tiktok-platform' / 'MissionFlow.js'
            text = flow.read_text(encoding='utf-8')
            start = text.index("  preview: '")
            end = text.index("'", start + len("  preview: '")) + 1
            flow.write_text(text[:start] + "  preview: '" + OLD_PREVIEW + "'" + text[end:], encoding='utf-8')
            r = run('audit_dev_text.py', ['--project', '{p}', '--final'], project)
            self.assertEqual(r.returncode, 1, r.stdout[-800:])
            self.assertIn('LOCAL PREVIEW', r.stdout)


if __name__ == '__main__':
    unittest.main()

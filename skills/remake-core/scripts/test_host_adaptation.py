"""Check host routing contracts without pretending to execute a different operating system."""
import ast
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import probe_host


class HostAdaptationTests(unittest.TestCase):
    def test_windows_and_mac_choose_different_process_and_venv_paths(self):
        win = probe_host.platform_policy("Windows")
        mac = probe_host.platform_policy("Darwin")
        self.assertEqual(win["grok_binary"], "grok.exe")
        self.assertEqual(mac["grok_binary"], "grok")
        self.assertEqual(win["venv_python"], "Scripts/python.exe")
        self.assertEqual(mac["venv_python"], "bin/python")
        self.assertIn("POSIX", mac["process_group"])
        self.assertFalse(probe_host.platform_policy("Other")["supported_host"])

    def test_binary_discovery_prefers_path_then_existing_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "candidate"
            candidate.write_text("fixture", encoding="utf-8")
            with patch.object(probe_host.shutil, "which", return_value=None):
                self.assertEqual(probe_host.existing_binary(["tool"], [candidate]), str(candidate.resolve()))
            with patch.object(probe_host.shutil, "which", return_value=str(candidate)):
                self.assertEqual(probe_host.existing_binary(["tool"], []), str(candidate.resolve()))

    def test_probe_never_invokes_a_subprocess(self):
        with patch.object(subprocess, "run", side_effect=AssertionError("must not launch")), \
             patch.object(subprocess, "Popen", side_effect=AssertionError("must not launch")):
            report = probe_host.probe()
        self.assertTrue(report["read_only_probe"])
        self.assertFalse(report["apps_started"])
        self.assertNotIn("authenticated", report["tools"]["grok"])

    def test_cli_writes_new_report_and_preserves_existing_report(self):
        with tempfile.TemporaryDirectory(prefix="host space ") as temp:
            output = Path(temp) / "host.json"
            command = [sys.executable, "-B", str(Path(probe_host.__file__)), "--out", str(output)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertIn(first.returncode, [0, 2])
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(report["read_only_probe"])
            original = output.read_bytes()
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(output.read_bytes(), original)

    def test_companion_scripts_keep_python_shebang_and_module_documentation(self):
        skills = Path(__file__).resolve().parents[2]
        for relative in ["mobile-touch-computer-use/scripts/prepare_preview.py",
                         "grok-image-review/scripts/review.py", "grok-delegate/scripts/delegate.py"]:
            companion = skills / relative
            if not companion.is_file():
                companion = skills.parent / "support-skills" / relative
            text = companion.read_text(encoding="utf-8")
            self.assertEqual(text.splitlines()[0], "#!/usr/bin/env python3")
            self.assertIsNotNone(ast.get_docstring(ast.parse(text)))


if __name__ == "__main__":
    unittest.main(verbosity=2)

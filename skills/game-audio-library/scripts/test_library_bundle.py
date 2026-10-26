#!/usr/bin/env python3
"""Small offline contracts for original-byte exports and relocatable installations."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import math
import os
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
import zipfile
from pathlib import Path
from unittest.mock import patch

import install_audio_library as installer
from library_bundle import export_bundle, portable_names


def wav_bytes(seed=1):
    out = io.BytesIO()
    with wave.open(out, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(22050)
        wav.writeframes(bytes([seed, 1, seed, 254]) * 4410)
    return out.getvalue()


class BundleContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="audio bundle contracts ")
        self.root = Path(self.temp.name)
        self.library = self.root / "source computer" / "Library with spaces"
        self.library.mkdir(parents=True)
        self.rows, self.credits = [], []
        self.allowlist = self.root / "verified.json"
        self.rules = [{"prefix": "raw/verified/puzzle", "license": "CC0",
                       "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                       "page": "https://original.example/puzzle", "author": "Original Author",
                       "proof": ["https://original.example/puzzle#license"]}]
        self.add_asset("raw/verified/puzzle/click.wav")
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def add_asset(self, relative, license_name="CC0", quality="100", seed=1):
        path = self.library / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(wav_bytes(seed))
        file_sha = installer.digest_file(path)
        self.rows.append({"path": str(path), "source": "verified", "name": path.stem,
                          "license": license_name, "quality": quality, "kind": "sfx",
                          "file_sha256": file_sha, "audio_id": "pcm-sha256:" + file_sha,
                          "family_id": "puzzle", "themes": "casual|puzzle", "mtime": "1"})
        self.credits.append({"file": str(path), "source": "verified", "title": path.stem,
                             "author": "Original Author", "license": license_name,
                             "license_url": "", "url": "https://original.example/puzzle/download",
                             "attribution_required": "no", "download_date": "2026-10-26"})
        return path

    def save(self):
        (self.library / "index.csv").write_bytes(installer.csv_bytes(list(self.rows[0]), self.rows))
        (self.library / "credits_master.csv").write_bytes(installer.csv_bytes(list(self.credits[0]), self.credits))
        self.allowlist.write_text(json.dumps({"schema": 1, "sources": self.rules}))

    def export(self, name="audio.zip"):
        self.save()
        out = self.root / name
        result = export_bundle(self.library, out, self.allowlist)
        self.assertTrue(result["ok"])
        self.assertTrue(result["source_bytes_verified"])
        self.assertEqual(installer.digest_file(out), result["sha256"])
        self.assertTrue(Path(result["sha256_file"]).read_text().startswith(result["sha256"]))
        return out, result

    def install(self, archive, dest=None):
        return installer.install_bundle(archive, dest or self.root / "recipient computer" / "Audio Library", False)

    def tamper(self, archive, action, name="tampered.zip"):
        with zipfile.ZipFile(archive) as z:
            entries = [(i, z.read(i.filename)) for i in z.infolist()]
        target = self.root / name
        with zipfile.ZipFile(target, "w") as z:
            for info, data in entries:
                info, data = action(info, data)
                if info is not None:
                    z.writestr(info, data)
        return target

    def assert_rejected_unchanged(self, archive):
        destination = self.root / "old library"
        destination.mkdir(exist_ok=True)
        (destination / "index.csv").write_bytes(b"path,license\n/old.wav,CC0\n")
        (destination / "credits_master.csv").write_bytes(b"file,license\n/old.wav,CC0\n")
        config = self.root / "config.json"
        config.write_text('{"library":"old"}')
        before = {p: p.read_bytes() for p in destination.rglob("*") if p.is_file()}
        config_before = config.read_bytes()
        with self.assertRaises((installer.BundleError, ValueError, KeyError, zipfile.BadZipFile)):
            installer.install_bundle(archive, destination, True, config)
        self.assertEqual(before, {p: p.read_bytes() for p in destination.rglob("*") if p.is_file()})
        self.assertEqual(config_before, config.read_bytes())

    def test_normal_relocation_and_preserved_metadata(self):
        archive, result = self.export()
        # Export should not leak either source machine absolute root in its metadata.
        with zipfile.ZipFile(archive) as z:
            for name in ("index.csv", "credits_master.csv", "library-manifest.json"):
                self.assertNotIn(str(self.library).encode(), z.read("GameAudioLibrary/" + name))
        installed = self.install(archive)
        destination = Path(installed["library"])
        rows = installer.read_csv_bytes((destination / "index.csv").read_bytes())[1]
        credits = installer.read_csv_bytes((destination / "credits_master.csv").read_bytes())[1]
        self.assertEqual(rows[0]["path"], str(destination / "raw/verified/puzzle/click.wav"))
        self.assertEqual(rows[0]["path"], credits[0]["file"])
        self.assertEqual(rows[0]["audio_id"], self.rows[0]["audio_id"])
        self.assertEqual(rows[0]["family_id"], "puzzle")
        self.assertEqual(rows[0]["themes"], "casual|puzzle")
        self.assertEqual(credits[0]["license"], "CC0")
        self.assertTrue(credits[0]["license_url"].startswith("https://creativecommons.org/"))
        self.assertEqual(installer.digest_file(rows[0]["path"]), self.rows[0]["file_sha256"])

    def test_repeat_incremental_install_preserves_usage_and_auth(self):
        archive, _ = self.export()
        result = self.install(archive)
        destination = Path(result["library"])
        for name in ("usage/game.json", "auth/session.json", "my-custom-notes.txt"):
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("personal state")
        before = {p: p.read_bytes() for p in destination.rglob("*") if p.is_file()}
        repeated = self.install(archive)
        self.assertEqual(repeated["installed"], 0)
        self.assertEqual(repeated["reused"], 1)
        self.assertEqual(before, {p: p.read_bytes() for p in destination.rglob("*") if p.is_file()})
        self.add_asset("raw/verified/puzzle/win.wav", seed=2)
        second, _ = self.export("new-version.zip")
        expanded = self.install(second)
        self.assertEqual(expanded["installed"], 1)
        self.assertEqual(expanded["reused"], 1)
        self.assertTrue(expanded["metadata_backup"])
        self.assertEqual(len(installer.read_csv_bytes((destination / "index.csv").read_bytes())[1]), 2)
        for name in ("usage/game.json", "auth/session.json", "my-custom-notes.txt"):
            self.assertEqual((destination / name).read_text(), "personal state")

    def test_standalone_offline_install_without_skill_or_site_packages(self):
        archive, _ = self.export()
        unpacked = self.root / "standalone"
        with zipfile.ZipFile(archive) as z:
            z.extractall(unpacked)
        # -I -S disables user imports and site-packages, and this script has no network code.
        result = subprocess.run([sys.executable, "-I", "-S", str(unpacked / "GameAudioLibrary/install_audio_library.py"),
                                 "--library", str(self.root / "offline destination"), "--no-activate"],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_activate_only_after_success_and_preserve_config_fields(self):
        archive, _ = self.export()
        config = self.root / "custom config" / "library.json"
        config.parent.mkdir()
        config.write_text('{"library":"old","custom":"keep"}')
        result = installer.install_bundle(archive, self.root / "activated library", True, config)
        self.assertEqual(json.loads(config.read_text())["library"], result["library"])
        self.assertEqual(json.loads(config.read_text())["custom"], "keep")
        self.assertTrue(list(config.parent.glob("library.json.backup-*")))

    def test_installer_config_common_resolution_and_env_precedence(self):
        archive, _ = self.export()
        home = self.root / "recipient home with spaces"
        home.mkdir()
        destination = self.root / "persistent library with spaces"
        config = home / ".game-audio-library/library.json"
        installer.install_bundle(archive, destination, True, config)
        script = 'import sys; sys.path.insert(0,sys.argv[1]); from common import LIB; print(LIB)'
        env = dict(os.environ, HOME=str(home))
        env.pop("GAME_AUDIO_LIB", None)
        command = [sys.executable, "-S", "-c", script, str(Path(__file__).resolve().parent)]
        resolved = subprocess.run(command, env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        self.assertEqual(resolved.stdout.strip(), str(destination.resolve()))
        env["GAME_AUDIO_LIB"] = str(self.root / "explicit override with spaces")
        override = subprocess.run(command, env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(override.returncode, 0, override.stderr)
        self.assertEqual(override.stdout.strip(), str(Path(env["GAME_AUDIO_LIB"]).resolve()))
        env.pop("GAME_AUDIO_LIB")
        config.unlink()
        default = subprocess.run(command, env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertEqual(default.stdout.strip(), str((home / "GameAudioLibrary").resolve()))

    def test_install_from_directory_already_at_destination(self):
        archive, _ = self.export()
        unpacked = self.root / "in place install"
        with zipfile.ZipFile(archive) as z:
            z.extractall(unpacked)
        destination = unpacked / "GameAudioLibrary"
        result = installer.install_bundle(destination, destination, False)
        self.assertEqual(result["installed"], 0)
        index = installer.read_csv_bytes((destination / "index.csv").read_bytes())[1]
        self.assertEqual(len(index), 1)
        self.assertTrue(Path(index[0]["path"]).is_absolute())

    def test_unverified_and_restricted_assets_are_not_exported(self):
        self.add_asset("raw/other/unverified/sound.wav", seed=2)
        self.add_asset("raw/verified/puzzle/restricted.wav", "CC-BY-NC 4.0", seed=3)
        self.add_asset("raw/verified/puzzle/quiet.wav", quality="69", seed=4)
        archive, result = self.export()
        self.assertEqual(result["assets"], 1)
        self.assertEqual(result["skipped"]["not-verified-for-redistribution"], 1)
        self.assertEqual(result["skipped"]["license-not-consistent-with-verified-source"], 1)
        self.assertEqual(result["skipped"]["quality-below-70-or-unknown"], 1)
        with zipfile.ZipFile(archive) as z:
            self.assertFalse(any("restricted" in name or "unverified" in name or "quiet.wav" in name for name in z.namelist()))

    def test_source_allowlist_rejects_royalty_free_as_redistribution(self):
        self.rules[0].update({"license": "Pixabay royalty-free", "license_url": "https://pixabay.com/service/license-summary/"})
        self.save()
        with self.assertRaises(installer.BundleError):
            export_bundle(self.library, self.root / "no.zip", self.allowlist)
        self.assertFalse((self.root / "no.zip").exists())

    def test_cc_by_author_attribution_and_local_license_text(self):
        self.rules[0].update({"license": "CC-BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
                              "attribution": '"Puzzle Click" by Original Author, CC BY 4.0. https://original.example/puzzle',
                              "license_files": ["raw/verified/puzzle/License.txt"]})
        (self.library / "raw/verified/puzzle/License.txt").write_text("Original author's CC BY 4.0 notice")
        self.rows[0]["license"] = "CC-BY 4.0"
        self.credits[0]["license"] = "CC-BY 4.0"
        archive, _ = self.export()
        with zipfile.ZipFile(archive) as z:
            self.assertIn(b'"Puzzle Click"', z.read("GameAudioLibrary/CREDITS.txt"))
            notices = [name for name in z.namelist() if name.startswith("GameAudioLibrary/LICENSES/") and name.endswith(".txt")]
            self.assertEqual(len(notices), 1)
            self.assertIn(b"Original author's", z.read(notices[0]))
        result = self.install(archive)
        credits = installer.read_csv_bytes((Path(result["library"]) / "credits_master.csv").read_bytes())[1]
        self.assertEqual(credits[0]["attribution_required"], "yes")
        self.assertIn('"Puzzle Click"', credits[0]["attribution"])

    def test_windows_names_and_case_conflicts_preserve_distinct_bytes(self):
        self.add_asset("raw/verified/puzzle/CON.wav", seed=2)
        self.add_asset("raw/verified/puzzle/click?.wav", seed=3)
        self.add_asset("raw/verified/puzzle/click*.wav", seed=4)
        # The source filesystem may itself be case-insensitive; exercise case mapping
        # directly, and exercise two distinct illegal-name collisions via real files.
        case_names = portable_names(["raw/source/Case/a.wav", "raw/source/case/A.wav"])
        self.assertEqual(len({value.casefold() for value in case_names.values()}), 2)
        archive, result = self.export()
        source = installer.BundleSource(archive)
        try:
            verified = installer.validate_bundle(source)
            manifest, index = verified[0], verified[2]
        finally:
            source.close()
        paths = [asset["path"] for asset in manifest["assets"]]
        self.assertEqual(len(paths), len(set(p.casefold() for p in paths)))
        for value in paths:
            installer.safe_relative(value)
        self.assertEqual(len(set(asset["sha256"] for asset in manifest["assets"])), 4)
        original_ids = {row["file_sha256"]: (row["audio_id"], row["family_id"], row["themes"]) for row in self.rows}
        for row in index:
            self.assertEqual((row["audio_id"], row["family_id"], row["themes"]), original_ids[row["file_sha256"]])
        self.assertEqual(self.install(archive)["installed"], 4)

    def test_bad_audio_hash_rejected_before_any_existing_file_changes(self):
        archive, _ = self.export()
        bad = self.tamper(archive, lambda info, data: (info, data + b"changed") if info.filename.endswith("click.wav") else (info, data))
        self.assert_rejected_unchanged(bad)

    def test_unmanifested_file_rejected(self):
        archive, _ = self.export()
        bad = self.root / "extra.zip"
        shutil.copyfile(archive, bad)
        with zipfile.ZipFile(bad, "a") as z:
            z.writestr("GameAudioLibrary/unapproved.py", "print('unexpected')")
        self.assert_rejected_unchanged(bad)

    def test_traversal_symlink_and_duplicate_zip_rejected(self):
        archive, _ = self.export()
        for kind in ("traversal", "symlink", "duplicate"):
            with self.subTest(kind=kind):
                bad = self.root / (kind + ".zip")
                shutil.copyfile(archive, bad)
                with zipfile.ZipFile(bad, "a") as z:
                    if kind == "traversal":
                        z.writestr("GameAudioLibrary/../outside.txt", "bad")
                    elif kind == "symlink":
                        info = zipfile.ZipInfo("GameAudioLibrary/link")
                        info.create_system = 3
                        info.external_attr = (stat.S_IFLNK | 0o777) << 16
                        z.writestr(info, "/outside")
                    else:
                        z.writestr("GameAudioLibrary/README.txt", "duplicate")
                self.assert_rejected_unchanged(bad)

    def test_existing_conflicting_audio_refuses_before_metadata_write(self):
        archive, _ = self.export()
        destination = self.root / "old library"
        target = destination / "raw/verified/puzzle/click.wav"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"Different personal sound")
        self.assert_rejected_unchanged(archive)
        self.assertEqual(target.read_bytes(), b"Different personal sound")

    def test_source_symlink_and_stale_hash_are_not_packaged(self):
        original = self.library / "raw/verified/puzzle/click.wav"
        original.write_bytes(b"changed since index")
        self.save()
        with self.assertRaises(installer.BundleError):
            export_bundle(self.library, self.root / "stale.zip", self.allowlist)
        original.unlink()
        outside = self.root / "outside.wav"
        outside.write_bytes(wav_bytes())
        original.symlink_to(outside)
        with self.assertRaises(installer.BundleError):
            export_bundle(self.library, self.root / "symlink-source.zip", self.allowlist)

    def test_export_does_not_overwrite_historical_zip(self):
        archive, _ = self.export()
        before = archive.read_bytes()
        with self.assertRaises(installer.BundleError):
            export_bundle(self.library, archive, self.allowlist)
        self.assertEqual(before, archive.read_bytes())

    def test_existing_metadata_concurrent_edit_not_overwritten(self):
        archive, _ = self.export()
        destination = self.root / "race library"
        original_atomic = installer._atomic
        original_unchanged = installer._unchanged
        changed = [False]
        def race(path, snapshot):
            if path.name == "index.csv" and not changed[0]:
                changed[0] = True
                path.write_text("path,license\nconcurrent.wav,CC0\n")
            return original_unchanged(path, snapshot)
        config = self.root / "not-activated.json"
        with patch.object(installer, "_unchanged", race):
            with self.assertRaises(installer.BundleError):
                installer.install_bundle(archive, destination, True, config)
        self.assertIn("concurrent.wav", (destination / "index.csv").read_text())
        self.assertFalse(config.exists())
        self.assertFalse((destination / ".audio-library-install.lock").exists())

    def test_actual_common_credits_consumer_retains_license_after_relocation(self):
        archive, _ = self.export()
        destination = Path(self.install(archive)["library"])
        script = ('import sys; sys.path.insert(0,sys.argv[1]); '
                  'from common import credits_by_file; import json; print(json.dumps(credits_by_file()))')
        env = dict(os.environ, GAME_AUDIO_LIB=str(destination))
        result = subprocess.run([sys.executable, "-S", "-c", script, str(Path(__file__).resolve().parent)],
                                env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        metadata = json.loads(result.stdout)
        key = str(destination / "raw/verified/puzzle/click.wav")
        self.assertIn(key, metadata)
        self.assertEqual(metadata[key]["license"], "CC0")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "real rebuild requires existing ffmpeg/ffprobe")
    def test_actual_build_index_full_rebuild_keeps_relocated_author_license(self):
        # Tiny synthesized contract fixture; exported library assets are never synthesized.
        path = self.library / "raw/verified/puzzle/click.wav"
        with wave.open(str(path), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(44100)
            f.writeframes(b"".join(struct.pack("<h", int(6000 * math.sin(2 * math.pi * 440 * i / 44100))) for i in range(22050)))
        self.rows[0]["file_sha256"] = installer.digest_file(path)
        archive, _ = self.export()
        destination = Path(self.install(archive)["library"])
        env = dict(os.environ, GAME_AUDIO_LIB=str(destination))
        result = subprocess.run([sys.executable, str(Path(__file__).with_name("build_index.py")), "--full"],
                                env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        index = installer.read_csv_bytes((destination / "index.csv").read_bytes())[1]
        self.assertEqual(len(index), 1)
        self.assertEqual(index[0]["license"], "CC0")
        self.assertEqual(index[0]["author"], "Original Author")
        self.assertNotIn("无授权", index[0]["issues"])
        self.assertGreaterEqual(float(index[0]["quality"]), 70)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "real rebuild requires existing ffmpeg/ffprobe")
    def test_windows_mapping_full_rebuild_preserves_only_same_byte_identity_metadata(self):
        path = self.add_asset("raw/verified/puzzle/reward?.wav", seed=3)
        self.rows, self.credits = [self.rows[-1]], [self.credits[-1]]
        def write_tone(target, frequency):
            with wave.open(str(target), "wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(44100)
                f.writeframes(b"".join(struct.pack("<h", int(6000 * math.sin(2 * math.pi * frequency * i / 44100))) for i in range(22050)))
        write_tone(path, 440)
        self.rows[0].update(file_sha256=installer.digest_file(path), family_id="artist:original_work_42",
                            themes="winter|cozy", kind="sfx")
        archive, _ = self.export()
        destination = Path(self.install(archive)["library"])
        installed_path = destination / "raw/verified/puzzle/reward_.wav"
        self.assertTrue(installed_path.is_file())
        index_path = destination / "index.csv"
        env = dict(os.environ, GAME_AUDIO_LIB=str(destination))
        command = [sys.executable, str(Path(__file__).with_name("build_index.py"))]
        result = subprocess.run(command + ["--full"], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        rebuilt = installer.read_csv_bytes(index_path.read_bytes())[1][0]
        self.assertEqual(rebuilt["family_id"], "artist:original_work_42")
        self.assertEqual(rebuilt["themes"], "winter|cozy")
        self.assertEqual(rebuilt["kind"], "sfx")
        self.assertEqual(rebuilt["file_sha256"], self.rows[0]["file_sha256"])
        self.assertGreaterEqual(float(rebuilt["quality"]), 70)
        # A replacement recording must not inherit the old work/theme identity.
        write_tone(installed_path, 660)
        changed = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(changed.returncode, 0, changed.stderr)
        replaced = installer.read_csv_bytes(index_path.read_bytes())[1][0]
        self.assertNotEqual(replaced["file_sha256"], rebuilt["file_sha256"])
        self.assertNotEqual(replaced["audio_id"], rebuilt["audio_id"])
        self.assertNotEqual(replaced["family_id"], "artist:original_work_42")
        self.assertNotEqual(replaced["themes"], "winter|cozy")
        self.assertEqual(replaced["license"], "CC0")


if __name__ == "__main__":
    unittest.main(verbosity=2)

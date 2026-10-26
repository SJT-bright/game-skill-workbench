#!/usr/bin/env python3
"""Install a verified offline audio bundle. Python 3.9+, standard library only.

This file is also embedded in exported bundles; do not import Skill modules here.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
import re
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

ROOT = "GameAudioLibrary"
MANIFEST = "library-manifest.json"
AUDIO_EXT = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aif", ".aiff", ".opus"}
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)
SUPPORT_FILES = {"index.csv", "credits_master.csv", "CREDITS.txt", "README.txt",
                 "install_audio_library.py", "Install.command", "Install.cmd"}


class BundleError(ValueError):
    pass


def digest_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_license(value):
    text = str(value or "").strip().upper().replace("_", " ")
    if re.fullmatch(r"CC\s*0(?:\s*1\.0)?(?:\s*UNIVERSAL)?", text):
        return "CC0"
    match = re.fullmatch(r"CC\s*[- ]?\s*BY\s*[- ]?\s*([1-4]\.0)", text)
    return "CC-BY " + match.group(1) if match else None


def check_license_url(license_name, value):
    parsed = urlparse(str(value or ""))
    if parsed.scheme != "https" or parsed.hostname != "creativecommons.org":
        return False
    path = parsed.path.rstrip("/")
    expected = "/publicdomain/zero/1.0" if license_name == "CC0" else "/licenses/by/" + license_name.split()[-1]
    return path == expected or path == expected + "/legalcode" or path == expected + "/legalcode.txt"


def safe_relative(value):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise BundleError("Invalid relative path: " + repr(value))
    parts = value.split("/")
    if value.startswith("/") or any(p in ("", ".", "..") for p in parts):
        raise BundleError("Unsafe relative path: " + repr(value))
    for part in parts:
        if any(ord(c) < 32 or c in '<>:"|?*' for c in part) or part.endswith((" ", ".")) or RESERVED.match(part):
            raise BundleError("Non-portable relative path: " + repr(value))
    return value


def read_csv_bytes(data):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""))
    fields = reader.fieldnames or []
    if len(fields) != len(set(fields)) or not fields or any(not f for f in fields):
        raise BundleError("Invalid CSV header")
    rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise BundleError("Invalid CSV row")
    return fields, rows


def csv_bytes(fields, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fields})
    return stream.getvalue().encode("utf-8")


def safe_target(root, relative):
    safe_relative(relative)
    target = root.joinpath(*relative.split("/"))
    current = target
    while current != root:
        if current.is_symlink():
            raise BundleError("Symlink in destination/source path: " + str(current))
        if current != target and current.exists() and not current.is_dir():
            raise BundleError("Parent path is not a directory: " + str(current))
        current = current.parent
    if target.exists() and not target.is_file():
        raise BundleError("Expected regular file: " + str(target))
    return target


class BundleSource:
    def __init__(self, source):
        self.path = Path(source).expanduser().resolve()
        self.archive = None
        if self.path.is_dir():
            if (self.path / MANIFEST).is_file():
                self.directory = self.path
            elif (self.path / ROOT / MANIFEST).is_file():
                self.directory = self.path / ROOT
            else:
                raise BundleError("No library-manifest.json found")
            self.directory = self.directory.resolve()
            self.members = None
        else:
            self.archive = zipfile.ZipFile(self.path)
            infos = self.archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)) or len(names) != len({name.casefold() for name in names}):
                raise BundleError("Duplicate or case-conflicting ZIP members")
            self.members = {}
            for info in infos:
                safe_relative(info.filename)
                parts = info.filename.split("/")
                mode = (info.external_attr >> 16) & 0xFFFF
                if len(parts) < 2 or parts[0] != ROOT or info.is_dir() or (mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG)):
                    raise BundleError("Unsupported ZIP member: " + info.filename)
                if info.flag_bits & 1:
                    raise BundleError("Encrypted ZIP member")
                self.members["/".join(parts[1:])] = info

    def close(self):
        if self.archive:
            self.archive.close()

    def open(self, relative):
        safe_relative(relative)
        if self.archive:
            if relative not in self.members:
                raise BundleError("Missing bundle member: " + relative)
            return self.archive.open(self.members[relative])
        return safe_target(self.directory, relative).open("rb")

    def read(self, relative, limit=64 * 1024 * 1024):
        with self.open(relative) as f:
            data = f.read(limit + 1)
        if len(data) > limit:
            raise BundleError("Metadata too large: " + relative)
        return data


def validate_bundle(source):
    """Validate all bytes and metadata before the installer touches its destination."""
    manifest = json.loads(source.read(MANIFEST))
    if not isinstance(manifest, dict) or manifest.get("schema") != 1 or manifest.get("format") != "game-audio-library-offline":
        raise BundleError("Unsupported bundle format")
    files = manifest.get("files")
    assets = manifest.get("assets")
    if not isinstance(files, dict) or not isinstance(assets, list) or not assets:
        raise BundleError("Empty or invalid manifest")
    folded = set()
    for relative, record in files.items():
        safe_relative(relative)
        if relative.casefold() in folded or relative == MANIFEST:
            raise BundleError("Duplicate manifest member")
        folded.add(relative.casefold())
        if not (relative in SUPPORT_FILES or relative.startswith("raw/") or relative.startswith("LICENSES/")):
            raise BundleError("Unexpected bundle file: " + relative)
        if relative.startswith("LICENSES/") and PurePosixPath(relative).suffix.lower() not in {".txt", ".json"}:
            raise BundleError("Unexpected license document type: " + relative)
        if relative.startswith("raw/") and PurePosixPath(relative).suffix.lower() not in AUDIO_EXT:
            raise BundleError("Non-audio payload under raw/: " + relative)
        if not isinstance(record, dict) or not SHA_RE.fullmatch(str(record.get("sha256", ""))) or type(record.get("size")) is not int or record["size"] < 0:
            raise BundleError("Invalid file digest record: " + relative)
        h, length = hashlib.sha256(), 0
        with source.open(relative) as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(block)
                length += len(block)
                if length > record["size"]:
                    raise BundleError("Size mismatch: " + relative)
        if length != record["size"] or h.hexdigest() != record["sha256"]:
            raise BundleError("SHA256/size mismatch: " + relative)
    if source.members is not None and set(source.members) != set(files) | {MANIFEST}:
        raise BundleError("ZIP member list does not match manifest")
    if not {"index.csv", "credits_master.csv", "CREDITS.txt", "install_audio_library.py", "README.txt"} <= set(files):
        raise BundleError("Required bundle metadata missing")
    index_fields, index = read_csv_bytes(source.read("index.csv"))
    credit_fields, credits = read_csv_bytes(source.read("credits_master.csv"))
    if "path" not in index_fields or "file" not in credit_fields:
        raise BundleError("Missing CSV path field")
    index_map, credit_map, asset_map = {}, {}, {}
    for key, rows, result in (("path", index, index_map), ("file", credits, credit_map), ("path", assets, asset_map)):
        for row in rows:
            if not isinstance(row, dict):
                raise BundleError("Invalid asset record")
            relative = safe_relative(row.get(key))
            if relative in result:
                raise BundleError("Duplicate metadata path: " + relative)
            result[relative] = row
    raw = {relative for relative in files if relative.startswith("raw/")}
    if not raw or not (raw == set(index_map) == set(credit_map) == set(asset_map)):
        raise BundleError("Audio/index/credits/manifest asset closure mismatch")
    for relative, asset in asset_map.items():
        license_name = canonical_license(asset.get("license"))
        if not license_name or not check_license_url(license_name, asset.get("license_url")):
            raise BundleError("Unsupported redistribution license: " + relative)
        if canonical_license(index_map[relative].get("license")) != license_name or canonical_license(credit_map[relative].get("license")) != license_name:
            raise BundleError("License metadata mismatch: " + relative)
        if credit_map[relative].get("license_url") != asset.get("license_url"):
            raise BundleError("License URL metadata mismatch: " + relative)
        try:
            quality = float(index_map[relative].get("quality", ""))
        except (TypeError, ValueError):
            raise BundleError("Invalid quality: " + relative)
        if not math.isfinite(quality) or quality < 70:
            raise BundleError("Quality below original 70 threshold: " + relative)
        if asset.get("sha256") != files[relative]["sha256"]:
            raise BundleError("Asset SHA mismatch: " + relative)
        if index_map[relative].get("file_sha256") and index_map[relative]["file_sha256"] != asset["sha256"]:
            raise BundleError("Index SHA mismatch: " + relative)
        if not asset.get("source") or not asset.get("author") or not asset.get("source_page") or not asset.get("proof") or not asset.get("attribution"):
            raise BundleError("Incomplete provenance: " + relative)
        if credit_map[relative].get("author") != asset["author"] or credit_map[relative].get("attribution") != asset["attribution"]:
            raise BundleError("Author/attribution metadata mismatch: " + relative)
        if not isinstance(asset["proof"], list) or not all(isinstance(value, str) and urlparse(value).scheme == "https" and urlparse(value).hostname for value in asset["proof"]):
            raise BundleError("Invalid license proof: " + relative)
    fingerprint = hashlib.sha256(json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    if fingerprint != manifest.get("content_id"):
        raise BundleError("Bundle content fingerprint mismatch")
    return manifest, index_fields, index, credit_fields, credits


def _snapshot(path):
    if path.is_symlink():
        raise BundleError("Metadata/config symlink refused: " + str(path))
    return path.read_bytes() if path.exists() else None


def _unchanged(path, snapshot):
    if _snapshot(path) != snapshot:
        raise BundleError("Concurrent metadata edit; refusing overwrite: " + str(path))


def _atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _merge_metadata(previous, incoming_fields, incoming, key, destination):
    old_fields, old_rows = read_csv_bytes(previous) if previous is not None else ([], [])
    fields = list(dict.fromkeys(old_fields + incoming_fields))
    mapping = {}
    for row in old_rows:
        value = row.get(key)
        if not value:
            raise BundleError("Existing metadata has no " + key)
        if not Path(value).is_absolute():
            # Also supports running the installer after unzipping directly into
            # the intended library. Package-relative rows become local rows once.
            safe_relative(value)
            value = str(destination.joinpath(*value.split("/")))
            row = dict(row, **{key: value})
        if value in mapping:
            raise BundleError("Existing metadata has duplicate " + key + ": " + value)
        mapping[value] = row
    for row in incoming:
        row = dict(row)
        row[key] = str(destination.joinpath(*row[key].split("/")))
        mapping[row[key]] = dict(mapping.get(row[key], {}), **row)
    return csv_bytes(fields, list(mapping.values()))


def install_bundle(bundle_path, destination, activate=True, config_path=None):
    source = BundleSource(bundle_path)
    lock = None
    try:
        manifest, index_fields, index, credit_fields, credits = validate_bundle(source)
        destination = Path(destination).expanduser().absolute()
        if destination.is_symlink():
            destination = destination.resolve()
        destination = destination.resolve()
        destination.mkdir(parents=True, exist_ok=True)
        lock_path = destination / ".audio-library-install.lock"
        try:
            lock = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise BundleError("Another install is active; lock exists: " + str(lock_path))
        os.write(lock, (str(os.getpid()) + "\n").encode("ascii"))
        index_path, credit_path = destination / "index.csv", destination / "credits_master.csv"
        old_index, old_credits = _snapshot(index_path), _snapshot(credit_path)
        config_path = Path(config_path) if config_path is not None else Path.home() / ".game-audio-library" / "library.json"
        old_config = _snapshot(config_path) if activate else None
        if activate and old_config is not None:
            existing_config = json.loads(old_config)
            if not isinstance(existing_config, dict):
                raise BundleError("Existing library config is not an object")
        else:
            existing_config = {}
        new_index = _merge_metadata(old_index, index_fields, index, "path", destination)
        new_credits = _merge_metadata(old_credits, credit_fields, credits, "file", destination)
        copy_plan, reused = [], 0
        # Preflight every collision before any source bytes or metadata are written.
        for asset in manifest["assets"]:
            relative = asset["path"]
            target = safe_target(destination, relative)
            if target.exists():
                if digest_file(target) != asset["sha256"]:
                    raise BundleError("Different bytes already exist; nothing overwritten: " + str(target))
                reused += 1
            else:
                copy_plan.append((relative, target, asset))
        # Detect case-only conflicts in an existing library on case-sensitive hosts too.
        for relative, target, asset in copy_plan:
            current = destination
            for component in relative.split("/"):
                if current.exists():
                    conflicts = [p.name for p in current.iterdir() if p.name.casefold() == component.casefold() and p.name != component]
                    if conflicts:
                        raise BundleError("Case-conflicting existing path: " + str(current / component))
                current = current / component
        for relative, target, asset in copy_plan:
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(prefix=".audio-", suffix=".tmp", dir=target.parent)
            try:
                with os.fdopen(fd, "wb") as out, source.open(relative) as incoming:
                    shutil.copyfileobj(incoming, out, 1024 * 1024)
                    out.flush()
                    os.fsync(out.fileno())
                if digest_file(temp_name) != asset["sha256"]:
                    raise BundleError("Source changed during copy: " + relative)
                # Hard-link publishes without overwriting a concurrent writer.
                try:
                    os.link(temp_name, target)
                except FileExistsError:
                    if digest_file(target) != asset["sha256"]:
                        raise BundleError("Concurrent conflicting audio write: " + relative)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
        _unchanged(index_path, old_index)
        _unchanged(credit_path, old_credits)
        if activate:
            _unchanged(config_path, old_config)
        changed_index, changed_credits = old_index != new_index, old_credits != new_credits
        backup_dir = None
        if (changed_index and old_index is not None) or (changed_credits and old_credits is not None):
            stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup_dir = destination / ".metadata-backups" / (stamp + "-" + manifest["content_id"][:12])
            backup_dir.mkdir(parents=True)
            if old_index is not None:
                (backup_dir / "index.csv").write_bytes(old_index)
            if old_credits is not None:
                (backup_dir / "credits_master.csv").write_bytes(old_credits)
        # Provenance commits first: an index must never reference missing credits.
        if changed_credits:
            _unchanged(credit_path, old_credits)
            _atomic(credit_path, new_credits)
        if changed_index:
            _unchanged(index_path, old_index)
            _atomic(index_path, new_index)
        # Keep bundle provenance with the installed library for offline attribution.
        receipt_dir = destination / ".installed-bundles" / manifest["content_id"]
        receipt_dir.mkdir(parents=True, exist_ok=True)
        for relative in (MANIFEST, "CREDITS.txt"):
            _atomic(receipt_dir / relative, source.read(relative))
        for relative in manifest["files"]:
            if relative.startswith("LICENSES/"):
                target = safe_target(receipt_dir, relative)
                _atomic(target, source.read(relative))
        # Activation is the final action, after every asset and metadata byte passed.
        if activate:
            _unchanged(config_path, old_config)
            existing_config.update({"schema": 1, "library": str(destination)})
            new_config = (json.dumps(existing_config, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            if old_config != new_config:
                if old_config is not None:
                    backup = config_path.with_name(config_path.name + ".backup-" + hashlib.sha256(old_config).hexdigest()[:16])
                    if not backup.exists():
                        _atomic(backup, old_config)
                _unchanged(config_path, old_config)
                _atomic(config_path, new_config)
        return {"ok": True, "library": str(destination), "content_id": manifest["content_id"],
                "assets": len(manifest["assets"]), "installed": len(copy_plan), "reused": reused,
                "activated": bool(activate), "metadata_backup": str(backup_dir) if backup_dir else None}
    finally:
        source.close()
        if lock is not None:
            os.close(lock)
            lock_path.unlink()


def main():
    parser = argparse.ArgumentParser(description="离线安装/增量合并音效库；不联网，不安装依赖。")
    parser.add_argument("bundle", nargs="?", default=str(Path(__file__).resolve().parent), help="音效库ZIP或已解压的GameAudioLibrary目录")
    parser.add_argument("--library", default=str(Path.home() / "GameAudioLibrary"), help="本地持久素材库目录")
    parser.add_argument("--no-activate", action="store_true", help="只安装，不修改Skill全局素材库配置")
    args = parser.parse_args()
    try:
        result = install_bundle(args.bundle, args.library, not args.no_activate)
    except (BundleError, OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

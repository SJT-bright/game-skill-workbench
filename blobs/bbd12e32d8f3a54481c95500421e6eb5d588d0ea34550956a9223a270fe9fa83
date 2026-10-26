#!/usr/bin/env python3
"""Export a portable audio library using an explicitly verified redistribution list.

Only CC0 / versioned CC-BY, quality >= 70, original bytes. No downloads.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from install_audio_library import (AUDIO_EXT, ROOT, MANIFEST, RESERVED, BundleError,
                                   BundleSource, canonical_license, check_license_url,
                                   csv_bytes, digest_file, read_csv_bytes,
                                   safe_relative, validate_bundle)


def verified_sources(path):
    document = json.loads(Path(path).read_bytes())
    if not isinstance(document, dict) or document.get("schema") != 1 or not isinstance(document.get("sources"), list):
        raise BundleError("Expected schema=1, sources=[...] redistribution allowlist")
    result, prefixes = [], set()
    for original in document["sources"]:
        if not isinstance(original, dict):
            raise BundleError("Invalid verified source record")
        rule = dict(original)
        prefix = safe_relative(rule.get("prefix"))
        if not prefix.startswith("raw/") or prefix in prefixes:
            raise BundleError("Invalid or duplicate source prefix: " + prefix)
        prefixes.add(prefix)
        rule["license"] = canonical_license(rule.get("license"))
        if not rule["license"] or not check_license_url(rule["license"], rule.get("license_url")):
            raise BundleError("Unverified/unsupported redistribution license: " + prefix)
        proof = rule.get("proof")
        if not isinstance(proof, list) or not proof or not all(_https(value) for value in proof):
            raise BundleError("Missing original license proof: " + prefix)
        if not _https(rule.get("page")) or not str(rule.get("author", "")).strip():
            raise BundleError("Missing source page/author: " + prefix)
        if not isinstance(rule.get("license_files", []), list):
            raise BundleError("license_files must be a list: " + prefix)
        result.append(rule)
    return sorted(result, key=lambda row: len(row["prefix"]), reverse=True)


def _https(value):
    parsed = urlparse(str(value or ""))
    return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username


def _relative(root, value):
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = root / path
    # Allow OS-level aliases of the library root (/var -> /private/var on macOS),
    # but never symlinks nested within the selected library itself.
    try:
        relative = path.resolve().relative_to(root)
    except ValueError:
        raise BundleError("Path outside selected library: " + str(path))
    if ".." in path.parts:
        raise BundleError("Invalid source path: " + str(path))
    current = path
    while current.resolve() != root:
        if current.is_symlink():
            raise BundleError("Symlink source refused: " + str(current))
        if current == current.parent:
            raise BundleError("Source path has no selected-library ancestor: " + str(path))
        current = current.parent
    return relative.as_posix(), path


def _portable_parts(value):
    parts = []
    for part in value.split("/"):
        part = re.sub(r'[<>:"\\|?*\x00-\x1f]', "_", part).rstrip(" .")
        if not part or part in (".", ".."):
            part = "_"
        if RESERVED.match(part):
            part = "_" + part
        if len(part.encode("utf-8")) > 180:
            suffix = Path(part).suffix[:12]
            part = part[:60] + "-" + hashlib.sha256(part.encode()).hexdigest()[:16] + suffix
        parts.append(part)
    return parts


def portable_names(values):
    """Map all components, resolving directory and file case collisions consistently."""
    children, mappings, used = {}, {}, {}
    for relative in sorted(values):
        original = relative.split("/")
        sanitized = _portable_parts(relative)
        parent_original, parent_portable = (), ()
        for position, (name, clean) in enumerate(zip(original, sanitized)):
            key = parent_original + (name,)
            if key not in mappings:
                siblings = used.setdefault(parent_portable, {})
                candidate = clean
                if candidate.casefold() in siblings and siblings[candidate.casefold()] != key:
                    path = Path(clean)
                    suffix = path.suffix if position == len(original) - 1 else ""
                    stem = clean[:-len(suffix)] if suffix else clean
                    candidate = stem + "-" + hashlib.sha256("/".join(key).encode()).hexdigest()[:12] + suffix
                    while candidate.casefold() in siblings and siblings[candidate.casefold()] != key:
                        candidate = "_" + candidate
                siblings[candidate.casefold()] = key
                mappings[key] = candidate
            parent_original = key
            parent_portable += (mappings[key],)
        children[relative] = safe_relative("/".join(parent_portable))
    return children


def _source_rule(relative, rules):
    return next((rule for rule in rules if relative == rule["prefix"] or relative.startswith(rule["prefix"] + "/")), None)


README = """独立音效/BGM库（离线安装，Python 3.9+，不安装依赖）

1. 解压整个 ZIP，保留 GameAudioLibrary 文件夹中的文件。
2. macOS/Linux：python3 install_audio_library.py --library ~/GameAudioLibrary
   Windows：py -3 install_audio_library.py --library "%USERPROFILE%\\GameAudioLibrary"
   也可直接指定 ZIP：python3 install_audio_library.py 音效库.zip --library 自选目录
3. 安装器先核验全部 SHA256、文件清单、授权和索引，再增量合并；相同素材复用，冲突拒绝覆盖。
   不修改 usage、auth、游戏选音记录。旧索引与授权表在 .metadata-backups 中保留。
4. 成功后写入 ~/.game-audio-library/library.json，本 Skill 自动索引此本地库。
   GAME_AUDIO_LIB 环境变量优先于上述配置；若设置过旧路径，请自行更新或取消。
   --no-activate 表示安装但不更改库选择。
5. 后续更新 Skill 时不必重新下载同一音效库。收到增量/新版音效库 ZIP 后重复同一安装命令即可。
   素材的作者、许可及署名要求见 CREDITS.txt 与 LICENSES/。用于游戏时保留所选 CC-BY 素材署名。

This offline installer uses Python standard library only; no network access or Skill installation is needed.
The asset files retain their original bytes. Quality metadata is the existing library's assessment, not a new listening approval.
Library ZIP and Skill ZIP are separate: keep this library installed across Skill updates.
"""


def export_bundle(library, out_path, sources_path):
    root = Path(library).expanduser().resolve()
    out_path = Path(out_path).expanduser().absolute()
    if out_path.suffix.lower() != ".zip":
        raise BundleError("Output must be a .zip file")
    sha_path = Path(str(out_path) + ".sha256")
    if out_path.exists() or sha_path.exists():
        raise BundleError("Output already exists; choose a new versioned filename")
    rules = verified_sources(sources_path)
    index_path, credit_path = root / "index.csv", root / "credits_master.csv"
    index_bytes, credits_bytes = index_path.read_bytes(), credit_path.read_bytes()
    index_fields, index = read_csv_bytes(index_bytes)
    credit_fields, credits = read_csv_bytes(credits_bytes)
    if "path" not in index_fields or "file" not in credit_fields:
        raise BundleError("Library metadata is missing its path field")
    credit_map = {}
    for row in credits:
        try:
            relative, _ = _relative(root, row.get("file"))
        except BundleError:
            continue
        if relative in credit_map and credit_map[relative] != row:
            raise BundleError("Conflicting source credits: " + relative)
        credit_map[relative] = row
    eligible, skipped, seen = [], Counter(), set()
    for row in index:
        try:
            relative, path = _relative(root, row.get("path"))
        except BundleError:
            skipped["outside-library-or-symlink"] += 1
            continue
        rule = _source_rule(relative, rules)
        if not rule:
            skipped["not-verified-for-redistribution"] += 1
            continue
        if not relative.startswith("raw/") or path.suffix.lower() not in AUDIO_EXT:
            skipped["not-raw-audio"] += 1
            continue
        if relative in seen:
            raise BundleError("Duplicate index path: " + relative)
        seen.add(relative)
        credit = credit_map.get(relative)
        if not credit:
            skipped["missing-credit-record"] += 1
            continue
        try:
            quality = float(row.get("quality", ""))
        except (TypeError, ValueError):
            quality = float("nan")
        if not math.isfinite(quality) or quality < 70:
            skipped["quality-below-70-or-unknown"] += 1
            continue
        if canonical_license(row.get("license")) != rule["license"] or canonical_license(credit.get("license")) != rule["license"]:
            skipped["license-not-consistent-with-verified-source"] += 1
            continue
        if credit.get("license_url") and not check_license_url(rule["license"], credit["license_url"]):
            skipped["credit-license-url-mismatch"] += 1
            continue
        if not path.is_file():
            raise BundleError("Selected audio missing: " + str(path))
        file_sha = digest_file(path)
        if row.get("file_sha256") and row["file_sha256"] != file_sha:
            raise BundleError("Index is stale; audio bytes changed: " + relative)
        eligible.append((relative, path, dict(row), dict(credit), rule, file_sha))
    if not eligible:
        raise BundleError("No quality >=70, explicitly redistribution-licensed audio to export")
    names = portable_names([entry[0] for entry in eligible])
    files, payload, assets, new_index, new_credits = {}, {}, [], [], []
    for field in ("file_sha256",):
        if field not in index_fields:
            index_fields.append(field)
    for field in ("license_url", "attribution"):
        if field not in credit_fields:
            credit_fields.append(field)
    used_rules = {}
    for relative, path, row, credit, rule, file_sha in eligible:
        portable = names[relative]
        row.update({"path": portable, "file_sha256": file_sha})
        author = credit.get("author") or row.get("author") or rule["author"]
        title = credit.get("title") or row.get("name") or path.stem
        attribution = credit.get("attribution") or rule.get("attribution")
        if not attribution:
            attribution = '{} — {}. Source: {}. License: {} ({}). Original audio, no changes.'.format(title, author, rule["page"], rule["license"], rule["license_url"])
        credit.update({"file": portable, "author": author, "title": title, "license": rule["license"],
                       "license_url": rule["license_url"], "attribution_required": "yes" if rule["license"].startswith("CC-BY") else "no",
                       "attribution": attribution})
        source_name = credit.get("source") or row.get("source") or relative.split("/")[1]
        credit["source"] = source_name
        asset = {"path": portable, "sha256": file_sha, "size": path.stat().st_size,
                 "source": source_name, "title": title, "author": author,
                 "license": rule["license"], "license_url": rule["license_url"],
                 "source_page": rule["page"], "proof": rule["proof"], "attribution": attribution,
                 "quality": row["quality"], "kind": row.get("kind", ""), "source_prefix": rule["prefix"]}
        files[portable] = {"sha256": file_sha, "size": asset["size"]}
        payload[portable] = path
        assets.append(asset)
        new_index.append(row)
        new_credits.append(credit)
        used_rules[rule["prefix"]] = rule
    payload["index.csv"] = csv_bytes(index_fields, new_index)
    payload["credits_master.csv"] = csv_bytes(credit_fields, new_credits)
    payload["README.txt"] = README.encode("utf-8")
    payload["install_audio_library.py"] = Path(__file__).with_name("install_audio_library.py").read_bytes()
    payload["Install.command"] = b'#!/bin/sh\ncd "$(dirname "$0")" || exit 1\nexec python3 ./install_audio_library.py "$@"\n'
    payload["Install.cmd"] = b'@echo off\r\ncd /d "%~dp0"\r\npy -3 install_audio_library.py %*\r\npause\r\n'
    credits_text = ["Offline Audio Library — ORIGINAL ASSETS / AUTHORS / LICENSES\n",
                    "CC0 assets do not require attribution. Retain the following CC-BY notices for assets used in a game.\n"]
    for asset in assets:
        credits_text.append("\n" + asset["path"] + "\n" + asset["attribution"] + "\nLicense: " + asset["license"] + " — " + asset["license_url"] + "\nProof: " + " ; ".join(asset["proof"]) + "\n")
    payload["CREDITS.txt"] = "".join(credits_text).encode("utf-8")
    for prefix, rule in used_rules.items():
        rule_id = hashlib.sha256(prefix.encode()).hexdigest()[:16]
        declaration = {key: value for key, value in rule.items() if key != "license_files"}
        payload["LICENSES/" + rule_id + "-source.json"] = (json.dumps(declaration, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        for number, local_file in enumerate(rule.get("license_files", [])):
            relative, path = _relative(root, local_file)
            if not (relative == prefix or relative.startswith(prefix + "/")) or path.suffix.lower() not in (".txt", ".md", ".html", ".htm"):
                raise BundleError("Invalid original license text path: " + relative)
            if path.stat().st_size > 2 * 1024 * 1024:
                raise BundleError("License text unexpectedly large: " + relative)
            payload["LICENSES/" + rule_id + "-" + str(number) + ".txt"] = path.read_bytes()
    for relative, content in payload.items():
        if isinstance(content, bytes):
            files[relative] = {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
    content_id = hashlib.sha256(json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    manifest = {"schema": 1, "format": "game-audio-library-offline", "content_id": content_id,
                "created_at": dt.datetime.now(dt.timezone.utc).isoformat(), "quality_minimum": 70,
                "asset_count": len(assets), "files": files, "assets": assets}
    payload[MANIFEST] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".audio-bundle-", suffix=".zip", dir=out_path.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temp_name, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
            for relative in sorted(payload):
                content = payload[relative]
                if isinstance(content, Path):
                    archive.write(content, ROOT + "/" + relative)
                else:
                    info = zipfile.ZipInfo(ROOT + "/" + relative)
                    info.create_system = 3
                    info.external_attr = (0o100755 if relative == "Install.command" else 0o100644) << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(info, content)
        with zipfile.ZipFile(temp_name) as archive:
            bad = archive.testzip()
            if bad:
                raise BundleError("ZIP CRC failed: " + bad)
        source = BundleSource(temp_name)
        try:
            validate_bundle(source)
        finally:
            source.close()
        # Verify source bytes again after archiving, including metadata snapshots.
        for relative, path, row, credit, rule, file_sha in eligible:
            if digest_file(path) != file_sha:
                raise BundleError("Source changed while exporting: " + relative)
        if index_path.read_bytes() != index_bytes or credit_path.read_bytes() != credits_bytes:
            raise BundleError("Library metadata changed while exporting; retry against a stable snapshot")
        zip_sha = digest_file(temp_name)
        os.link(temp_name, out_path)
        try:
            with sha_path.open("x", encoding="utf-8") as f:
                f.write(zip_sha + "  " + out_path.name + "\n")
        except Exception:
            out_path.unlink()
            raise
        return {"ok": True, "zip": str(out_path), "sha256_file": str(sha_path), "sha256": zip_sha,
                "bytes": out_path.stat().st_size, "content_id": content_id, "assets": len(assets),
                "kinds": dict(Counter(asset["kind"] for asset in assets)), "skipped": dict(skipped),
                "crc_verified": True, "member_list_verified": True, "source_bytes_verified": True}
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main():
    parser = argparse.ArgumentParser(description="导出可原样再分发的本地音效库离线ZIP；只读源库")
    parser.add_argument("--library", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--sources", required=True, help="已核实CC0/CC-BY再分发授权allowlist JSON")
    args = parser.parse_args()
    try:
        result = export_bundle(args.library, args.out, args.sources)
    except (BundleError, OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

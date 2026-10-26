#!/usr/bin/env python3
"""扫描 ~/GameAudioLibrary/raw，生成素材索引 index.csv，并给每个文件做音质分析和打分。

  python3 build_index.py            # 增量：只分析新增或改动过的文件
  python3 build_index.py --full     # 全部重新分析

index.csv 每行：路径、来源、素材包、标签、时长、响度(LUFS)、峰值、开头静音、
采样率、码率、授权、是否需署名、质量分(0-100)、质量问题。
没有授权记录的文件（不在 credits_master.csv 里）标记为 unknown，检索时默认排除。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import tempfile
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (AUDIO_EXT, CREDITS_MASTER, INDEX, RAW, classify_license, credits_by_file,  # noqa: E402
                    need_ffmpeg, read_csv, write_csv)
from audio_identity import family as audio_family  # noqa: E402

FIELDS = ["path", "source", "pack", "name", "tags", "kind", "duration", "lufs", "peak_db",
          "lead_silence", "clip", "sample_rate", "channels", "bitrate_kbps", "size_kb", "license",
          "attribution", "author", "url", "quality", "issues", "mtime",
          "file_sha256", "audio_id", "family_id", "themes", "analysis_error"]

# 文件名 / 文件夹名里的词 → 标签。检索时用标签匹配需求 ID。
TAG_WORDS = {
    "click": ["click", "tap", "button", "press", "select_", "ui_"],
    "pop": ["pop", "bubble", "plop", "blop", "bloop"],
    "coin": ["coin", "collect", "pickup", "pick_up", "gem", "money", "cash", "ding"],
    "win": ["win", "victory", "success", "complete", "fanfare", "level_up", "levelup", "achievement", "cheer"],
    "lose": ["lose", "lost", "fail", "game_over", "gameover", "defeat", "sad"],
    "invalid": ["error", "wrong", "denied", "invalid", "negative", "buzz", "no_"],
    "whoosh": ["whoosh", "swoosh", "swish", "swipe", "woosh", "transition"],
    "sparkle": ["sparkle", "magic", "twinkle", "shine", "glitter", "chime", "bell", "glow"],
    "place": ["drop", "place", "land", "thud", "put", "tock", "wood", "plunk"],
    "swap": ["swap", "switch", "slide", "move", "shift"],
    "match": ["match", "clear", "combo", "break", "burst", "crystal", "glass"],
    "jump": ["jump", "bounce", "spring"],
    "hit": ["hit", "impact", "punch", "hurt", "attack"],
    "shoot": ["shoot", "laser", "shot", "bullet"],
    "water": ["water", "splash", "liquid", "drink", "bubble"],
    "step": ["footstep", "step", "walk"],
    "door": ["door", "gate"],
    "star": ["star"],
    "tick": ["tick", "clock", "timer", "countdown", "beep"],
    "unlock": ["unlock", "open", "chest", "reward", "gift", "bonus", "powerup", "power_up"],
    "popup": ["popup", "pop_up", "open", "appear", "notification", "notify", "alert"],
    "close": ["close", "back", "cancel", "disappear"],
    "jingle": ["jingle", "sting", "stinger", "fanfare", "short"],
    "music": ["music", "bgm", "loop", "theme", "song", "track", "ost", "melody"],
    "cute": ["cute", "happy", "playful", "fun", "cartoon", "kids", "toy", "bouncy", "cheerful", "whimsical"],
    "retro": ["8bit", "8_bit", "chiptune", "retro", "arcade", "pixel", "nes"],
    "dark": ["horror", "dark", "scary", "evil", "battle", "epic", "metal", "gore", "creepy"],
}


THEME_PACKS = {p['key']: p for p in json.loads((Path(__file__).resolve().parent.parent / 'templates/theme-packs.json').read_text())['packs']}
# Older installed packs remain declared by packs.csv even without a themed manifest entry.
LEGACY_PACK_KINDS = {
    row["key"]: ("sfx" if row.get("type") == "sfx" else
                 "jingle" if row["key"] == "kenney_jingles" else "bgm")
    for row in read_csv(Path(__file__).resolve().parent.parent / "templates/packs.csv")
    if row.get("key") and row.get("type") in {"sfx", "music", "bgm", "jingle"}
}


def _values(value) -> list[str]:
    if isinstance(value, str):
        return [v for v in value.split("|") if v]
    return list(value or [])


def asset_config(path: Path) -> tuple[dict, dict]:
    parts = path.relative_to(RAW).parts
    key = parts[1] if len(parts) > 2 else ""
    pack = {"kind": LEGACY_PACK_KINDS[key]} if key in LEGACY_PACK_KINDS else {}
    pack.update(THEME_PACKS.get(key, {}))
    assets = pack.get("assets") or {}
    relative = "/".join(parts[2:])
    return pack, assets.get(relative, {})


def make_tags(path: Path) -> str:
    # Source site names (e.g. opengameart) are not sound descriptions.
    description = '/'.join(path.relative_to(RAW).parts[1:])
    description = re.sub(r'([a-z])([A-Z])', r'\1_\2', description)
    text = "_" + re.sub(r"[^a-z0-9]+", "_", description.lower()) + "_"
    pack, asset = asset_config(path)
    tags = []
    for tag, words in TAG_WORDS.items():
        # Metal material in an explicitly declared SFX pack is not heavy-metal music.
        # Every other existing dark keyword and explicit metadata tag still applies.
        if tag == "dark" and pack.get("kind") == "sfx":
            words = [word for word in words if word != "metal"]
        if any(re.search(r"_" + re.escape(w.strip('_')) + r"(?:s|es)?_", text) for w in words):
            tags.append(tag)
    tags += _values(asset.get("themes", pack.get("themes", [])))
    tags += _values(pack.get("tags", [])) + _values(asset.get("tags", []))
    if asset.get("kind", pack.get("kind")) == 'bgm':
        tags.append('music')
    return "|".join(dict.fromkeys(tags))


def analyze(path: Path) -> dict:
    """一次 ffmpeg 同时测：开头静音、峰值、积分响度。"""
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path), "-af",
         "silencedetect=n=-50dB:d=0.01,astats=metadata=0,volumedetect,ebur128=peak=sample", "-f", "null", "-"],
        capture_output=True, text=True, timeout=300)
    err = r.stderr
    out: dict = {}
    m = re.search(r"Input.*?Duration: (\d+):(\d+):([\d.]+).*?bitrate: (\d+) kb/s", err, re.S)
    if m:
        h, mi, s, br = m.groups()
        out["duration"] = round(int(h) * 3600 + int(mi) * 60 + float(s), 3)
        out["bitrate_kbps"] = int(br)
    m = re.search(r"Stream.*?Audio:.*?(\d+) Hz, (mono|stereo|[\d.]+)", err)
    if m:
        out["sample_rate"] = int(m.group(1))
        out["channels"] = 1 if m.group(2) == "mono" else 2
    m = re.search(r"Integrated loudness:\s+I:\s+(-?[\d.]+|-inf) LUFS", err)
    out["lufs"] = float(m.group(1)) if m and m.group(1) != "-inf" else -70.0
    peaks = re.findall(r"Peak level dB:\s+(-?[\d.]+|-inf)", err)
    out["peak_db"] = max((float(p) for p in peaks if p != "-inf"), default=-70.0)
    rms = re.findall(r"RMS level dB:\s+(-?[\d.]+|-inf)", err)
    # 削波：有大量采样顶在 0 dBFS
    m0 = re.search(r"histogram_0db:\s+(\d+)", err)
    out["clip"] = int(m0.group(1)) if m0 else 0
    # 短于 0.4 秒时 LUFS 测不出来（-70），用 RMS 估算，保证短音效也能比较响度
    if out["lufs"] <= -69 and rms:
        vals = [float(v) for v in rms if v != "-inf"]
        if vals:
            out["lufs"] = round(max(vals) - 3.0, 1)
    first_start = re.search(r"silence_start: (-?[\d.e-]+)", err)
    first_end = re.search(r"silence_end: ([\d.]+)", err)
    lead = 0.0
    if first_start and abs(float(first_start.group(1))) < 0.005 and first_end:
        lead = float(first_end.group(1))
    out["lead_silence"] = round(lead, 3)
    return out


def score(row: dict) -> tuple[int, str]:
    """质量打分：越高越好。只看客观指标，好不好听交给试听。"""
    s, issues = 100, []
    dur = float(row.get("duration") or 0)
    lufs = float(row.get("lufs") or -70)
    peak = float(row.get("peak_db") or -70)
    sr = int(row.get("sample_rate") or 0)
    br = int(row.get("bitrate_kbps") or 0)
    lead = float(row.get("lead_silence") or 0)
    if dur <= 0.02:
        return 0, "空文件或损坏"
    if lufs < -45:
        s -= 40; issues.append("几乎没声音")
    elif lufs < -35:
        s -= 15; issues.append("偏小声")
    if int(row.get("clip") or 0) >= 20 or (peak >= -0.05 and lufs > -10):
        s -= 35; issues.append("削波/爆音")
    elif peak >= -0.05:
        s -= 8; issues.append("峰值顶满")
    if sr and sr < 32000:
        s -= 20; issues.append(f"采样率低({sr})")
    if row["path"].lower().endswith((".mp3", ".ogg", ".m4a")) and 0 < br < 96:
        s -= 15; issues.append(f"码率低({br}k)")
    if dur < 8 and lead > 0.3:
        s -= 10; issues.append(f"开头静音{lead:.2f}s")
    if dur > 600:
        s -= 30; issues.append("过长(合集/长录音)")
    if "dark" in (row.get("tags") or ""):
        s -= 25; issues.append("风格偏暗/重")
    if row.get("license") == "unknown":
        s -= 50; issues.append("无授权记录")
    return max(s, 0), "；".join(issues)


def kind_of(dur: float, tags: str) -> str:
    if "jingle" in tags and 1.0 < dur <= 10:
        return "jingle"
    if dur <= 2.5:
        return "sfx"
    if dur <= 10 or "jingle" in tags:
        return "jingle"
    return "bgm"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def decoded_audio_id(path: Path) -> str:
    """Hash decoded mono/22050Hz/s16 PCM, never substitute an encoded-file hash."""
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-map", "0:a:0",
         "-ac", "1", "-ar", "22050", "-acodec", "pcm_s16le",
         "-f", "hash", "-hash", "sha256", "-"],
        capture_output=True, text=True, timeout=300)
    match = re.fullmatch(r"SHA256=([0-9a-fA-F]{64})\s*", result.stdout)
    if result.returncode or not match:
        raise ValueError("PCM decode/hash failed: " + result.stderr[-500:])
    # An empty stream has no meaningful playable-audio identity.
    if match.group(1).lower() == hashlib.sha256(b"").hexdigest():
        raise ValueError("PCM decode produced no samples")
    return "pcm-sha256:" + match.group(1).lower()


def declared_kind(duration: float, tags: str, declared: str) -> str:
    if declared in {"sfx", "ambience"}:
        return declared
    if declared == "bgm" and duration > 10:
        return "bgm"
    if declared == "jingle":
        tags += "|jingle"
    return kind_of(duration, tags)


def _snapshot(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


def _csv_snapshot(data: bytes | None) -> list[dict]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig")))) if data else []


def write_index_cas(rows: list[dict], expected_index: bytes | None,
                    expected_credits: bytes | None) -> None:
    """Prepare a complete CSV, then refuse stale writers before atomic publication."""
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".index-", suffix=".csv", dir=INDEX.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
            stream.flush()
            os.fsync(stream.fileno())
        if _snapshot(INDEX) != expected_index:
            raise RuntimeError("index.csv changed during indexing; refusing to overwrite concurrent work")
        if _snapshot(CREDITS_MASTER) != expected_credits:
            raise RuntimeError("credits_master.csv changed during indexing; refusing stale license publication")
        os.replace(temp, INDEX)
    finally:
        temp.unlink(missing_ok=True)


ANALYSIS_FIELDS = ("duration", "lufs", "peak_db", "lead_silence", "clip",
                   "sample_rate", "channels", "bitrate_kbps")


def build_index(*, full: bool = False, workers: int = 4) -> dict:
    expected_index, expected_credits = _snapshot(INDEX), _snapshot(CREDITS_MASTER)
    old = {r["path"]: r for r in _csv_snapshot(expected_index)}
    credits = {r["file"]: r for r in _csv_snapshot(expected_credits)}
    files = sorted(p for p in RAW.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXT)
    rows, todo = [], []
    # Complete source-byte identity is the cache key. mtime remains informational only.
    for path in files:
        digest = file_sha256(path)
        prev = old.get(str(path), {})
        if (not full and prev.get("file_sha256") == digest and prev.get("audio_id", "").startswith("pcm-sha256:")
                and not prev.get("analysis_error") and all(prev.get(k, "") != "" for k in ANALYSIS_FIELDS)):
            rows.append(_row(path, digest, credits, prev))
        else:
            todo.append((path, digest))

    def work(item) -> dict:
        path, digest = item
        previous = old.get(str(path), {})
        data = {key: previous[key] for key in ("family_id", "themes", "kind", "file_sha256")
                if key in previous} if previous.get("file_sha256") == digest else {}
        errors = []
        try:
            data.update(analyze(path))
        except Exception as error:
            errors.append("分析失败：" + str(error))
        try:
            data["audio_id"] = decoded_audio_id(path)
        except Exception as error:
            data["audio_id"] = ""
            errors.append(str(error))
        if file_sha256(path) != digest:
            raise RuntimeError("Audio source changed during analysis: " + str(path))
        data["analysis_error"] = "；".join(errors)
        return _row(path, digest, credits, data)

    print(f"素材总数 {len(files)}，需要分析 {len(todo)} 个…")
    with ThreadPoolExecutor(max(1, workers)) as executor:
        rows.extend(executor.map(work, todo))
    for row in rows:
        quality, issues = score(row)
        row["quality"] = quality
        row["issues"] = "；".join(filter(None, [issues, row.get("analysis_error", "")]))
    rows.sort(key=lambda row: row["path"])
    write_index_cas(rows, expected_index, expected_credits)
    return {"files": len(files), "analyzed": len(todo), "reused": len(files) - len(todo),
            "unknown": sum(row.get("license") == "unknown" for row in rows),
            "analysis_failures": sum(bool(row.get("analysis_error")) for row in rows)}


def _row(path: Path, digest: str, credits: dict, cached: dict) -> dict:
    parts = path.relative_to(RAW).parts
    pack, asset = asset_config(path)
    cr = credits.get(str(path), {})
    # A verified portable installer may rename characters for Windows. Reuse
    # same-byte metadata when an exact manifest asset key no longer exists.
    preserved = cached if cached.get("file_sha256") == digest else {}
    keep_portable = not asset and (not pack or bool(pack.get("assets")))
    theme_values = asset.get("themes", preserved.get("themes", pack.get("themes", [])) if keep_portable else pack.get("themes", []))
    # Preserve existing known CSV association when no replacement credit is present.
    lic = cr.get("license") or cached.get("license") or "unknown"
    _, attr, _ = classify_license(lic, allow_sa=True)
    row = {key: cached[key] for key in (*ANALYSIS_FIELDS, "audio_id", "analysis_error") if key in cached}
    row.update(path=str(path), source=parts[0], pack=parts[1] if len(parts) > 2 else "",
               name=asset.get("title") or path.stem, tags=make_tags(path),
               themes="|".join(dict.fromkeys(_values(theme_values))),
               size_kb=round(path.stat().st_size / 1024, 1), license=lic,
               attribution="yes" if attr else "no", author=cr.get("author", cached.get("author", "")),
               url=cr.get("url", cached.get("url", "")), mtime=str(int(path.stat().st_mtime)),
               file_sha256=digest)
    tags = row["tags"].split("|")
    if keep_portable and preserved.get("themes"):
        tags = [tag for tag in tags if tag not in _values(pack.get("themes", []))]
    row["tags"] = "|".join(dict.fromkeys([*tags, *_values(theme_values)]))
    declared = asset.get("kind", pack.get("kind", ""))
    if keep_portable and preserved.get("kind"):
        declared = preserved["kind"]
    row["kind"] = declared_kind(float(row.get("duration") or 0), row["tags"], declared)
    if asset.get("family_id") or preserved.get("family_id"):
        row["family_id"] = asset.get("family_id") or preserved["family_id"]
    row["family_id"] = audio_family(row)
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--workers", type=int, default=max(2, min(4, (os.cpu_count() or 4) // 2)))
    args = ap.parse_args()
    need_ffmpeg()
    result = build_index(full=args.full, workers=args.workers)
    print(f"✅ 索引完成：{INDEX}（{result['files']} 个文件，其中 {result['unknown']} 个无授权记录，检索时会排除）")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

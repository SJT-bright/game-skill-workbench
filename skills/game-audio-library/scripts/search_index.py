#!/usr/bin/env python3
"""按游戏的需求表（needs.csv），在本地素材库里给每个音频 ID 找候选。

  python3 search_index.py --needs needs.csv --out candidates.csv
  python3 search_index.py --needs needs.csv --style retro      # 像素/复古风游戏
  python3 search_index.py --needs needs.csv --prefer-pack kenney_interface

打分 = 标签匹配 + 关键词匹配 + 时长/类型合适 + 音质分 + 风格 + “同一素材包”加分。
同一素材包加分是为了让整个游戏的音效听感统一：脚本会自动找出覆盖需求最多的
1-2 个包，优先从里面选。

候选不足 3 个的 ID 会写进 needs_missing.csv，直接拿去给 fetch_*.py --batch 补下载。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import itertools
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import LIB, INDEX, classify_license, read_csv, write_csv  # noqa: E402
from audio_identity import identity, family, relative_asset_path


OUT_FIELDS = ["id", "type", "rank", "score", "path", "name", "source", "pack", "duration",
              "lufs", "quality", "license", "attribution", "author", "url", "issues",
              "audio_id", "file_sha256", "asset_id", "family_id", "themes", "match_mode", "matched_themes", "fit_priority"]

DUR_RANGE = {"sfx": (0.03, 2.5), "jingle": (0.8, 10.0), "bgm": (12.0, 600.0)}


STOP = {"soft", "sound", "sounds", "game", "short", "cute", "loop", "music", "background", "effect",
        "effects", "sfx", "wav", "mp3", "ogg", "the", "and", "for", "low", "light", "bright", "big",
        "small", "simple", "cartoon", "new", "item", "level"}


def words(s: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(w) > 2 and w not in STOP]


def base_score(item: dict, need: dict, style: str) -> float | None:
    if item.get("license") == "unknown" or not classify_license(item.get("license", ""))[0]:
        return None   # 无授权记录、不可商用、ND、SA 一律不进候选
    if float(item.get("quality") or 0) < 70:
        return None  # Keep flagged source audio for review, not automatic selection.
    t = need["type"]
    if t == "bgm" and item.get("kind") != "bgm":
        return None  # Long ambient effects must not become music candidates.
    dur = float(item.get("duration") or 0)
    lo, hi = DUR_RANGE[t]
    if need.get("max_sec"):
        hi = min(hi, float(need["max_sec"]) * (1.0 if t == "sfx" else 3.0))
    if not lo <= dur <= hi:
        return None
    itags = set((item.get("tags") or "").split("|"))
    ntags = [x for x in (need.get("tags") or "").split("|") if x]
    hit = [x for x in ntags if x in itags]
    name_words = set(words(item["path"]))
    kw_hit = sum(1 for w in set(words(need.get("keywords", ""))) if w in name_words)
    if not hit and kw_hit < 2:
        return None
    s = 40 + 10 * (len(hit) - 1) if hit else 0
    s += min(kw_hit * 6, 24)
    s += float(item.get("quality") or 0) * 0.4
    if item.get("kind") == t:
        s += 10
    if t in ("bgm", "jingle") and "music" in itags:
        s += 8
    if style == "cute" and "cute" in itags:
        s += 8
    if style == "retro":
        s += 12 if "retro" in itags else -6
    elif "retro" in itags:
        s -= 6           # 默认 Q 版可爱风，8-bit 音效略降权
    if "dark" in itags and "dark" not in ntags:
        s -= 30
    if item.get("attribution") == "no":
        s += 4
    return s


# Theme matching is a ranking dimension, not permission to replace a requested
# action with a different sound. Common music/cute tags do not prove a theme.
GENERIC_TAGS = {'music', 'bgm', 'sfx', 'jingle', 'cute', 'bright', 'soft', 'happy',
                'playful', 'cartoon', 'loop', 'any', 'sound', 'effect'}
ACTION_TAGS = {'click', 'pop', 'coin', 'win', 'lose', 'invalid', 'whoosh', 'sparkle',
               'place', 'swap', 'match', 'jump', 'hit', 'shoot', 'step', 'door',
               'star', 'tick', 'unlock', 'popup', 'close'}
MATERIALS = {'wood', 'metal', 'glass', 'paper', 'stone', 'plastic', 'rubber', 'water',
             'bubble', 'sand', 'snow', 'cloth', 'ceramic', 'ice', 'mechanical'}


def tagset(value):
    return {v.strip().lower() for v in str(value or '').split('|') if v.strip()}


def known_themes():
    path = Path(__file__).resolve().parent.parent / 'templates/theme-packs.json'
    return {t for pack in json.loads(path.read_text(encoding='utf-8'))['packs']
            for t in (set(pack.get('themes', [])) | {theme for asset in pack.get('assets', {}).values() for theme in asset.get('themes', [])})} - GENERIC_TAGS


def fit(item, need, themes):
    itags = tagset(item.get('tags'))
    ntags = tagset(need.get('tags'))
    wanted = tagset(need.get('themes')) | (ntags & themes)
    present = tagset(item.get('themes')) | (itags & themes)
    matched = wanted & present
    if need['type'] in {'sfx', 'jingle'}:
        actions = ntags & ACTION_TAGS
        hits = actions & itags
        if actions and not hits:
            return None  # A theme hit cannot make a laser into a UI click.
        material = (ntags | set(words(need.get('keywords', '')))) & MATERIALS
        material_hits = material & (itags | set(words(item.get('name', ''))))
        priority = (len(hits), len(material_hits), bool(matched))
    else:
        # Explicitly matching tracks first, unclassified music second, other
        # declared themes last. Existing quality/licence/duration gates still run.
        priority = ((2 if matched else 1 if not present else 0) if wanted else 1,
                    len(matched), 0)
    mode = 'theme_match' if matched else 'generic' if not wanted else 'fallback_unclassified' if not present else 'fallback_other_theme'
    return priority, mode, sorted(matched), sorted(wanted)


def history_counts(index, recent):
    by_path = {str(row['path']): row for row in index}
    by_relative = {}
    for row in index:
        try:
            by_relative[relative_asset_path(row['path'])] = row
        except ValueError:
            continue
    asset_uses, family_uses = Counter(), Counter()
    for doc in recent:
        assets = set(doc.get('asset_ids', []))
        families = set(doc.get('family_ids', []))
        for value in doc.get('paths', []):
            row = by_path.get(value)
            if row is None:
                try:
                    row = by_relative.get(relative_asset_path(value))
                except ValueError:
                    # Historical path before the library was relocated. These
                    # records were produced from RAW, so its suffix is portable.
                    suffix = str(value).replace('\\', '/').split('/raw/', 1)
                    if len(suffix) == 2:
                        row = by_relative.get('raw/' + suffix[1])
            if row is not None:
                if not doc.get('asset_ids'):
                    assets.add(identity(row))
                if not doc.get('family_ids'):
                    families.add(family(row))
        asset_uses.update(assets); family_uses.update(families)
    return asset_uses, family_uses


def rank_candidates(index, needs, style, project, recent=(), prefer_packs=(), per_id=6, themes=None):
    themes = known_themes() if themes is None else set(themes)
    used_assets, used_families = history_counts(index, recent)
    used_packs = Counter(pack for doc in recent[:8] for pack in doc.get('packs', []))
    scored = {}
    for need in needs:
        compatible = []
        for item in index:
            try:
                if not all(math.isfinite(float(item.get(k) or 0)) for k in ('quality', 'duration')):
                    continue
                score = base_score(item, need, style)
                suitability = fit(item, need, themes) if score is not None else None
                if suitability is not None:
                    compatible.append((score, item, suitability))
            except (ValueError, TypeError, KeyError):
                continue  # Malformed index data is never an eligible sound.
        compatible.sort(key=lambda entry: (entry[2][0], entry[0]), reverse=True)
        scored[need['id']] = compatible
    cover = Counter()
    for need in needs:
        if need['type'] == 'sfx':
            cover.update({f"{it['source']}/{it['pack']}" for _, it, _ in scored[need['id']][:15] if it.get('pack')})
    prefer = {p for p, n in cover.most_common(2) if n >= 3} | set(prefer_packs)
    rows, missing, details = [], [], []
    for need in needs:
        ranked = []
        for score, item, suitability in scored[need['id']]:
            key = f"{item['source']}/{item['pack']}"
            if key in prefer or item.get('pack') in prefer:
                score += 6
            uses = max(used_assets[identity(item)], used_families[family(item)])
            score -= min(uses * (24 if need['type'] == 'bgm' else 14), 60)
            score -= min(used_packs[key] * 3, 12)
            salt = hashlib.sha256((project + '|' + need['id'] + '|' + identity(item)).encode()).hexdigest()
            score += int(salt[:8], 16) / 0xffffffff * 6
            ranked.append((score, item, suitability))
        ranked.sort(key=lambda entry: (entry[2][0], entry[0]), reverse=True)
        picked = []
        seen_assets, seen_families = set(), set()
        for _, entries in itertools.groupby(ranked, key=lambda entry:entry[2][0]):
            primary, alternatives = [], []
            for entry in entries:
                _, item, _ = entry
                asset, group = identity(item), family(item)
                if asset in seen_assets:
                    continue
                seen_assets.add(asset)
                if group in seen_families:
                    if need['type'] != 'bgm':
                        alternatives.append(entry)
                    continue
                seen_families.add(group);primary.append(entry)
            # Spread families only within equal semantic suitability. A different
            # material/theme must not overtake an appropriate alternate take.
            picked.extend(primary + alternatives)
        picked = picked[:per_id]
        for rank, (score, item, suitability) in enumerate(picked, 1):
            rows.append({**{key:item.get(key, '') for key in OUT_FIELDS}, 'id':need['id'], 'type':need['type'],
                         'rank':rank, 'score':round(score, 1), 'asset_id':identity(item), 'family_id':family(item),
                         'match_mode':suitability[1], 'matched_themes':'|'.join(suitability[2]),
                         'fit_priority':'|'.join(str(int(value)) for value in suitability[0])})
        family_count = len({family(item) for _, item, _ in picked})
        detail = {'id':need['id'], 'candidates':len(picked), 'distinct_families':family_count,
                  'requested_themes':sorted(tagset(need.get('themes')) | (tagset(need.get('tags')) & themes)),
                  'theme_matches':sum(entry[2][1] == 'theme_match' for entry in picked),
                  'fallback':bool(picked and picked[0][2][1].startswith('fallback_'))}
        details.append(detail)
        if len(picked) < 3:
            missing.append(need)
    return rows, missing, details


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--needs', required=True)
    ap.add_argument('--out', default='candidates.csv')
    ap.add_argument('--style', choices=['cute', 'retro', 'any'], default='cute')
    ap.add_argument('--per-id', type=int, default=6)
    ap.add_argument('--prefer-pack', action='append', default=[])
    ap.add_argument('--project', help='Stable game identity for cross-game diversity')
    args = ap.parse_args()
    if args.per_id < 1:
        ap.error('--per-id must be positive')
    index = read_csv(INDEX)
    needs = read_csv(Path(args.needs))
    if not index:
        raise SystemExit('索引为空：先安装本地音效库，再运行 build_index.py')
    if not needs or any(not row.get('id') or row.get('type') not in DUR_RANGE for row in needs) or len({row['id'] for row in needs}) != len(needs):
        raise SystemExit('需求表为空、ID重复或类型无效，未生成候选')
    project = str(Path(args.project).resolve()) if args.project else str(Path(args.needs).resolve().parent.parent)
    recent = []
    for record in sorted((LIB/'usage').glob('*.json'), key=lambda f:f.stat().st_mtime, reverse=True)[:20]:
        try:
            doc = json.loads(record.read_text(encoding='utf-8'))
            if doc.get('project') != project:
                recent.append(doc)
        except (OSError, ValueError):
            continue
    rows, missing, details = rank_candidates(index, needs, args.style, project, recent, args.prefer_pack, args.per_id)
    write_csv(Path(args.out), rows, OUT_FIELDS)
    report = Path(args.out).with_suffix('.fit.json')
    report.write_text(json.dumps({'project':project, 'needs':details, 'scope':'ranking and explicit fallback; not proof of listening or game output'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for item in details:
        print(f"{item['id']}: 候选{item['candidates']}、独立家族{item['distinct_families']}" + ('；题材不足，使用已标明回退' if item['fallback'] else ''))
    missing_path = Path(args.out).with_name('needs_missing.csv')
    if missing:
        write_csv(missing_path, missing, list(needs[0]))
    else:
        missing_path.unlink(missing_ok=True)
    print('候选与匹配说明已写入 ' + str(args.out))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Check that every audio file in the game has a recorded, commercially usable source.

Read-only. Scans PROJECT/assets for audio files. Each file must be covered by:
  1. docs/audio/credits.csv written by the game-audio-library pipeline (column "outputs"
     lists the game files made from each source; "license" must be allowed), or
  2. a line in docs/audio/sources.md naming the file. For a localize game (英化) audio kept from the original
     game or supplied by the starter pack may be written "原游戏自带" / "启动包提供" (plus the licence when known).
  Synthesized/AI-made, NC/ND/personal-use, CC-BY-SA and "待下载" are rejected.
The licence rules mirror game-audio-library/scripts/common.py classify_license.

board remake (重塑, v7.8 总表 H7; Saul: pick from ~/GameAudioLibrary, keep no sound of the base game, avoid sounds other
games already use) adds, for every audio file:
  - "原游戏自带" / "启动包提供" / "original game" / "starter pack" is not a source: replace the sound from the library.
    A starter pack's own sounds (copied unchanged from a workshop / light pack) pass once
    remake-game/scripts/starter_audio_credits.py has written their library source into credits.csv (Saul 10-30);
    a sound of the base game itself never does.
  - the source must be found in the library's index.csv, by the credits.csv row (library_path / original_path /
    source_path / file / source_file, source_sha256 / original_sha256, "pack / name" title, pack + name, file name
    narrowed by source and url / source_url, url alone) or by the game file's own sha256 (a raw copy). Not found =
    problem. The credits.csv headers seen in the games (8 kinds, 2026-10-30) all resolve through these columns.
  - the library row's licence must be allowed too, and need no attribution (Saul: CC0 / commercial use / no
    attribution only): a licence or library row that needs attribution is a problem.
  - reuse, from the library's usage/*.json (one record per project that took sounds): the same file (path) or the
    same decoded audio (asset id) used by 2 or more OTHER games = problem; by 1 other game = warning. One game counts
    once however many folders it had (working copy, audio work folder, the folder after it moved into ！交付游戏).
  - a credits.csv path that is not where the file really is (matched by file name) = warning; a credits "outputs"
    path with no file behind it = warning.
  New games fail on these problems; a game on LEGACY_GAMES.json gets them as warnings (tiktok_finalize_steps.policy).
board localize keeps the rules above the remake paragraph unchanged.
The board is --board, else PROJECT/docs/board.txt, else remake (the strictest, as preflight.py does).
The library is --library, else $GAME_AUDIO_LIB, else ~/.game-audio-library/library.json, else ~/GameAudioLibrary
(the same lookup as game-audio-library/scripts/common.py library_root). A remake check with no index.csv fails.

Usage:
  python audit_audio_sources.py --project GAME_PROJECT [--board remake|localize] [--library DIR]
                                [--binding review.json] [--out result.json]

Exit codes: 0 all recorded and allowed, 1 problems found, 2 bad input or output exists.
It does not listen to audio or verify how attribution is presented; attribution-required files are counted for downstream licence review.
Loudness and fail-sound length of the finished package are checked by package_gates/audio.py when the package is written.
"""
import argparse
import csv
import hashlib
import json
import os
import re
from pathlib import Path

AUDIO = {'.mp3', '.ogg', '.wav', '.m4a', '.aac', '.flac'}
SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', 'audio-inbox', 'audio_work'}
DENY = [r'\bnc\b', r'non[- ]?commercial', r'personal use', r'editorial', r'\bnd\b', r'no[- ]?deriv',
        r'sampling\+', r'\bsa\b', r'share[- ]?alike']
FREE = [r'\bcc0\b', r'public ?domain', r'\bpdm\b', r'pixabay', r'mixkit', r'kenney', r'sonniss',
        r'99sounds', r'bigsoundbank', r'royalty[- ]?free']
ATTR = [r'\bcc[- ]?by\b', r'oga[- ]?by', r'attribution', r'zapsplat', r'incompetech', r'soundimage', r'noiseforfun']
KEPT = re.compile(r'原游戏自带|启动包提供|original game|starter pack', re.I)
NOT_REAL = re.compile(r'synth|generated|numpy|scipy|\bai[- ]?(made|generated|music|audio)\b|合成|生成|待下载', re.I)
BOARDS = ('remake', 'localize')
GAMES_ROOT_NAME = '！自制游戏'
DELIVERED = ('！交付游戏', '！成功完结游戏')
GENERIC_DIRS = {'game', 'audio', 'audio-project', 'audio_project', 'audio-proj', 'audio-refresh', 'audio_out', 'light',
                'work', '_work', 'fix-work', 'stage', 'source', 'src', 'project', 'projects', '工程', '选音工程', '音频',
                '3_音频', '工作工程', '本地预览', '.candidates', 'candidates', 'downloads', 'desktop'}
SKIP_USAGE = re.compile(r'/\.kiro/crew/scratch/|/release-selftest/', re.I)


def licence(text):
    """(allowed, attribution_required, reason)"""
    t = (text or '').lower().replace('_', ' ')
    if not t.strip():
        return False, False, 'empty licence'
    for p in DENY:
        if re.search(p, t):
            return False, False, 'not allowed: ' + p
    if NOT_REAL.search(t):
        return False, False, 'synthesized/AI-made or pending download'
    if any(re.search(p, t) for p in FREE):
        return True, False, ''
    if any(re.search(p, t) for p in ATTR):
        return True, True, ''
    return False, False, 'unknown licence: ' + text


def scan(project):
    root = project / 'assets'
    if not root.is_dir():
        raise ValueError(f'no assets folder in {project}')
    return [p for p in sorted(root.rglob('*'))
            if p.suffix.lower() in AUDIO and p.is_file()
            and not SKIP_DIRS & {x.lower() for x in p.relative_to(project).parts}]


# ---------------------------------------------------------------- remake: library, usage, game identity

def library_root(given=None):
    if given:
        return Path(given).expanduser().resolve()
    override = os.environ.get('GAME_AUDIO_LIB')
    if override:
        return Path(override).expanduser().resolve()
    config = Path.home() / '.game-audio-library' / 'library.json'
    if config.is_file():
        try:
            value = json.loads(config.read_text(encoding='utf-8')).get('library')
            if isinstance(value, str) and value.strip():
                return Path(value).expanduser().resolve()
        except (OSError, ValueError, AttributeError):
            pass
    return (Path.home() / 'GameAudioLibrary').resolve()


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


class Library:
    def __init__(self, root):
        self.root = root
        self.rows, self.by_path, self.by_name, self.by_sha, self.by_pack_name, self.by_url = [], {}, {}, {}, {}, {}
        index = root / 'index.csv'
        self.ok = index.is_file()
        if self.ok:
            with index.open(newline='', encoding='utf-8-sig') as f:
                self.rows = list(csv.DictReader(f))
        for row in self.rows:
            path = (row.get('path') or '').strip()
            if not path:
                continue
            self.by_path[path] = row
            self.by_name.setdefault(Path(path).name.lower(), []).append(row)
            if row.get('file_sha256'):
                self.by_sha.setdefault(row['file_sha256'].strip().lower(), row)
            key = ((row.get('pack') or '').strip().lower(), (row.get('name') or '').strip().lower())
            self.by_pack_name.setdefault(key, []).append(row)
            if (row.get('url') or '').strip():
                self.by_url.setdefault(row['url'].strip(), []).append(row)
        self.usage = []          # [(project path, set of library paths, set of asset ids)]
        for f in sorted((root / 'usage').glob('*.json')) if (root / 'usage').is_dir() else []:
            try:
                d = json.loads(f.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                continue
            if not isinstance(d, dict):
                continue
            proj = str(d.get('project') or d.get('game') or f.stem)
            if SKIP_USAGE.search(proj.replace('\\', '/')):
                continue         # test fixtures and Skill self-tests are not games
            self.usage.append((proj, {str(p) for p in d.get('paths') or []},
                               {str(x) for x in d.get('asset_ids') or []}))

    def path_row(self, value):
        value = (value or '').strip()
        if not value:
            return None
        if value in self.by_path:
            return self.by_path[value]
        try:
            resolved = str(Path(value).expanduser().resolve())
        except (OSError, RuntimeError):
            return None
        return self.by_path.get(resolved)


def _norm_part(name):
    name = re.sub(r'[（(]\s*自制\s*[)）]', '', name).strip()
    person = re.match(r'^(?:待-)?\d+[^-_\d][^-_]*-(.+)$', name)    # "1Akira-BarleysBubble", "2子午-Pinecone": drop the person
    if person:
        name = person.group(1)
    name = re.sub(r'^新?\d+[_\-\s]*', '', name)
    parts = [p for p in re.split(r'[-_\s]+', name) if p]
    skip = re.compile(r'^(\d+|v\d.*|r\d+|fix\d*|audio\d*|art\d*|gameplay|balance|economy|refresh|source|en|tiktok|test|'
                      r'starterpack|final|cocos|redesign|light|work)$', re.I)
    kept = [p for p in parts if not skip.match(p)]
    latin = [p for p in kept if len(re.sub(r'[^A-Za-z]', '', p)) >= 4]
    # Latin game name first; a Chinese name keeps all its parts (新游戏_底子全民飞车漂移 and 新游戏_底子我出枪贼快 are two games)
    pick = latin[0] if latin else (''.join(kept) if kept else name)
    return re.sub(r'[^0-9a-z\u4e00-\u9fff]', '', pick.lower())


def game_key(path):
    """One game, many folders: the game folder under ！自制游戏 (or under ！交付游戏 / ！成功完结游戏 after delivery, or
    启动包工坊/projects/<name>), else the nearest folder that is not a generic work folder. Normalised: "（自制）",
    "新260_" and a person prefix "1仁木-" are dropped, the Latin game name is preferred (新260_MeteorBlaster and
    新260-MeteorBlaster（自制） are one game)."""
    parts = [p for p in str(path).replace('\\', '/').rstrip('/').split('/') if p]
    if GAMES_ROOT_NAME in parts:
        rest = parts[parts.index(GAMES_ROOT_NAME) + 1:]
        if rest and rest[0] in DELIVERED and len(rest) > 1:
            return _norm_part(rest[1])
        if len(rest) > 2 and rest[0] == '启动包工坊' and rest[1] == 'projects':
            return _norm_part(re.sub(r'^fusion-', '', rest[2]))
        if rest:
            return _norm_part(rest[0])
    for part in reversed(parts):
        if part.lower() not in GENERIC_DIRS:
            return _norm_part(part)
    return str(path)


def same_game(a, b):
    if not a or not b:
        return False
    return a == b or (min(len(a), len(b)) >= 5 and (a.startswith(b) or b.startswith(a)))


def resolve_source(lib, row, game_file_sha, own_paths):
    """credits.csv row (may be None) + the game file's sha256 -> (index row or None, how)."""
    row = row or {}
    for col in ('library_path', 'original_path', 'source_path', 'file'):
        hit = lib.path_row(row.get(col))
        if hit:
            return hit, col
    for col in ('source_sha256', 'original_sha256'):
        v = (row.get(col) or '').strip().lower()
        if v and v in lib.by_sha:
            return lib.by_sha[v], col
    if game_file_sha in lib.by_sha:
        return lib.by_sha[game_file_sha], 'game file sha256'
    cands = []
    how = ''
    source_file = (row.get('source_file') or '').strip().replace('\\', '/')
    if source_file:
        cands = [r for r in lib.by_name.get(Path(source_file).name.lower(), [])
                 if (r.get('path') or '').replace('\\', '/').lower().endswith(source_file.lower())]
        how = 'source_file'
    if not cands:
        title = (row.get('title') or '').strip()
        if ' / ' in title:
            pack, name = title.split(' / ', 1)
            cands = lib.by_pack_name.get((pack.strip().lower(), name.strip().lower()), [])
            how = 'title pack / name'
    if not cands and row.get('pack') and row.get('name'):
        cands = lib.by_pack_name.get((row['pack'].strip().lower(), row['name'].strip().lower()), [])
        how = 'pack + name'
    if not cands:
        for col in ('file', 'original_path', 'library_path', 'source_path'):
            v = (row.get(col) or '').strip()
            if v:
                cands = lib.by_name.get(Path(v.replace('\\', '/')).name.lower(), [])
                how = 'file name (%s)' % col
                if cands:
                    break
    if len(cands) > 1:
        src = (row.get('source') or '').strip().lower()
        if src:
            top, _, pack = src.partition('/')
            narrowed = [c for c in cands if (c.get('source') or '').lower() == top and
                        (not pack or (c.get('pack') or '').lower() == pack)]
            cands = narrowed or cands
    url = (row.get('url') or row.get('source_url') or '').strip()
    if len(cands) > 1 and url:
        cands = [c for c in cands if (c.get('url') or '').strip() == url] or cands
    if not cands and url and url in lib.by_url:          # header "outputs,license,author,source_url,license_url"
        cands = lib.by_url[url]
        how = 'url'
    if len(cands) > 1:
        cands = [c for c in cands if c.get('path') in own_paths] or cands
    if cands:
        return sorted(cands, key=lambda c: c.get('path') or '')[0], how
    return None, ''


def decide_policy(project):
    try:
        import sys
        here = str(Path(__file__).resolve().parent)
        if here not in sys.path:
            sys.path.insert(0, here)
        from tiktok_finalize_steps import policy as _P
        out = _P.decide(project=project)
        return out['policy'], out['reason']
    except Exception as error:  # noqa: BLE001 - a broken decision never makes a game legacy
        return 'new', 'policy decision failed (%r) -> new game' % (error,)


def read_board(project, given):
    if given:
        return given, '--board'
    try:
        text = (project / 'docs' / 'board.txt').read_text(encoding='utf-8').strip().lower()
    except OSError:
        text = ''
    if text in BOARDS:
        return text, 'docs/board.txt'
    return 'remake', 'no --board and no docs/board.txt: checked as remake (strictest)'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--board', choices=BOARDS, help='remake | localize; default docs/board.txt, else remake')
    ap.add_argument('--library', type=Path, help='GameAudioLibrary folder (default as game-audio-library finds it)')
    ap.add_argument('--binding', type=Path, help='known-issue review JSON whose "binding" is copied into the report')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    try:
        if a.out and a.out.exists():
            raise ValueError(f'output exists: {a.out}')
        binding = None
        if a.binding:
            binding = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
            if not isinstance(binding, dict):
                raise ValueError(f'no binding object in {a.binding}')
        files = scan(a.project)
        credits_csv = a.project / 'docs/audio/credits.csv'
        rows = []
        if credits_csv.is_file():
            with credits_csv.open(newline='', encoding='utf-8-sig') as f:
                rows = list(csv.DictReader(f))
        sources_md = a.project / 'docs/audio/sources.md'
        lines = sources_md.read_text(encoding='utf-8-sig').splitlines() if sources_md.is_file() else []
    except (OSError, ValueError, csv.Error) as e:
        print(json.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False))
        return 2
    board, board_by = read_board(a.project, a.board)
    remake = board == 'remake'

    by_output = {}
    for r in rows:
        for out in re.split(r'[;|]' if remake else ';', r.get('outputs') or ''):   # localize: v7.7.5 rule as is
            if out.strip():
                by_output.setdefault(out.strip().replace('\\', '/'), []).append(r)
    lib = policy = policy_reason = None
    own_key, own_paths, warnings = None, set(), []
    if remake:
        lib = Library(library_root(a.library))
        policy, policy_reason = decide_policy(a.project)
        own_key = game_key(a.project.resolve())
        project_text = str(a.project.resolve())
        for proj, paths, _ids in lib.usage:
            if proj == project_text or same_game(game_key(proj), own_key):
                own_paths |= paths
        actual = {f.relative_to(a.project).as_posix() for f in files}
        actual_names = {f.name for f in files}       # a moved file gets the "write the real path" warning instead
        for out in sorted(by_output):
            if out not in actual and out.startswith('assets/') and Path(out).name not in actual_names:
                warnings.append({'path': out, 'warning': 'credits.csv "outputs" names a file that is not in the project'})
    checks, attribution = [], 0
    for f in files:
        rel = f.relative_to(a.project).as_posix()
        problem, attr, extra, remake_problems = '', False, {}, []
        recs = by_output.get(rel)
        if not recs and remake:            # moved file, credits not updated: match by file name, report the path
            same = [r for out, rs in by_output.items() if Path(out).name == f.name for r in rs]
            if len({id(r) for r in same}) == 1:
                recs = same[:1]
                listed = [out for out, rs in by_output.items() if Path(out).name == f.name]
                warnings.append({'path': rel, 'warning': 'credits.csv lists it as %s; write the real path' % listed[0]})
        hits = []
        if recs:
            results = [licence(r.get('license', '')) for r in recs]
            bad = [why for ok, _, why in results if not ok]
            problem = ('credits.csv: ' + bad[0]) if bad else ''
            attr = any(x[1] for x in results)
        else:
            hits = [x for x in lines if f.name in x]
            if not hits:
                problem = 'no record in docs/audio/credits.csv or docs/audio/sources.md'
            elif any(NOT_REAL.search(x) or any(re.search(p, x.lower()) for p in DENY) for x in hits):
                problem = 'sources.md marks it synthesized/pending or NC/ND/SA/personal-use'
            elif any(KEPT.search(x) for x in hits):
                problem = ''
                if remake:
                    remake_problems.append('sources.md says it is kept from the base game / starter pack; a remake keeps '
                                           'no base sound: pick a replacement from the audio library')
            else:
                results = [licence(x) for x in hits]
                problem = '' if any(ok for ok, _, _ in results) else 'sources.md: no allowed licence on its line'
                attr = any(ok and need for ok, need, _ in results)
        if remake and not problem and not remake_problems:
            if not lib.ok:
                remake_problems.append('no index.csv in the audio library %s, so the source cannot be checked' % lib.root)
            else:
                file_sha = sha256(f)
                found, how = None, ''
                for r in recs or [None]:
                    found, how = resolve_source(lib, r, file_sha, own_paths)
                    if found:
                        break
                if not found and hits:      # sources.md line: try every audio file name written on it
                    for line in hits:
                        for name in re.findall(r'[\w.\-]+\.(?:mp3|ogg|wav|m4a|aac|flac)', line, re.I):
                            found, how = resolve_source(lib, {'file': name}, file_sha, own_paths)
                            if found:
                                break
                        if found:
                            break
                if not found:
                    remake_problems.append('source not found in %s (credits.csv needs the library file: file / '
                                           'library_path / original_path / source_sha256)' % (lib.root / 'index.csv'))
                else:
                    src = found.get('path') or ''
                    asset_id = (found.get('audio_id') or '').strip()
                    extra = {'library_path': src, 'matched_by': how}
                    ok, need, why = licence(found.get('license', ''))
                    if not ok:
                        remake_problems.append('library index.csv licence of %s: %s' % (src, why))
                    elif need or attr or (found.get('attribution') or '').strip().lower() in ('yes', 'true', '1',
                                                                                              '是', 'required'):
                        remake_problems.append('source %s needs attribution (%s); a remake uses CC0 / commercial-use '
                                               'sounds that need no attribution: pick another from the library'
                                               % (src, found.get('license', '')))
                    others = sorted({game_key(proj) for proj, paths, ids in lib.usage
                                     if (src in paths or (asset_id and asset_id in ids))
                                     and proj != str(a.project.resolve())
                                     and not same_game(game_key(proj), own_key)})
                    if others:
                        extra['used_by_other_games'] = others
                    if len(others) >= 2:
                        remake_problems.append('the library sound %s is already used by %d other games (%s); pick one '
                                               'fewer games use' % (src, len(others), ', '.join(others[:6])))
                    elif others:
                        warnings.append({'path': rel, 'warning': 'the library sound %s is used by 1 other game (%s)'
                                         % (src, others[0])})
        if remake_problems:
            if policy == 'new':
                problem = '; '.join(remake_problems)
            else:
                warnings.extend({'path': rel, 'warning': '(legacy game) ' + p} for p in remake_problems)
        attribution += 1 if attr and not problem else 0
        check = {'path': rel, 'passed': not problem, 'problem': problem, 'attribution_required': attr}
        check.update(extra)
        checks.append(check)
    failed = sum(1 for c in checks if not c['passed'])
    report = {'tool': 'audit_audio_sources', 'checked': len(checks), 'failed': failed, 'passed': failed == 0,
              'attribution_required': attribution, 'board': board, 'board_from': board_by, 'checks': checks,
              'warnings': warnings,
              'note': 'Checks source records only. Keep attribution records and satisfy each licence; use a permitted player-visible location if required, or replace the asset. This check does not verify presentation.'}
    if remake:
        report.update({'policy': policy, 'policy_reason': policy_reason, 'library': str(lib.root),
                       'game': own_key})
    if binding is not None:
        report['binding'] = binding
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'checked': len(checks), 'failed': failed, 'attribution_required': attribution, 'board': board,
                      'policy': policy, 'warnings': len(warnings),
                      'problems': [c for c in checks if not c['passed']][:15], 'first_warnings': warnings[:10]},
                     ensure_ascii=False))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())

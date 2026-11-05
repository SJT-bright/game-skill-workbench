#!/usr/bin/env python3
"""Bring a sound from the audio library into a game and record where it came from, in ONE step (生成时预防方案 P15).

The AI runs this itself; the user never runs commands.

  python3 import_audio.py --project <Cocos project> --file <library file> [--file ...] [--dest assets/resources/audio]
                          [--as NAME] [--kind sfx|music|jingle] [--fail | --result] [--library DIR] [--no-usage]
                          [--allow-reuse]

Why: in the 2026-11-04 census 18 games had sounds copied into assets/ with no recorded source, and the package gate
audit_audio_sources.py (AUDIO-02) only caught it when the package was written; 10+ games had a fail sound of 3-5 s.
Here the copy and the record cannot be separated: a sound only lands in the project together with its
docs/audio/credits.csv row (library path, licence, author, url, source SHA-256, output SHA-256), and the library's
usage/ record is written in the same run. Per file:
  1. the library row is found in <library>/index.csv (by path, else by the file's SHA-256). Not in the index = refused:
     no source, no licence. The licence must be commercial use without attribution (the gate's own rules,
     audit_audio_sources.licence); NC / ND / SA / attribution / synthesized are refused.
  2. reuse, from <library>/usage/*.json, the gate's way (same file path or same audio_id, one game counted once):
     1 other game = warning printed; 2 or more = refused (the gate fails a new remake game on it) unless --allow-reuse.
  3. a fail sound (name with fail / lose / gameover / timeout ..., the gate's list, or --fail) and a result / win sound
     (win / victory / complete / clear / success / result ..., or --result) longer than 2.0 s is cut to 2.0 s with a
     0.35 s fade-out (package_gates/audio.py FAIL_TARGET_SECONDS / FAIL_FADE_SECONDS). WAV is cut in Python; other
     formats need ffmpeg (found like the package gate does). Other sounds are copied byte for byte.
  4. the file is written to <dest>/<name>, the credits.csv row added (other rows and columns kept; a row for the same
     output replaced), then the usage record <library>/usage/<sha256(project|import_audio)>.json updated
     (skipped with --no-usage, e.g. on a trial copy). If any file of the run is refused, nothing is written.
  5. (P04) each file is added to the size ledger docs/startup/budget.json (startup_budget.py) with its bytes, as
     "deferred" (AudioService loads sound after the first frame). A file that would push the first download (main
     package + subpackages requested before the home page) over 10 MiB is refused before anything is written; a
     sound that lands in the first download is a warning (put the audio folder in a ByteDance subpackage bundle).
The library is --library, else $GAME_AUDIO_LIB, else ~/.game-audio-library/library.json, else ~/GameAudioLibrary (the
gate's lookup; no machine path is written here). Prints one JSON line. Exit: 0 imported, 1 refused, 2 bad input.
"""
from __future__ import annotations

import argparse
import array
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import audit_audio_sources as gate  # noqa: E402  same library lookup, licence rules, game identity as AUDIO-02
from package_gates import audio as pkg_audio  # noqa: E402  fail-sound words and the 2 s rule
import startup_budget as budget  # noqa: E402  P04 size ledger docs/startup/budget.json

CUT_SECONDS = pkg_audio.FAIL_TARGET_SECONDS
FADE_SECONDS = pkg_audio.FAIL_FADE_SECONDS
RESULT_TOKENS = set(pkg_audio.JINGLE_TOKENS) | {'result', 'results', 'settle', 'settlement', 'levelup', 'finish',
                                                'finished', 'end', 'ending', 'gameend', 'reward'}
CREDIT_FIELDS = ['id', 'type', 'title', 'author', 'source', 'license', 'attribution_required', 'url', 'library_path',
                 'source_sha256', 'outputs', 'output_sha256', 'notes']
PART = 'import_audio'


def sha256_file(path: Path) -> str:
    return gate.sha256(path)


def rel(project: Path, path: Path) -> str:
    return path.resolve().relative_to(project.resolve()).as_posix()


# ---------------------------------------------------------------- cutting

def wav_seconds(path: Path) -> float:
    with wave.open(str(path), 'rb') as w:
        return w.getnframes() / float(w.getframerate())


def cut_wav(src: Path, out: Path, seconds: float, fade: float) -> None:
    """Keep the first `seconds`, linear fade-out over the last `fade` seconds. 8 / 16 / 32-bit PCM."""
    with wave.open(str(src), 'rb') as r:
        params = r.getparams()
        width, ch, rate = r.getsampwidth(), r.getnchannels(), r.getframerate()
        keep = min(r.getnframes(), int(round(seconds * rate)))
        data = r.readframes(keep)
    code = {1: 'B', 2: 'h', 4: 'i'}.get(width)
    if not code:
        raise ValueError('%s: %d-bit WAV is not supported without ffmpeg' % (src.name, width * 8))
    samples = array.array(code)
    samples.frombytes(data)
    if sys.byteorder == 'big' and width > 1:
        samples.byteswap()
    fade_frames = max(1, min(keep, int(round(fade * rate))))
    start = keep - fade_frames
    mid = 128 if width == 1 else 0
    for f in range(start, keep):
        gain = (keep - 1 - f) / float(fade_frames)
        for c in range(ch):
            i = f * ch + c
            samples[i] = int(round(mid + (samples[i] - mid) * gain))
    if sys.byteorder == 'big' and width > 1:
        samples.byteswap()
    with wave.open(str(out), 'wb') as w:
        w.setparams(params._replace(nframes=keep))
        w.writeframes(samples.tobytes())


def ffmpeg_seconds(ffmpeg: str, path: Path) -> float | None:
    m = pkg_audio.measure(ffmpeg, path.read_bytes(), path.suffix)
    return m.get('seconds') if m else None


def cut_ffmpeg(ffmpeg: str, src: Path, out: Path, seconds: float, fade: float) -> None:
    run = subprocess.run([ffmpeg, '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(src), '-t', '%.3f' % seconds,
                          '-af', 'afade=t=out:st=%.3f:d=%.3f' % (max(0.0, seconds - fade), fade), '-map_metadata', '-1',
                          str(out)], capture_output=True, text=True, errors='replace', timeout=120)
    if run.returncode != 0 or not out.is_file():
        raise ValueError('ffmpeg could not cut %s: %s' % (src.name, run.stderr[-200:]))


def length_of(path: Path, ffmpeg: str | None) -> float | None:
    if path.suffix.lower() == '.wav':
        try:
            return wav_seconds(path)
        except (wave.Error, EOFError, OSError):
            pass
    return ffmpeg_seconds(ffmpeg, path) if ffmpeg else None


# ---------------------------------------------------------------- library

def usage_by_others(lib: gate.Library, own_key: str, path: str, audio_id: str) -> list[str]:
    games = set()
    for proj, paths, ids in lib.usage:
        if path in paths or (audio_id and audio_id in ids):
            key = gate.game_key(proj)
            if not gate.same_game(key, own_key):
                games.add(key)
    return sorted(games)


def find_row(lib: gate.Library, src: Path) -> dict | None:
    row = lib.path_row(str(src))
    if row:
        return row
    return lib.by_sha.get(sha256_file(src).lower())


def plan_one(lib, project, own_key, args, src_text, name_override, ffmpeg):
    src = Path(src_text).expanduser()
    if not src.is_file():
        return None, 'file not found: %s' % src
    row = find_row(lib, src)
    if not row:
        return None, ('%s is not in %s/index.csv: no source or licence to record. Pick from the library (or add it '
                      'to the library index with its licence first).' % (src.name, lib.root))
    allowed, attribution, why = gate.licence(row.get('license'))
    if (row.get('attribution') or '').strip().lower() in ('yes', 'true', '1', 'required'):
        attribution = True
    if not allowed:
        return None, '%s: licence "%s" not allowed (%s)' % (src.name, row.get('license'), why)
    if attribution:
        return None, '%s: licence "%s" needs attribution; only commercial use without attribution is taken' % (
            src.name, row.get('license'))
    lib_path = row.get('path') or str(src)
    others = usage_by_others(lib, own_key, lib_path, (row.get('audio_id') or '').strip())
    if len(others) >= 2 and not args.allow_reuse:
        return None, '%s is already used by %d other games (%s); pick another sound' % (
            src.name, len(others), ', '.join(others[:5]))
    name = name_override or src.name
    if Path(name).suffix.lower() != src.suffix.lower():
        name = Path(name).stem + src.suffix.lower()
    if not re.fullmatch(r'[A-Za-z0-9_.\-]+', name):
        return None, '%s: use an English file name (letters, digits, _ - .) with --as' % name
    words = pkg_audio.tokens(name) | pkg_audio.tokens(src.name)
    fail = args.fail or bool(words & pkg_audio.FAIL_TOKENS)
    result = args.result or bool(words & RESULT_TOKENS)
    seconds = length_of(src, ffmpeg)
    cut = False
    if fail or result:
        if seconds is None:
            return None, '%s: a %s sound must be 2 s or less, and its length cannot be read here (ffmpeg missing?)' % (
                src.name, 'fail' if fail else 'result')
        cut = seconds > CUT_SECONDS + 0.005
        if cut and src.suffix.lower() != '.wav' and not ffmpeg:
            return None, '%s: %.2f s, needs cutting to %.1f s and ffmpeg was not found' % (src.name, seconds, CUT_SECONDS)
    kind = args.kind or ('jingle' if (fail or result) else 'sfx')
    return {'src': src, 'row': row, 'name': name, 'kind': kind, 'fail': fail, 'result': result, 'seconds': seconds,
            'cut': cut, 'others': others, 'lib_path': lib_path}, None


# ---------------------------------------------------------------- writing

def write_credits(project: Path, entries: list[dict]) -> Path:
    credits = project / 'docs' / 'audio' / 'credits.csv'
    credits.parent.mkdir(parents=True, exist_ok=True)
    old_rows, old_fields = [], []
    outs = {e['rel'] for e in entries}
    if credits.is_file():
        with credits.open(newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            old_fields = list(reader.fieldnames or [])
            old_rows = [r for r in reader if (r.get('outputs') or '').strip() not in outs]
    fields = old_fields + [f for f in CREDIT_FIELDS if f not in old_fields]
    rows = list(old_rows)
    for e in entries:
        r = e['row']
        rows.append({'id': Path(e['rel']).stem, 'type': e['kind'], 'title': '%s / %s' % (r.get('pack', ''), r.get('name', '')),
                     'author': r.get('author', ''), 'source': '%s/%s' % (r.get('source', ''), r.get('pack', '')),
                     'license': r.get('license', ''), 'attribution_required': 'no', 'url': r.get('url', ''),
                     'library_path': e['lib_path'], 'source_sha256': r.get('file_sha256') or sha256_file(e['src']),
                     'outputs': e['rel'], 'output_sha256': e['sha256'], 'notes': e['notes']})
    tmp = credits.with_name(credits.name + '.tmp')
    with tmp.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fields})
    os.replace(tmp, credits)
    return credits


def register_usage(lib_root: Path, project: Path, entries: list[dict]) -> Path:
    """Same record shape as game-audio-library audio_pipeline.commit_usage (schema 2) and ad-boost pick_sfx; its own
    key so a later pipeline run for the game does not drop it."""
    usage = lib_root / 'usage'
    usage.mkdir(parents=True, exist_ok=True)
    record = usage / (hashlib.sha256((str(project.resolve()) + '|' + PART).encode()).hexdigest() + '.json')
    old = {}
    if record.is_file():
        try:
            old = json.loads(record.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            old = {}
    payload = {'schema': 2, 'project': str(project.resolve()), 'part': PART, 'at': time.time(),
               'paths': sorted(set(old.get('paths') or []) | {e['lib_path'] for e in entries}),
               'asset_ids': sorted(set(old.get('asset_ids') or []) | {e['row'].get('audio_id') for e in entries
                                                                       if e['row'].get('audio_id')}),
               'packs': sorted(set(old.get('packs') or []) | {'%s/%s' % (e['row'].get('source', ''), e['row'].get('pack', ''))
                                                             for e in entries})}
    tmp = record.with_suffix('.tmp')
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, record)
    return record


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--file', action='append', required=True, help='a sound file inside the library (repeat)')
    ap.add_argument('--dest', default='assets/resources/audio', help='folder under the project (default %(default)s)')
    ap.add_argument('--as', dest='as_name', default='', help='file name in the game (one --file only)')
    ap.add_argument('--kind', choices=('sfx', 'music', 'jingle'), help='credits.csv type (default sfx / jingle)')
    ap.add_argument('--fail', action='store_true', help='treat as a fail sound: cut to 2 s with a fade-out')
    ap.add_argument('--result', action='store_true', help='treat as a result / win sound: cut to 2 s with a fade-out')
    ap.add_argument('--library', type=Path, help='audio library folder with index.csv (default: the gate lookup)')
    ap.add_argument('--no-usage', action='store_true', help='do not register usage (trial copy)')
    ap.add_argument('--allow-reuse', action='store_true', help='take a sound 2+ other games used (the gate will flag it)')
    a = ap.parse_args(argv)
    project = a.project.expanduser()
    if not (project / 'assets').is_dir():
        print(json.dumps({'status': 'error', 'error': 'no assets folder in %s' % project}, ensure_ascii=False))
        return 2
    if a.as_name and len(a.file) != 1:
        print(json.dumps({'status': 'error', 'error': '--as needs exactly one --file'}, ensure_ascii=False))
        return 2
    dest = (project / a.dest).resolve()
    try:
        dest.relative_to((project / 'assets').resolve())
    except ValueError:
        print(json.dumps({'status': 'error', 'error': '--dest must be inside assets/'}, ensure_ascii=False))
        return 2
    lib = gate.Library(gate.library_root(a.library))
    if not lib.ok:
        print(json.dumps({'status': 'refused', 'problems': ['no index.csv in %s: give --library or set GAME_AUDIO_LIB' % lib.root]},
                         ensure_ascii=False))
        return 1
    ffmpeg = pkg_audio.find_ffmpeg()
    own_key = gate.game_key(project.resolve())
    plans, problems = [], []
    for f in a.file:
        p, err = plan_one(lib, project, own_key, a, f, a.as_name, ffmpeg)
        if err:
            problems.append(err)
        else:
            plans.append(p)
    names = [p['name'] for p in plans]
    if len(set(names)) != len(names):
        problems.append('two files would get the same name in %s' % a.dest)
    budget_items = [(dest / p['name'], p['src'].stat().st_size, 'deferred') for p in plans]
    if not problems:
        try:   # P04: the size ledger; sound is never a home-page need (AudioService loads it after the first frame)
            budget.record_many(project, budget_items, PART, dry_run=True)
        except budget.BudgetError as error:
            problems.append(str(error))
    if problems:
        print(json.dumps({'status': 'refused', 'problems': problems, 'written': []}, ensure_ascii=False))
        return 1
    dest.mkdir(parents=True, exist_ok=True)
    entries, warnings, made = [], [], []
    try:
        for p in plans:
            out = dest / p['name']
            fd, tmp_name = tempfile.mkstemp(prefix='.import_', suffix=p['src'].suffix, dir=str(dest))
            os.close(fd)
            tmp = Path(tmp_name)
            made.append(tmp)
            notes = [PART]
            if p['cut']:
                if p['src'].suffix.lower() == '.wav':
                    cut_wav(p['src'], tmp, CUT_SECONDS, FADE_SECONDS)
                else:
                    cut_ffmpeg(ffmpeg, p['src'], tmp, CUT_SECONDS, FADE_SECONDS)
                after = length_of(tmp, ffmpeg)
                if after is None or after > CUT_SECONDS + 0.05:
                    raise ValueError('%s still %s s after cutting' % (p['name'], after))
                notes.append('%s sound cut %.2f s -> %.2f s, fade-out %.2f s' % ('fail' if p['fail'] else 'result',
                                                                                  p['seconds'], after, FADE_SECONDS))
            else:
                shutil.copyfile(p['src'], tmp)
            if p['others']:
                warnings.append('%s is already used by 1 other game (%s)' % (p['src'].name, p['others'][0])
                                if len(p['others']) == 1 else '%s used by %d other games (--allow-reuse)' % (p['src'].name, len(p['others'])))
            entries.append(dict(p, tmp=tmp, out=out, rel=rel(project, out), sha256=sha256_file(tmp), notes='; '.join(notes)))
        for e in entries:
            os.replace(e['tmp'], e['out'])
        credits = write_credits(project, entries)
    except (OSError, ValueError, wave.Error, subprocess.SubprocessError) as error:
        for t in made:
            t.unlink(missing_ok=True)
        for e in entries:
            if e['out'].is_file() and sha256_file(e['out']) == e['sha256']:
                e['out'].unlink()
        print(json.dumps({'status': 'error', 'error': str(error)}, ensure_ascii=False))
        return 2
    usage = None if a.no_usage else str(register_usage(lib.root, project, entries))
    try:
        ledger = budget.record_many(project, [(e['out'], None, 'deferred') for e in entries], PART)
        budget_warnings = ledger['warnings']
        first_mib = round(ledger['summary']['first_download_bytes'] / 1048576.0, 2)
    except budget.BudgetError as error:   # cut files are smaller than the dry run's sources: not expected
        budget_warnings = [str(error)]
        first_mib = None
    print(json.dumps({'status': 'imported', 'files': [{'file': e['rel'], 'sha256': e['sha256'], 'kind': e['kind'],
                                                        'notes': e['notes']} for e in entries],
                      'credits': rel(project, credits), 'usage': usage or 'not registered (--no-usage)',
                      'budget': 'docs/startup/budget.json', 'first_download_mib': first_mib,
                      'budget_warnings': budget_warnings,
                      'warnings': warnings}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())

"""Audio gate (v7.8, 总表 H7 and 22.1): loudness and fail-sound length of the audio that is really in the package.

Saul's rules: sound effects about -16 LUFS, background music about -20 LUFS, a fail / game-over sound 2 seconds or less
with a fade-out (企鹅雪道 5.5 s cut to 1.8 s; Pinecone fix2 shipped a 6.0 s jingle_lose.mp3), nothing harsh.
game-audio-library's process_audio.py writes exactly these targets, so a finished file far off them was never
processed, was processed again by hand, or was replaced afterwards. Every package entry runs this through
package_gates.run (make_tiktok_zip.py, build_checked_zip.py, check_package.py), on the bytes that go into the ZIP.

Each .mp3/.ogg/.oga/.wav/.m4a/.aac/.flac in the package is measured once with ffmpeg (ebur128 integrated loudness,
volumedetect on the full band and on a 4 kHz high-pass):
    A1_audio_loudness    integrated loudness more than 4 LU from its target (-16 LUFS sound effect, -20 LUFS
                         music; a jingle either, see below). Files shorter than 0.5 s are not measured for
                         loudness (ebur128 gates them away).
                         A file of 0.5 s or more that measures -70 LUFS (silence) counts as off target.
    A2_fail_sound_length a sound effect whose name reads as fail / lose / lost / game over / defeat / death / die /
                         time-up (timeout, times up; Saul 10-30) longer than 2.5 s (the rule is 2 s with a fade-out;
                         the gate leaves 0.5 s of slack).
    A0_ffmpeg_missing    ffmpeg is not installed, so nothing could be measured. A check never skips silently (B18).
new game: A0/A1/A2 block; legacy game (on LEGACY_GAMES.json): they warn. board localize (英化 keeps the original
game's sounds): they warn. Warning only, both policies:
    W_audio_harsh        the 4 kHz high-passed signal is less than 6 dB below the full band ("may sound harsh").
                         Sounds of 0.3 s or less are not reported (Saul 10-30: button clicks and ticks are bright by
                         nature; 13 of 18 calibration packages warned before).
    W_audio_unmeasured   ffmpeg could not decode a file (the game will not play it either; replace it).
    W_audio_unnamed      a sound longer than 2.5 s whose asset name could not be read, so the fail-sound rule could
                         not be applied to it (open the project and check it is not a fail sound).

Which name: a Cocos build names native audio by uuid (native/4d/4dd8ecf4-....mp3). The gate reads every bundle
config.json in the package (2.4 and 3.x: uuids + paths) to get the asset path (audio/bgm/jingle_lose); a writer view
(context project) also reads the project's .meta files. Without either, the package file name is used.
Music or sound effect, first rule that applies:
    1. project docs/audio/needs.csv type (bgm -> music; sfx / jingle -> sound effect) of the id whose credits.csv
       "outputs" names this file (writer view only, game-audio-library writes both files);
    2. a fail name (above) -> jingle, and the fail-sound length rule applies (starter packs ship
       bgm/music_fail.mp3; Pinecone fix2 had bgm/jingle_lose);
    3. a word jingle / win / won / victory / fanfare / stinger / success / complete / clear -> jingle;
    4. the file name contains bgm / music / song / soundtrack / theme / loop -> music;
    5. longer than 15 s -> music; otherwise a sound effect.
Only the asset's own file name is read for rules 2-4, not its folder (audio/bgm/jingle_lose is a jingle).
Allowed loudness: sound effect -20..-12 LUFS, music -24..-16 LUFS, jingle (rules 2-3) -24..-12 LUFS, because
game-audio-library makes jingle_win / jingle_lose at -16 and starter packs ship music_win / music_fail at -20
(calibrated 2026-10-30 on 6 子午/巴扎黑 starter-pack games); a needs.csv jingle (rule 1) is held to -16 +-4.
"""
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import finding

AUDIO_EXT = ('.mp3', '.ogg', '.oga', '.wav', '.m4a', '.aac', '.flac')
SFX_LUFS, BGM_LUFS, TOLERANCE_LU = -16.0, -20.0, 4.0
# allowed integrated loudness per kind: target +-4 LU; a jingle named only by its file name may sit at either level
# (game-audio-library makes jingle_win / jingle_lose at -16, starter packs ship music_win / music_fail at -20)
LUFS_RANGE = {'sfx': (SFX_LUFS - TOLERANCE_LU, SFX_LUFS + TOLERANCE_LU),
              'music': (BGM_LUFS - TOLERANCE_LU, BGM_LUFS + TOLERANCE_LU),
              'jingle': (BGM_LUFS - TOLERANCE_LU, SFX_LUFS + TOLERANCE_LU)}
MIN_LOUDNESS_SECONDS = 0.5
FAIL_MAX_SECONDS = 2.5
BGM_MIN_SECONDS = 15.0
HARSH_DB = -6.0
HARSH_MIN_SECONDS = 0.3      # clicks / ticks this short are not reported as harsh (Saul 10-30)
SILENT_LUFS = -69.9
UUID = re.compile(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', re.I)
BGM_NAME = re.compile(r'bgm|music|song|soundtrack|theme|loop', re.I)
FAIL_TOKENS = {'fail', 'fails', 'failed', 'failure', 'lose', 'loses', 'lost', 'loss', 'loser', 'gameover', 'defeat',
               'defeated', 'death', 'dead', 'die', 'died', 'dies', 'timeout', 'timesup', 'timeup'}
# v7.8 (W89, 总表 H7): Saul's rule is 2 s or less with a fade-out. game-audio-library reads THIS list and number
# (scripts/fail_sound.py): process_audio.py cuts every fail-named sound to FAIL_TARGET_SECONDS with a fade-out of
# FAIL_FADE_SECONDS, search_index.py never picks a longer one. A2 above keeps 0.5 s of slack. A time-up sound
# (timeout, time_out, times_up, time_up) is a fail sound: Saul 10-30 (FoxDenDash timeout -26 LUFS, Holly timeout.mp3 3 s).
FAIL_TARGET_SECONDS = 2.0
FAIL_FADE_SECONDS = 0.35
JINGLE_TOKENS = {'jingle', 'win', 'won', 'victory', 'fanfare', 'stinger', 'success', 'complete', 'clear'}
FFMPEG_DIRS = ('/opt/homebrew/bin', '/usr/local/bin', '/usr/bin', r'C:\ffmpeg\bin', r'C:\Program Files\ffmpeg\bin')
TIMEOUT = 120
_CACHE = {}        # sha256 of the bytes -> measurement (the writers run the gates more than once per package)


def find_ffmpeg():
    """-> path of ffmpeg or None (PATH first, then the usual Homebrew / Windows folders)."""
    found = shutil.which('ffmpeg')
    if found:
        return found
    for folder in FFMPEG_DIRS:
        for name in ('ffmpeg', 'ffmpeg.exe'):
            path = os.path.join(folder, name)
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
    local = os.environ.get('LOCALAPPDATA')
    if local:
        path = os.path.join(local, 'Microsoft', 'WinGet', 'Links', 'ffmpeg.exe')
        if os.path.isfile(path):
            return path
    return None


def measure(ffmpeg, data, suffix):
    """-> {'seconds', 'lufs', 'hf_db'} (a value is None when ffmpeg did not report it) or None when undecodable.
    One ffmpeg run: ebur128 integrated loudness, mean volume full band and after a steep 4 kHz high-pass."""
    key = hashlib.sha256(data).hexdigest()
    if key in _CACHE:
        return _CACHE[key]
    graph = ('[0:a:0]asplit=3[a][b][c];[a]ebur128=framelog=quiet,anullsink;[b]volumedetect,anullsink;'
             '[c]highpass=f=4000,highpass=f=4000,highpass=f=4000,volumedetect[o]')
    fd, name = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
        run = subprocess.run([ffmpeg, '-nostdin', '-hide_banner', '-nostats', '-i', name, '-filter_complex', graph,
                              '-map', '[o]', '-f', 'null', '-'], capture_output=True, text=True, errors='replace',
                             timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        _CACHE[key] = None
        return None
    finally:
        try:
            os.unlink(name)
        except OSError:
            pass
    err = run.stderr
    lufs = re.findall(r'^\s*I:\s+(-?[\d.]+|-inf) LUFS', err, re.M)
    means = {}
    for index, value in re.findall(r'Parsed_volumedetect_(\d+) @ [^\]]*\] mean_volume:\s+(-?[\d.]+|-inf) dB', err):
        means[int(index)] = float(value)
    if run.returncode != 0 or not lufs:
        _CACHE[key] = None
        return None
    seconds = None
    dur = re.search(r'Duration:\s+(\d+):(\d+):(\d+(?:\.\d+)?)', err)
    if dur:
        seconds = round(int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3)), 3)
    hf = None
    if len(means) >= 2:
        order = sorted(means)          # the full-band volumedetect is created before the high-passed one
        full, high = means[order[0]], means[order[-1]]
        if full != float('-inf') and high != float('-inf'):
            hf = round(high - full, 1)
    value = float(lufs[-1]) if lufs[-1] != '-inf' else -70.0
    out = {'seconds': seconds, 'lufs': value, 'hf_db': hf}
    _CACHE[key] = out
    return out


def _bundle_names(view):
    """{dashed uuid: asset path without extension} from every bundle config.json in the package."""
    try:
        from tiktok_finalize_steps.policy import decode_uuid
    except ImportError:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from tiktok_finalize_steps.policy import decode_uuid
    names = {}
    for rel, data in view.files.items():
        if not re.search(r'(^|/)config(\.[0-9a-f]+)?\.json$', rel):
            continue
        try:
            config = json.loads(data.decode('utf-8-sig'))
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(config, dict):
            continue
        uuids, paths = config.get('uuids'), config.get('paths')
        if not isinstance(uuids, list) or not isinstance(paths, dict):
            continue
        for index, entry in paths.items():
            try:
                uuid = decode_uuid(uuids[int(index)])
            except (ValueError, IndexError, TypeError):
                continue
            if uuid and isinstance(entry, list) and entry and isinstance(entry[0], str):
                names.setdefault(uuid, entry[0])
    return names


def _project_info(view):
    """Writer view only: ({uuid: project relpath}, {project relpath: needs.csv type})."""
    project = getattr(view, 'project', None)
    if not project:
        return {}, {}
    project = Path(project)
    by_uuid, kinds = {}, {}
    assets = project / 'assets'
    if assets.is_dir():
        for meta in assets.rglob('*.meta'):
            target = meta.with_suffix('')
            if target.suffix.lower() not in AUDIO_EXT:
                continue
            try:
                uuid = json.loads(meta.read_text(encoding='utf-8-sig')).get('uuid')
            except (OSError, ValueError, AttributeError):
                continue
            if isinstance(uuid, str):
                by_uuid[uuid.lower()] = target.relative_to(project).as_posix()
    try:
        with (project / 'docs/audio/needs.csv').open(newline='', encoding='utf-8-sig') as handle:
            types = {(r.get('id') or '').strip(): (r.get('type') or '').strip().lower() for r in csv.DictReader(handle)}
        with (project / 'docs/audio/credits.csv').open(newline='', encoding='utf-8-sig') as handle:
            for row in csv.DictReader(handle):
                ids = [x.strip() for x in (row.get('id') or '').split(';')]
                outs = [x.strip().replace('\\', '/') for x in (row.get('outputs') or '').split(';')]
                for i, out in enumerate(outs):
                    kind = types.get(ids[i] if i < len(ids) else ids[0]) or types.get(ids[0])
                    if out and kind:
                        kinds[out] = kind
    except (OSError, ValueError, csv.Error):
        pass
    return by_uuid, kinds


def tokens(name):
    stem = re.sub(r'\.[A-Za-z0-9]+$', '', name.rsplit('/', 1)[-1])
    words = [w.lower() for w in re.findall(r'[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+', stem)]
    joined = ''.join(words)
    out = set(words) | ({'gameover'} if 'gameover' in joined else set())
    for word in ('timeout', 'timesup', 'timeup'):          # time_out / times_up / TimeUp read as one word
        if word in joined:
            out.add(word)
    return out


def is_fail_name(name):
    return bool(tokens(name) & FAIL_TOKENS)


def board_of(view):
    if view.board in ('remake', 'localize'):
        return view.board
    record = getattr(view, 'finalize_record', None)
    if isinstance(record, dict) and record.get('board') in ('remake', 'localize'):
        return record['board']
    project = getattr(view, 'project', None)
    if project:
        try:
            text = (Path(project) / 'docs/board.txt').read_text(encoding='utf-8').strip().lower()
        except OSError:
            text = ''
        if text in ('remake', 'localize'):
            return text
    return None


def check(view):
    files = sorted(n for n in view.files if n.lower().endswith(AUDIO_EXT))
    if not files:
        return []
    policy, _why = view.get_policy()
    board = board_of(view)
    level = 'block' if policy == 'new' and board != 'localize' else 'warn'
    why_level = ('new game' if level == 'block' else
                 'board localize keeps the original sounds' if board == 'localize' else 'legacy game')
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return [finding('A0_ffmpeg_missing', level, 'ffmpeg is not installed, so the loudness and fail-sound length of '
                        '%d audio file(s) could not be measured (%s). Install ffmpeg (macOS: brew install ffmpeg; '
                        'Windows: winget install Gyan.FFmpeg) and build the package again' % (len(files), why_level),
                        {'audio_files': files[:20]})]
    names = _bundle_names(view)
    by_uuid, kinds = _project_info(view)
    loud, long_fail, harsh, unmeasured, unnamed = [], [], [], [], []
    for rel in files:
        stats = measure(ffmpeg, view.files[rel], Path(rel).suffix.lower())
        if stats is None:
            unmeasured.append(rel)
            continue
        found = UUID.search(rel.rsplit('/', 1)[-1])
        uuid = found.group(1).lower() if found else None
        project_rel = by_uuid.get(uuid) if uuid else None
        name = project_rel or (names.get(uuid) if uuid else None) or (None if uuid else rel)
        kind_from_config = kinds.get(project_rel) if project_rel else None
        seconds = stats['seconds'] or 0.0
        if kind_from_config in ('bgm', 'music'):
            kind, kind_by = 'music', 'needs.csv'
        elif kind_from_config:
            kind, kind_by = 'sfx', 'needs.csv'
        elif name and is_fail_name(name):
            kind, kind_by = 'jingle', 'fail name'        # music_fail / bgm_gameover is still a fail sound
        elif name and tokens(name) & JINGLE_TOKENS:
            kind, kind_by = 'jingle', 'jingle name'      # music_win / jingle_win
        elif name and BGM_NAME.search(name.rsplit('/', 1)[-1]):
            kind, kind_by = 'music', 'name'
        elif seconds > BGM_MIN_SECONDS:
            kind, kind_by = 'music', 'longer than %g s' % BGM_MIN_SECONDS
        else:
            kind, kind_by = 'sfx', 'default'
        low, high = LUFS_RANGE[kind]
        target = BGM_LUFS if kind == 'music' else SFX_LUFS
        row = {'file': rel, 'name': name, 'kind': kind, 'kind_by': kind_by, 'seconds': stats['seconds'],
               'lufs': stats['lufs'], 'target_lufs': target if kind != 'jingle' else [SFX_LUFS, BGM_LUFS],
               'allowed_lufs': [low, high], 'hf_db': stats['hf_db']}
        if seconds >= MIN_LOUDNESS_SECONDS and stats['lufs'] is not None and \
                (stats['lufs'] <= SILENT_LUFS or not low <= stats['lufs'] <= high):
            loud.append(row)
        if kind in ('sfx', 'jingle') and seconds > FAIL_MAX_SECONDS:
            if name is None:
                unnamed.append(row)
            elif is_fail_name(name):
                long_fail.append(row)
        if stats['hf_db'] is not None and stats['hf_db'] > HARSH_DB and seconds > HARSH_MIN_SECONDS:
            harsh.append(row)
    out = []
    if loud:
        out.append(finding('A1_audio_loudness', level, '%d audio file(s) more than %g LU from the loudness target '
                           '(sound effect %g LUFS, music %g LUFS; %s): %s. Process them again with game-audio-library '
                           '(process_audio.py) or set the gain so each lands on its target, then build again'
                           % (len(loud), TOLERANCE_LU, SFX_LUFS, BGM_LUFS, why_level,
                              '; '.join('%s %s LUFS (%s by %s, allowed %g..%g)'
                                        % (r['name'] or r['file'], r['lufs'], r['kind'], r['kind_by'],
                                           r['allowed_lufs'][0], r['allowed_lufs'][1]) for r in loud[:6])), loud))
    if long_fail:
        out.append(finding('A2_fail_sound_length', level, '%d fail / game-over sound(s) longer than %g s (%s): %s. '
                           'Cut each to 2 s or less with a fade-out (企鹅雪道 5.5 s -> 1.8 s), then build again'
                           % (len(long_fail), FAIL_MAX_SECONDS, why_level,
                              '; '.join('%s %.1f s' % (r['name'] or r['file'], r['seconds'] or 0) for r in long_fail[:6])),
                           long_fail))
    if harsh:
        out.append(finding('W_audio_harsh', 'warn', '%d audio file(s) whose energy above 4 kHz is less than %g dB below '
                           'the full band, so they may sound harsh: %s. Listen to them; a low-pass (for example 4500 Hz) '
                           'softens them' % (len(harsh), -HARSH_DB, '; '.join('%s %s dB' % (r['name'] or r['file'],
                                                                                              r['hf_db']) for r in harsh[:6])),
                           harsh))
    if unmeasured:
        out.append(finding('W_audio_unmeasured', 'warn', 'ffmpeg could not decode %d audio file(s) (%s); the game cannot '
                           'play them either. Replace them with files game-audio-library made'
                           % (len(unmeasured), ', '.join(unmeasured[:6])), unmeasured))
    if unnamed:
        out.append(finding('W_audio_unnamed', 'warn', '%d sound(s) longer than %g s whose asset name is not in any bundle '
                           'config, so the fail-sound length rule could not be applied: %s. Check in the project that '
                           'none of them is a fail / game-over sound' % (len(unnamed), FAIL_MAX_SECONDS,
                                                                        ', '.join(r['file'] for r in unnamed[:6])),
                           unnamed))
    return out

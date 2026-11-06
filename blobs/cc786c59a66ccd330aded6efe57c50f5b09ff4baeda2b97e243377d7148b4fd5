#!/usr/bin/env python3
"""English stage-1 inventory of the original game's own sound code (生成时预防 R4O6, 补查2 第 12 组).

奔跑吧巨人's music switch also silenced the sound effects, and 弹球传奇's own sound calls were reported to error on TikTok.
Both games kept their original sound manager, so the kit's AudioService (separate music and sfx switches, mute during
ads, BGM fallback) was never used. This scan lists every sound entry of the original so the switch to AudioService is on
the to-do list from the first day:
  audio_play          cc.audioEngine.play / playMusic / playEffect, AudioSource play() / playOneShot()
  audio_platform_api  tt / wx createInnerAudioContext, new Audio(), (webkit)AudioContext (browser or platform audio)
  audio_switch        reads and writes of the music / sound switch or volume (storage keys, setMusicVolume, pauseAll ...)
Read only: nothing in the project is written. It cannot tell from code whether one switch drives both channels; every row
says what to change and the settings page still has to be tried by hand (two switches, each one alone).

  python3 audio_inventory.py --project GAME        prints {"audio_todo": [...], "audio_summary": {...}}
`tiktok_finalize.py inventory` adds the same two keys to docs/english/platform-inventory.json.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SKIP_DIRS = {'node_modules', 'library', 'temp', 'build', 'local', 'tiktok-platform', 'packages', 'extensions'}
SOUND_RECEIVER = r'(?:[\w$]*(?:clip|audio|source|bgm|sound|music|sfx|effect)[\w$]*)'
PLAY = [
    ('cc.audioEngine', re.compile(r'\bcc\.audioEngine\.(play|playMusic|playEffect)\s*\(')),
    ('AudioSource', re.compile(r'(?i)\b%s(?:\??\.[\w$]+)*\??\.(play|playOneShot)\s*\(' % SOUND_RECEIVER)),
    ('AudioSource', re.compile(r'\.(playOneShot)\s*\(')),
]
PLATFORM = re.compile(r'\b(?:tt|wx|swan|qq|my)\.createInnerAudioContext\s*\(|\bnew\s+Audio\s*\(|'
                      r'\bnew\s+(?:window\.)?(?:webkit)?AudioContext\s*\(')
SWITCH_CALL = re.compile(r'(?i)\b(?:cc\.audioEngine\.)?(setMusicVolume|setEffectsVolume|setEffectVolume|setVolume|'
                         r'pauseAll|resumeAll|stopAll|pauseMusic|resumeMusic|stopMusic|pauseAllEffects|stopAllEffects)\s*\(')
STORE = re.compile(r'(?i)(?:getItem|setItem|getStorageSync|setStorageSync|getGlobalData|setGlobalData|getData|setData|'
                   r'get|set)\s*\(\s*[\'"`]([\w.-]*(?:music|sound|effect|sfx|audio|bgm|volume|mute)[\w.-]*)[\'"`]')
FIX = {
    'audio_play': 'play through the kit AudioService (assets/tiktok-platform/AudioService.js): music via playMusic, '
                  'effects via playSfx, so each obeys its own switch and the ad mute',
    'audio_platform_api': 'remove: the engine audio inside AudioService is the only player (a platform or browser audio '
                          'object is not muted for ads and errors on some TikTok hosts)',
    'audio_switch': 'read and write the switches through AudioService (music and sfx kept apart, saved in SaveStore '
                    '"audio"); the settings page gets two switches',
}


def source_files(project):
    root = Path(project) / 'assets'
    if not root.is_dir():
        return []
    out = []
    for p in sorted(root.rglob('*')):
        if p.suffix in ('.js', '.ts') and p.is_file() and not SKIP_DIRS & set(p.relative_to(project).parts) \
                and not p.name.endswith('.d.ts'):
            out.append(p)
    return out


def code_lines(text):
    """(line number, line) with // comments and /* */ blocks blanked (strings are not parsed: good enough here)."""
    text = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'), text, flags=re.S)
    for i, line in enumerate(text.splitlines(), 1):
        yield i, re.sub(r'(^|[^:\'"])//.*$', r'\1', line)


def scan(project):
    project = Path(project)
    rows = []
    for p in source_files(project):
        rel = p.relative_to(project).as_posix()
        text = p.read_text(encoding='utf-8', errors='replace')
        if 'AudioService' in p.stem:
            continue
        for n, line in code_lines(text):
            if not line.strip():
                continue
            seen = []                  # call positions already listed (cc.audioEngine.play is not also an AudioSource)
            for api, rx in PLAY:
                for m in rx.finditer(line):
                    if any(abs(m.end() - e) <= 1 for e in seen):
                        continue
                    seen.append(m.end())
                    rows.append({'kind': 'audio_play', 'api': '%s.%s' % (api, m.group(1)), 'file': rel, 'line': n,
                                 'code': line.strip()[:160]})
            if PLATFORM.search(line):
                rows.append({'kind': 'audio_platform_api', 'api': PLATFORM.search(line).group(0).rstrip('( '),
                             'file': rel, 'line': n, 'code': line.strip()[:160]})
            for m in SWITCH_CALL.finditer(line):
                rows.append({'kind': 'audio_switch', 'api': m.group(1), 'file': rel, 'line': n, 'code': line.strip()[:160]})
            for m in STORE.finditer(line):
                rows.append({'kind': 'audio_switch', 'api': 'storage key %s' % m.group(1), 'key': m.group(1),
                             'file': rel, 'line': n, 'code': line.strip()[:160]})
    # one row per (kind, file, line, api)
    uniq, out = set(), []
    for r in rows:
        k = (r['kind'], r['file'], r['line'], r['api'])
        if k not in uniq:
            uniq.add(k)
            out.append(dict(r, fix=FIX[r['kind']]))
    return out


def plan(project):
    rows = scan(project)
    keys = sorted({r['key'] for r in rows if r.get('key')})
    music_keys = [k for k in keys if re.search(r'(?i)music|bgm', k)]
    sfx_keys = [k for k in keys if re.search(r'(?i)sound|effect|sfx', k) and k not in music_keys]
    summary = {'play': sum(r['kind'] == 'audio_play' for r in rows),
               'platform_api': sum(r['kind'] == 'audio_platform_api' for r in rows),
               'switch': sum(r['kind'] == 'audio_switch' for r in rows),
               'files': sorted({r['file'] for r in rows}), 'switch_keys': keys,
               'advice': 'none' if not rows else 'switch the original sound code to AudioService at stage 1'}
    if keys and not (music_keys and sfx_keys):
        summary['one_switch_suspect'] = ('only %s switch keys %s: music and sound effects may share one switch '
                                         '(奔跑吧巨人)' % ('music' if music_keys else 'non-music', keys))
    return {'audio_todo': rows, 'audio_summary': summary}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    a = ap.parse_args(argv)
    if not (a.project / 'assets').is_dir():
        print(json.dumps({'error': 'not a Cocos project (no assets/): %s' % a.project}))
        return 2
    print(json.dumps(plan(a.project), ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())

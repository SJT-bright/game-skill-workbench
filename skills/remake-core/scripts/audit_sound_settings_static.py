#!/usr/bin/env python3
"""Static source check for the sound settings SKILL.md calls mandatory (v7.5, Germ2048 item 2). Read-only.

cocos-game-check/package-check/scripts/audit_sound_settings.py judges a recorded runtime trace against the native build;
before a build there is no trace, so preflight first runs this static check on the source:
  1. background music exists: a music play call (playMusic, audioEngine.play(..., true), an AudioSource with loop, or a
     bgm/music clip played through the game's audio manager);
  2. music and sound effects have separate volume controls: one music/BGM volume (or level) and one SFX/effect volume
     (or level) identifier in game code, or cc.audioEngine.setMusicVolume + setEffectsVolume.
Only the Germ2048 shape (one Sound on/off switch, no BGM, no separate volumes) is needs_fix; other gaps are "review"
(calibrated on 20 completed games, whose audio names vary). The runtime trace audit stays the final proof.
Exit 0 pass, 1 needs fix, 2 bad input.

  python3 audit_sound_settings_static.py --project <cocos project> [--out report.json]
"""
import argparse
import json
from pathlib import Path
import re
import sys

SKIP = {'library', 'temp', 'build', 'local', 'node_modules', '.git', 'packages', 'profiles', 'tiktok-platform'}
MUSIC_PLAY = [
    re.compile(r'\bplayMusic\s*\('),
    re.compile(r'audioEngine\s*\.\s*play\s*\([^,()]+,\s*true'),
    re.compile(r'\bloop\s*[:=]\s*true[^\n]{0,120}\b(?:bgm|music)|\b(?:bgm|music)\w*[^\n]{0,120}\bloop\s*[:=]\s*true', re.I),
    re.compile(r'\bplay(?:Bgm|BGM|Background)\w*\s*\('),
]
MUSIC_VOLUME = re.compile(r'\b(?:set|get|_)?(?:music|bgm|backgroundMusic)_?(?:volume|level)\b|\bsetMusicVolume\b', re.I)
SFX_VOLUME = re.compile(r'\b(?:set|get|_)?(?:sfx|effects?|soundEffects?|sound)_?(?:volume|level)\b|\bsetEffectsVolume\b', re.I)
ONE_SWITCH = re.compile(r'\b(?:is)?sound_?(?:on|off|enabled?|open|switch|toggle)\b|\bsoundState\b', re.I)
COMMENT = re.compile(r'/\*.*?\*/|(^|[^:\'"\\])//[^\n]*', re.S)


def code_files(project):
    for p in sorted((project / 'assets').rglob('*')):
        if p.is_file() and p.suffix in ('.ts', '.js') and not p.name.endswith('.d.ts') and not SKIP & set(p.relative_to(project).parts):
            yield p


def first(pattern, text):
    m = pattern.search(text)
    return (text.count('\n', 0, m.start()) + 1, m.group(0)[:80]) if m else None


def audit(project):
    project = Path(project).resolve()
    if not (project / 'assets').is_dir():
        raise ValueError('not a Cocos project (no assets folder): %s' % project)
    found = {'music_play': [], 'music_volume': [], 'sfx_volume': []}
    for p in code_files(project):
        try:
            text = COMMENT.sub(lambda m: m.group(1) or '', p.read_text(encoding='utf-8', errors='ignore'))
        except OSError:
            continue
        rel = p.relative_to(project).as_posix()
        for pat in MUSIC_PLAY:
            hit = first(pat, text)
            if hit:
                found['music_play'].append('%s:%d %s' % (rel, hit[0], hit[1]))
                break
        for key, pat in (('music_volume', MUSIC_VOLUME), ('sfx_volume', SFX_VOLUME), ('one_switch', ONE_SWITCH)):
            hit = first(pat, text)
            if hit:
                found.setdefault(key, []).append('%s:%d %s' % (rel, hit[0], hit[1]))
    gaps = []
    if not found['music_play']:
        gaps.append('no background music is played (no playMusic / looping music clip): add BGM from the audio library')
    if not found['music_volume'] or not found['sfx_volume']:
        gaps.append('settings need separate music (BGM) and sound-effect volumes, saved; found music volume: %s, SFX volume: %s'
                    % ('yes' if found['music_volume'] else 'no', 'yes' if found['sfx_volume'] else 'no'))
    # Calibration 2026-10-29 (20 completed games): audio names vary too much for "marker not found" to be a refusal, so
    # only the Germ2048 shape is refused: one Sound on/off switch, no music volume, no SFX volume, no BGM. The rest is review.
    germ_shape = bool(found.get('one_switch')) and len(gaps) == 2 and not found['music_volume'] and not found['sfx_volume']
    problems = gaps if germ_shape else []
    review = [] if germ_shape else gaps
    return {'tool': 'audit_sound_settings_static', 'schema': 2, 'project': str(project), 'found': {k: v[:5] for k, v in found.items()},
            'problems': problems, 'review': review, 'passed': not problems,
            'status': 'needs_fix' if problems else ('review' if review else 'pass'),
            'boundary': 'static source markers only; the runtime proof is package-check audit_sound_settings.py on a recorded trace'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    try:
        r = audit(a.project)
    except ValueError as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False)); return 2
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(r, ensure_ascii=False))
    return 0 if r['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())

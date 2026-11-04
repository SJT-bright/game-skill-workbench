#!/usr/bin/env python3
"""Static source check for the sound settings SKILL.md calls mandatory (v7.5, Germ2048 item 2; schema 3 in 简化.11.3,
CubeDigits 11-02 audio requirements step 1). Read-only.

cocos-game-check/package-check/scripts/audit_sound_settings.py judges a recorded runtime trace against the native build;
before a build there is no trace, so preflight first runs this static check on the source.

Does the check apply? Yes when the source has any sound signal: a sound control (music / sound / SFX / BGM volume or
switch, a "Music" / "Sound Effects" label in code or a scene), an audio file under assets/, or an audio play call.
"This round did not change audio", an old game, a maintenance task or an English version are no reasons to skip it
(requirement 3.2). A truly silent game is not_applicable only with a silent-design record (docs/audio/silent_design.md)
AND no sound signal; with no signal and no record the result is review.

Status (one of pass / fail / review / not_applicable; requirement 3.4). passed is true only for pass and
not_applicable; review is never a pass:
  fail    - sound controls but no audio file under assets/ (CubeDigits 3.7.1: sliders that save, nothing to play);
          - sound controls and audio files but no play call (an audio API used together with play / playMusic /
            playEffect / playOneShot, or an AudioSource component in a scene / prefab);
          - the silent-design record is there but the source has sound signals (the two contradict each other);
          - the Germ2048 shape: one Sound on/off switch, no BGM, no separate volumes.
  review  - the remaining gaps: no background-music play call found, or no separate music and SFX volume found
            (audio names vary between games, so these stay review, calibrated on 20 games in 2026-10-29); or no sound
            at all and no silent-design record.
  pass / not_applicable as above. The runtime trace audit stays the final proof that sound comes out.
Exit 0 pass or not_applicable, 1 fail or review (read status), 2 bad input.

  python3 audit_sound_settings_static.py --project <cocos project> [--out report.json]
"""
import argparse
import json
from pathlib import Path
import re
import sys

SKIP = {'library', 'temp', 'build', 'local', 'node_modules', '.git', 'packages', 'profiles', 'tiktok-platform'}
AUDIO_EXT = ('.mp3', '.ogg', '.oga', '.wav', '.m4a', '.aac', '.flac')
MUSIC_PLAY = [
    re.compile(r'\bplayMusic\s*\('),
    re.compile(r'audioEngine\s*\.\s*play\s*\([^,()]+,\s*true'),
    re.compile(r'\bloop\s*[:=]\s*true[^\n]{0,120}\b(?:bgm|music)|\b(?:bgm|music)\w*[^\n]{0,120}\bloop\s*[:=]\s*true', re.I),
    re.compile(r'\bplay(?:Bgm|BGM|Background)\w*\s*\('),
]
MUSIC_VOLUME = re.compile(r'\b(?:set|get|_)?(?:music|bgm|backgroundMusic)_?(?:volume|level)\b|\bsetMusicVolume\b', re.I)
SFX_VOLUME = re.compile(r'\b(?:set|get|_)?(?:sfx|effects?|soundEffects?|sound)_?(?:volume|level)\b|\bsetEffectsVolume\b', re.I)
ONE_SWITCH = re.compile(r'\b(?:is)?sound_?(?:on|off|enabled?|open|switch|toggle)\b|\bsoundState\b', re.I)
# 简化.11.3: the same control / play-call words as package_gates/sound.py (calibrated on 303 TikTok packages)
CONTROL_ID = re.compile(r'\b_?(?:is)?(?:music|bgm|sfx|sounds?|soundEffects?|audio|backgroundMusic)_?'
                        r'(?:volumes?|vol|on|off|enabled?|muted?|switch|toggle|level|active)\b|'
                        r'\bset(?:Music|Effects)Volume\b|\bvolumes\s*:\s*\{', re.I)
CONTROL_TEXT = re.compile(r'["\'](?:music|sound|sounds|sound effects?|sfx|bgm|background music|music volume|'
                          r'sound volume|sfx volume|volume)["\']', re.I)
LABEL_TEXT = re.compile(r'"_string"\s*:\s*"(?:music|sound|sounds|sound effects?|sfx|bgm|background music|volume)'
                        r'(?:\s*(?:on|off|volume|:))?"', re.I)
AUDIO_API = re.compile(r'\baudioEngine\b|\bAudioSource\b|\bAudioClip\b|\bcreate(?:Inner|WebAudio)?AudioContext\s*\(|'
                       r'\bcreateBufferSource\s*\(|\bnew\s+(?:window\.)?(?:webkit)?Audio(?:Context)?\s*\(')
PLAY_CALL = re.compile(r'\.\s*play(?:Music|Effect|OneShot)?\s*\(|\bplayOneShot\s*\(')
SCENE_AUDIO = re.compile(r'"cc\.AudioSource"')
SILENT_RECORD = ('docs/audio/silent_design.md', 'docs/audio/silent_design.txt')
COMMENT = re.compile(r'/\*.*?\*/|(^|[^:\'"\\])//[^\n]*', re.S)


def walk(project, suffixes):
    for p in sorted((project / 'assets').rglob('*')):
        if p.is_file() and p.suffix.lower() in suffixes and not p.name.endswith('.d.ts') \
                and not SKIP & set(p.relative_to(project).parts):
            yield p


def code_files(project):
    return walk(project, ('.ts', '.js'))


def first(pattern, text):
    m = pattern.search(text)
    return (text.count('\n', 0, m.start()) + 1, m.group(0)[:80]) if m else None


def audit(project):
    project = Path(project).resolve()
    if not (project / 'assets').is_dir():
        raise ValueError('not a Cocos project (no assets folder): %s' % project)
    found = {'music_play': [], 'music_volume': [], 'sfx_volume': [], 'controls': [], 'play_calls': []}
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
        hit = first(CONTROL_ID, text) or first(CONTROL_TEXT, text)
        if hit:
            found['controls'].append('%s:%d %s' % (rel, hit[0], hit[1]))
        api, call = first(AUDIO_API, text), first(PLAY_CALL, text)
        if api and call:
            found['play_calls'].append('%s:%d %s ... %s' % (rel, api[0], api[1], call[1]))
    for p in walk(project, ('.scene', '.prefab', '.fire')):
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        rel = p.relative_to(project).as_posix()
        hit = first(LABEL_TEXT, text)
        if hit:
            found['controls'].append('%s:%d %s' % (rel, hit[0], hit[1]))
        hit = first(SCENE_AUDIO, text)
        if hit:
            found['play_calls'].append('%s:%d %s' % (rel, hit[0], hit[1]))
    audio_files = [p.relative_to(project).as_posix() for p in walk(project, AUDIO_EXT)]
    found['audio_files'] = audio_files
    record = next((rel for rel in SILENT_RECORD if (project / rel).is_file()), None)
    signals = {'controls': bool(found['controls'] or found['music_volume'] or found['sfx_volume'] or found.get('one_switch')),
               'audio_files': len(audio_files), 'play_calls': bool(found['play_calls'] or found['music_play'])}
    applicable = signals['controls'] or signals['audio_files'] > 0 or signals['play_calls']

    def report(status, problems, review, why):
        return {'tool': 'audit_sound_settings_static', 'schema': 3, 'project': str(project),
                'applicable': applicable, 'applicable_why': why, 'silent_record': record, 'signals': signals,
                'found': {k: v[:5] for k, v in found.items()}, 'problems': problems, 'review': review,
                'status': status, 'passed': status in ('pass', 'not_applicable'),
                'boundary': 'static source markers only; it shows the parts exist, not that sound comes out. The runtime '
                            'proof is package-check audit_sound_settings.py on a recorded trace; package_gates/sound.py '
                            'checks the built package in every writer'}

    if not applicable:
        if record:
            return report('not_applicable', [], [], 'no sound control, audio file or play call; silent design recorded '
                          'in %s' % record)
        return report('review', [], ['no sound control, audio file or play call was found and there is no silent-design '
                                     'record: add music and sound effects (game-audio-library) or, for a game that is '
                                     'silent by design, write docs/audio/silent_design.md'],
                      'no sound signal; not_applicable needs docs/audio/silent_design.md')
    why = 'sound signals: %s' % ', '.join(k for k, v in signals.items() if v)
    problems = []
    if record:
        problems.append('%s says the game is silent, but the source has sound (%s): remove the sound or the record'
                        % (record, why))
    if signals['controls'] and not audio_files:
        problems.append('the game has sound settings (%s) but no audio file under assets/, so nothing can be heard '
                        '(CubeDigits 3.7.1): add music and sound effects from the audio library and wire them'
                        % '; '.join((found['controls'] or found['music_volume'] or found['sfx_volume'] or
                                     found.get('one_switch') or [])[:2]))
    elif signals['controls'] and not signals['play_calls']:
        problems.append('the game has sound settings and %d audio file(s) but nothing plays them (no audio API used '
                        'together with play / playMusic / playEffect / playOneShot, no AudioSource component): setting '
                        'or saving a volume does not make a sound' % len(audio_files))
    gaps = []
    if not found['music_play']:
        gaps.append('no background music is played (no playMusic / looping music clip): add BGM from the audio library')
    if not found['music_volume'] or not found['sfx_volume']:
        gaps.append('settings need separate music (BGM) and sound-effect volumes, saved; found music volume: %s, SFX volume: %s'
                    % ('yes' if found['music_volume'] else 'no', 'yes' if found['sfx_volume'] else 'no'))
    # Calibration 2026-10-29 (20 completed games): audio names vary too much for "marker not found" to be a refusal, so
    # only the Germ2048 shape is refused: one Sound on/off switch, no music volume, no SFX volume, no BGM. The rest is review.
    germ_shape = bool(found.get('one_switch')) and len(gaps) == 2 and not found['music_volume'] and not found['sfx_volume']
    if germ_shape:
        problems.extend(gaps)
        gaps = []
    if problems:
        return report('fail', problems, gaps, why)
    return report('review' if gaps else 'pass', [], gaps, why)


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

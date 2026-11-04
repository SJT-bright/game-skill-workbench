"""Sound wiring gate (简化.11.3, audio check step 1; CubeDigits 11-02 report "TikTok 测试包声音功能门禁").

CubeDigits shipped a settings page with Music and Sound Effects sliders that saved their values, but the package had
no audio file, the Cocos 3.7.1 build had no audio module and nothing ever played; the old checks called it "not
applicable, this round did not change audio". This gate reads the bytes that go into the ZIP (every package entry
runs it through package_gates.run: make_tiktok_zip.py, build_checked_zip.py, check_package.py):

    sound controls   game code (not the engine, the adapter or the kit) names a music / sound / SFX / BGM setting
                     (musicVolume, sfx_volume, soundOn, isMusicMute, setMusicVolume, volumes: {bgm, sfx} ...) or
                     shows such a label ("Music", "Sound Effects", "SFX", "BGM" as a code string or a scene/prefab
                     Label text).
    S1_sound_no_audio_files   sound controls, but no .mp3/.ogg/.oga/.wav/.m4a/.aac/.flac file in the package
                              (GrassCutter v010/v011 2026-11-02, CubeDigits 3.7.1).
    S2_sound_no_play_call     sound controls and audio files, but no game code file both uses an audio API
                              (cc.audioEngine, AudioSource, AudioClip, createInnerAudioContext, Web Audio) and calls
                              play / playMusic / playEffect / playOneShot (also through a variable:
                              this._engine = cc.audioEngine; this._engine.play(...)), and no scene/prefab has an
                              AudioSource component. Setting a volume or saving it does not make a sound.
    S3_sound_engine_no_audio  sound controls, but the engine in the package has no audio module (3.x cc.js without
                              AudioSource, 2.4 cocos2d-js without audioEngine): the module was switched off in the
                              project's build settings (CubeDigits 3.7.1). The engine is also found when it was moved
                              into a subpackage (subpackages/renderer/cc.js, 泡泡六角龙).
    S4_sound_silent_record_contradicted   writer view only: docs/audio/silent_design.md says the game is silent, but
                              the package has sound controls.
Levels: a new game blocks, a legacy game (LEGACY_GAMES.json) warns. Board localize is no exemption: an English
version keeps the original sounds, it does not keep a broken sound setting (requirement 3.2). A package without
sound controls is not judged here (a silent game; the source check audit_sound_settings_static.py asks for the
silent-design record).
Boundary: a static read of the package. It shows that the parts exist, not that sound comes out; measuring the
output (PCM in the host) is step 2 of the plan and is not done by this gate.
"""
import re
from pathlib import Path

from . import finding

AUDIO_EXT = ('.mp3', '.ogg', '.oga', '.wav', '.m4a', '.aac', '.flac')
# files that ship with every kit build or come from the build tool, not game code
KIT_FILES = re.compile(r'(^|/)(storage-guard|tiktok-touch-3x|subpackage-recovery|image-event-compat|game|application|'
                       r'web-adapter|engine-adapter|first-screen|main)\.js$|(^|/)tiktok-platform/[^/]+\.plugin\.js$|'
                       r'(^|/)src/(system|polyfills)\.bundle\.js$|(^|/)src/import-map\.js$', re.I)
ENGINE_NAME = re.compile(r'(^|/)(cc|cocos2d-js(-min)?|cocos2d-jsb(-min)?)\.js$')
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
ENGINE_AUDIO = {2: re.compile(r'audioEngine'), 3: re.compile(r'AudioSource')}
SILENT_RECORD = ('docs/audio/silent_design.md', 'docs/audio/silent_design.txt')


def engine_files(view):
    return [n for n in view.js() if view.is_engine(n) or ENGINE_NAME.search(n)]


def game_code(view):
    engine = set(engine_files(view))
    return [n for n in view.game_js() if n not in engine and not KIT_FILES.search(n)]


def scene_json(view):
    return [n for n in view.files if n.lower().endswith('.json') and '/import/' in '/' + n]


def _hits(view, names, pattern, limit=5):
    out = []
    for name in names:
        m = pattern.search(view.text(name))
        if m:
            out.append('%s: %s' % (name, m.group(0)[:60]))
            if len(out) >= limit:
                break
    return out


def _play_hits(view, names, limit=5):
    out = []
    for name in names:
        text = view.text(name)
        api, call = AUDIO_API.search(text), PLAY_CALL.search(text)
        if api and call:
            out.append('%s: %s ... %s' % (name, api.group(0)[:30], call.group(0)[:20]))
            if len(out) >= limit:
                break
    return out


def silent_record(view):
    project = getattr(view, 'project', None)
    if not project:
        return None
    for rel in SILENT_RECORD:
        if (Path(project) / rel).is_file():
            return rel
    return None


def inspect(view):
    """-> what the package has (also read by the tests and the calibration)."""
    code = game_code(view)
    scenes = scene_json(view)
    controls = _hits(view, code, CONTROL_ID) + _hits(view, code, CONTROL_TEXT) + _hits(view, scenes, LABEL_TEXT)
    audio = sorted(n for n in view.files if n.lower().endswith(AUDIO_EXT))
    play = _play_hits(view, code) + _hits(view, scenes, SCENE_AUDIO, 2)
    engine = engine_files(view)
    pattern = ENGINE_AUDIO.get(view.engine_major)
    engine_audio = None
    if pattern is not None and engine:
        engine_audio = any(pattern.search(view.text(n)) for n in engine)
    return {'controls': controls, 'audio_files': audio[:10], 'audio_count': len(audio), 'play_calls': play,
            'engine_major': view.engine_major, 'engine_files': engine[:5], 'engine_has_audio': engine_audio}


def check(view):
    info = inspect(view)
    if not info['controls']:
        return []
    policy, _why = view.get_policy()
    level = 'block' if policy == 'new' else 'warn'
    why = 'new game' if level == 'block' else 'legacy game, warning only'
    where = '; '.join(info['controls'][:3])
    out = []
    if not info['audio_count']:
        out.append(finding('S1_sound_no_audio_files', level, 'the game has sound settings (%s) but the package has no audio '
                           'file, so nothing can be heard (%s; CubeDigits 3.7.1, GrassCutter v011). Put the music and '
                           'sound effects in the project (game-audio-library), wire them to the settings and build '
                           'again; a truly silent game removes the sound settings instead' % (where, why), info))
    elif not info['play_calls']:
        out.append(finding('S2_sound_no_play_call', level, 'the game has sound settings (%s) and %d audio file(s), but no '
                           'game code plays them (no file uses cc.audioEngine / AudioSource / AudioClip / '
                           'createInnerAudioContext and calls play on it, no AudioSource component in a scene; %s). '
                           'Setting a volume or saving it does not make a sound: call the engine play API from the '
                           'audio manager' % (where, info['audio_count'], why), info))
    if info['engine_has_audio'] is False:
        out.append(finding('S3_sound_engine_no_audio', level, 'the game has sound settings (%s) but the Cocos %s engine in '
                           'the package has no audio module (%s has no %s; %s). Turn the audio module on in Project '
                           'Settings > Feature Cropping (3.x) / Module Config (2.4) and build again'
                           % (where, '3.x' if info['engine_major'] == 3 else '2.4', ', '.join(info['engine_files'][:2]),
                              ENGINE_AUDIO[info['engine_major']].pattern, why), info))
    record = silent_record(view)
    if record:
        out.append(finding('S4_sound_silent_record_contradicted', level, '%s says the game is silent, but the package has '
                           'sound settings (%s): remove the settings or the record (%s)' % (record, where, why), info))
    return out

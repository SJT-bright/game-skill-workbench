"""Portrait gate, package half (v7.8, 总表 B31; 切水果 v1 went out landscape).

Every TikTok mini-game is portrait. Blocks in both policies (new and legacy games alike):
    O1_device_orientation  game.json sets "deviceOrientation" to anything but "portrait" ("landscape", "Portrait",
                           "", ...). A missing key passes: the platform default is portrait, and many synthetic
                           packages in the Skill's own tests write no orientation at all.
The source half (cc.Canvas _designResolution in scenes/prefabs, 3.x settings designResolution) is the source step
tiktok_finalize_steps/orientation.py; its block lands in the source record and the writers refuse it (K5).
A separate module rather than a rule inside tiktok_compat: the rule has its own origin (B31, not the TikTok
research patch), blocks in both policies, and GATE_MODULES fail-closed then names it on its own when it is missing.
"""
from . import finding

WANTED = 'portrait'


def check(view):
    game = view.game_json
    if 'deviceOrientation' not in game:
        return []                        # platform default: portrait
    value = game.get('deviceOrientation')
    if value == WANTED:
        return []
    return [finding('O1_device_orientation', 'block', 'game.json deviceOrientation is %r; every TikTok mini-game must '
                    'be portrait. Set the ByteDance build option orientation to portrait (Cocos 2.4: '
                    'settings/bytedance.json "orientation"), make every cc.Canvas design resolution taller than wide, '
                    'and build again' % (value,), {'deviceOrientation': value})]

#!/usr/bin/env python3
"""生成时预防 R4Q5 (补查3 第 5 组): tiktok_finalize_steps/debug_leftover_scan.py.

Samples cut from the two census games:
  奔跑吧巨人 attackontitan: homePanel.ts `isDebugOpen === true ? profiler.showStats() : ...`, homePanel.prefab
    level/btnDebug active; 方块收割者 CubeBatle: Begin.fire (startScene) node logo + begin/bg.js (setTimeout 2 s then
    fadeOut(2): the "Galaxy Games" splash).
  1 old       the census writings -> stats + debug + splash hits; new game after R4Q5 -> K_debug_leftover block
  2 fixed     hideStats only, btnDebug inactive, bg.js without the timer -> clean
  3 levels    English -> warning; begun before R4Q5 -> warning; legacy -> not checked
  4 words     "contest" / "latest" / "Testimony"-free names do not count; inactive parent hides a debug child;
              a popup in a non-launch scene that fades itself is not a splash; glossary debug_leftover_ok keeps one
  5 wired     in SOURCE_STEPS; in SYNC_SOURCE_STEPS before ui_kit_scan
Run: python3 test_debug_leftover_scan.py
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tiktok_finalize as F  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import policy as P  # noqa: E402
from tiktok_finalize_steps import debug_leftover_scan as D  # noqa: E402

HOME_TS = '''
export class homePanel extends Component {
    onBtnDebugClick() {
        let isDebugOpen = SaveStore.get('debug');
        isDebugOpen === true ? profiler.showStats() : profiler.hideStats();
    }
}
'''
HOME_TS_FIXED = '''
export class homePanel extends Component {
    start() { profiler.hideStats(); }   // never shown
}
'''
BG_JS = '''cc.Class({ extends: cc.Component, properties: {},
    start () {
        if(gamedata.is_show){
            gamedata.is_show=false;
            setTimeout(function(){ this.node.runAction(cc.fadeOut(2)); }.bind(this),2000);
        }else{ this.node.active=false; }
    },
});
'''
BG_JS_FIXED = '''cc.Class({ extends: cc.Component, properties: {}, start () { this.node.active = false; } });
'''
BG_UUID = '1a2b3c4d-5e6f-4a1b-9c2d-3e4f5a6b7c8d'
POP_UUID = '9f8e7d6c-5b4a-4f3e-8d2c-1b0a9f8e7d6c'
SCENE_UUID = '9aecfc6c-63f6-4313-89c4-bf0a6f7bf66b'


def node(name, parent=None, active=True, comps=()):
    n = {'__type__': 'cc.Node', '_name': name, '_active': active, '_components': [{'__id__': c} for c in comps]}
    if parent is not None:
        n['_parent'] = {'__id__': parent}
    return n


def prefab(names_active):
    objs = [{'__type__': 'cc.Prefab', 'data': {'__id__': 1}}, node('homePanel')]
    objs.append(node('level', 1))
    for name, act in names_active:
        objs.append(node(name, 2, act))
    return objs


def scene(script_uuid, label=''):
    objs = [{'__type__': 'cc.SceneAsset'}, {'__type__': 'cc.Scene', '_name': 'Begin'}, node('Canvas', 1),
            node('logo', 2, True, comps=[4]), {'__type__': D.compress_uuid(script_uuid), 'node': {'__id__': 3}}]
    if label:
        objs.append(node('studio_text', 2))
        objs.append({'__type__': 'cc.Label', 'node': {'__id__': 5}, '_string': label})
    return objs


def project(tmp, old=True, by='init', board='remake', debug_names=None, label='', ok=None):
    root = Path(tmp)
    for d in ('assets/script/UI/home', 'assets/Scripts/begin', 'assets/Scripts/Main', 'assets/Scenes',
              'assets/resources/prefab/ui/home', 'settings'):
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}', encoding='utf-8')
    (root / 'settings/builder.json').write_text(json.dumps({'startScene': SCENE_UUID}), encoding='utf-8')
    (root / 'assets/script/UI/home/homePanel.ts').write_text(HOME_TS if old else HOME_TS_FIXED, encoding='utf-8')
    (root / 'assets/Scripts/begin/bg.js').write_text(BG_JS if old else BG_JS_FIXED, encoding='utf-8')
    (root / 'assets/Scripts/begin/bg.js.meta').write_text(json.dumps({'uuid': BG_UUID}), encoding='utf-8')
    (root / 'assets/Scripts/Main/Success.js').write_text(BG_JS, encoding='utf-8')     # popup fading itself
    (root / 'assets/Scripts/Main/Success.js.meta').write_text(json.dumps({'uuid': POP_UUID}), encoding='utf-8')
    (root / 'assets/Scenes/Begin.fire').write_text(json.dumps(scene(BG_UUID, label)), encoding='utf-8')
    (root / 'assets/Scenes/Begin.fire.meta').write_text(json.dumps({'uuid': SCENE_UUID}), encoding='utf-8')
    (root / 'assets/Scenes/Main1.fire').write_text(json.dumps(scene(POP_UUID)), encoding='utf-8')
    names = debug_names if debug_names is not None else [('btnDebug', old), ('btnStart', True)]
    (root / 'assets/resources/prefab/ui/home/homePanel.prefab').write_text(json.dumps(prefab(names)), encoding='utf-8')
    if ok:
        (root / 'docs/copy').mkdir(parents=True, exist_ok=True)
        (root / 'docs/copy/glossary.json').write_text(json.dumps({'debug_leftover_ok': ok}), encoding='utf-8')
    P.write_marker(root, board, '2.0', reason=by)
    return root


def run(root, policy='new', board='remake'):
    ctx = T.Ctx('source', root, project=root, board=board, engine=2, policy=policy)
    return D.apply(ctx)


class DebugLeftoverScan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='r4q5-')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_1_old_writings_blocked_for_new_game(self):
        root = project(self.tmp)
        found = D.scan(root)
        kinds = sorted({h['kind'] for h in found['hits']})
        self.assertEqual(kinds, ['debug', 'splash', 'stats'], found['hits'])
        self.assertEqual(found['launch_scene'], 'assets/Scenes/Begin.fire')
        self.assertTrue(any(h['where'] == 'homePanel/level/btnDebug' for h in found['hits']))
        r = run(root)
        self.assertEqual([b['gate'] if isinstance(b, dict) and 'gate' in b else b.get('id', b.get('gate_id'))
                          for b in r['blocks']], ['K_debug_leftover'], r)
        self.assertLess(found['seconds'], 1.0)

    def test_2_fixed_project_clean(self):
        root = project(self.tmp, old=False)
        self.assertEqual(D.scan(root)['hits'], [])
        r = run(root)
        self.assertEqual(r['blocks'], [])
        self.assertEqual(r['warnings'], [])

    def test_3_levels(self):
        root = project(self.tmp, board='localize')
        r = run(root, board='localize')
        self.assertEqual(r['blocks'], [])
        self.assertTrue(r['warnings'])
        self.assertEqual(D.level_of('new', 'remake', False), 'warn')     # in progress, begun before R4Q5
        self.assertEqual(D.level_of('new', 'remake', True), 'block')
        r = run(root, policy='legacy')
        self.assertEqual((r['blocks'], r['warnings']), ([], []))

    def test_4_words_inactive_popup_and_ok(self):
        self.assertFalse(D.words('contestBg') & D.DEBUG_WORDS)
        self.assertFalse(D.words('latest_score') & D.DEBUG_WORDS)
        self.assertTrue(D.words('btnDebug') & D.DEBUG_WORDS)
        self.assertTrue(D.words('cheat_add_gold') & D.DEBUG_WORDS)
        self.assertTrue(D.words('TestButton') & D.DEBUG_WORDS)
        root = project(self.tmp, old=False, debug_names=[('contestBg', True), ('debugPanel', False)])
        self.assertEqual(D.scan(root)['hits'], [])          # Main1 Success.js fades itself: not the launch scene
        root2 = Path(self.tmp) / 'b'
        project(root2, old=False, label='Galaxy Games')
        self.assertEqual({h['kind'] for h in D.scan(root2)['hits']}, {'splash'})
        root3 = Path(self.tmp) / 'c'
        project(root3, old=False, label='Galaxy Games', ok=['Galaxy Games', 'studio_text'])
        self.assertEqual(D.scan(root3)['hits'], [])

    def test_5_wired(self):
        self.assertIn('debug_leftover_scan', T.SOURCE_STEPS)
        steps = list(F.SYNC_SOURCE_STEPS)
        self.assertIn('debug_leftover_scan', steps)
        self.assertLess(steps.index('debug_leftover_scan'), steps.index('ui_kit_scan'))


if __name__ == '__main__':
    unittest.main()

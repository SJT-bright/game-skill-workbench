#!/usr/bin/env python3
"""v7.8 W93 (Saul 10-30 21:5x, Meteor Blaster r9 analysis): button_sweep says where a dead tap got stuck, re-taps the
page below after a popup closed (blocked_after_close) and sweeps the running level when the adapter has `play`.
Here, without a browser:
  - layout_rules.diagnose / dropPress / noisyParents / dropUnder on probe records shaped like the real ones;
  - gates.PROBE_JS run in Node on a small fake engine (cc.Node.prototype.dispatchEvent / emit,
    cc.Component.EventHandler.emitEvents, tt.*), the way the page runs it;
  - the suite wires all of it (blocked_after_close in the verdict list, adapter.play, the probe calls).
The browser half is proven on real packages: briefs/out/W93/RESULT.md (HappyCup v20.7.1 copies with a page-side
fault: close leaves a full-screen BlockInputEvents / sets the popup to opacity 0 -> blocked_after_close; a throwing
callback, a transparent cover, an unanswered tt call, a busy flag -> the matching sentence).
Run: python3 -B test_button_sweep_diag.py
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
RR = HERE / 'runtime_regression'
RULES = RR / 'layout_rules.mjs'
GATES = RR / 'gates.mjs'
SUITE = RR / 'suites' / 'button_sweep.mjs'


def node(js):
    exe = shutil.which('node')
    if not exe:
        raise unittest.SkipTest('node is required')
    r = subprocess.run([exe, '--input-type=module', '-e', js], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-1500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def rules(body):
    return node('const R = await import(%s);\nconst out = await (async () => {\n%s\n})();\nconsole.log(JSON.stringify(out));\n'
                % (json.dumps(RULES.as_uri()), body))


T = {'path': 'Canvas/home/skins'}
BASE = {'installed': True, 'hit': {'path': 'Canvas/home/skins', 'name': 'skins', 'block': False, 'button': True, 'opacity': 255},
        'end': 'Canvas/home/skins', 'emits': [{'from': 'Canvas/home/skins', 'n': 1, 'bad': []}], 'clicks': [], 'err': None,
        'pend': [], 'btn': {'exists': True, 'interactable': True, 'events': 1, 'touchEnd': 0}}


def pr(**kw):
    d = json.loads(json.dumps(BASE))
    d.update(kw)
    return d


class Diagnose(unittest.TestCase):
    def say(self, probe, target=T):
        return rules('return R.diagnose(%s, %s);' % (json.dumps(target), json.dumps(probe)))

    def test_each_stage_has_its_sentence(self):
        glass = {'path': 'Canvas/home/__glass', 'name': '__glass', 'block': True, 'button': False, 'opacity': 0, 'full': False}
        got = self.say(pr(hit=glass))
        self.assertEqual(got['stage'], 'hit')
        self.assertEqual(got['say'], '点不到（被 Canvas/home/__glass（BlockInputEvents，opacity 0 全透明） 盖住）')
        pre = self.say({'coveredBy': {'path': 'Canvas/__leftMask', 'block': True, 'opacity': 255, 'full': True}})
        self.assertEqual(pre['say'], '点不到（被 Canvas/__leftMask（BlockInputEvents，opacity 255，全屏） 盖住）')
        self.assertTrue(self.say(pr(hit=None))['say'].startswith('点不到（触点没落到'))
        # the button's own child label took the touch: still the button
        self.assertEqual(self.say(pr(hit={'path': 'Canvas/home/skins/label'}))['stage'], 'no_change')
        threw = self.say(pr(err={'src': 'callback', 'msg': 'boom @x.js:1'}))
        self.assertEqual(threw, {'stage': 'callback_error', 'say': '回调报错：boom @x.js:1'})
        self.assertEqual(self.say(pr(emits=[], clicks=[]))['say'], '回调没执行（cc.Button 没发出点击（按下和抬起没配成一次点击））')
        self.assertIn('没收到抬起', self.say(pr(end=None, emits=[]))['say'])
        self.assertIn('interactable = false', self.say(pr(emits=[], btn={'exists': True, 'interactable': False}))['say'])
        bad = self.say(pr(emits=[{'from': 'Canvas/home/skins', 'n': 1, 'bad': ['Home.onSkins is not a function']}]))
        self.assertEqual(bad['say'], '回调没执行（clickEvents 指向不存在的回调：Home.onSkins is not a function）')
        self.assertEqual(self.say(pr(emits=[{'from': 'Canvas/home/skins', 'n': 0, 'bad': []}]))['say'], '回调没执行（按钮上没有挂任何点击回调）')
        req = self.say(pr(pend=[{'what': 'tt.login'}, {'what': 'rewarded ad u1 (show without close)'}]))
        self.assertEqual(req['say'], '请求没回来：tt.login，rewarded ad u1 (show without close)')
        self.assertEqual(self.say(pr())['say'], '点到了也执行了，但画面没变')

    def test_click_listener_touch_end_and_touch_only_count_as_run(self):
        self.assertEqual(self.say(pr(emits=[], clicks=[{'path': 'Canvas/home/skins', 'listeners': True}]))['stage'], 'no_change')
        self.assertEqual(self.say(pr(emits=[], btn={'exists': True, 'interactable': True, 'touchEnd': 1}))['stage'], 'no_change')
        self.assertEqual(self.say(pr(emits=[], btn={'exists': False}), {'path': 'Canvas/drag', 'touchOnly': True})['stage'], 'hit')
        drag = pr(emits=[], btn={'exists': False}, hit={'path': 'Canvas/drag'}, end='Canvas/drag')
        self.assertEqual(self.say(drag, {'path': 'Canvas/drag', 'touchOnly': True})['stage'], 'no_change')

    def test_a_logged_error_is_a_clue_not_the_verdict(self):
        # HappyCup logged "Error 3804" on every tap; only an exception thrown out of the touch dispatch is the verdict
        got = self.say(pr(err={'src': 'cc.error', 'msg': 'Error 3804'}))
        self.assertEqual(got['stage'], 'no_change')
        self.assertEqual(got['say'], '点到了也执行了，但画面没变；2 秒内第一个报错（cc.error）：Error 3804')
        self.assertEqual(self.say({'installed': False})['stage'], 'unknown')


class Reactions(unittest.TestCase):
    def test_press_feedback_and_level_noise(self):
        got = rules('''
          const a = {m: {'C/b': {uuid: 'b', box: {x0: 0, y0: 0, x1: 100, y1: 40}}, 'C/b/l': {uuid: 'l', box: {x0: 10, y0: 10, x1: 90, y1: 30}},
                         'C/t': {uuid: 't', box: {x0: 0, y0: 100, x1: 100, y1: 140}}}};
          const scaled = {m: {'C/b': {uuid: 'b', box: {x0: 2, y0: 1, x1: 97, y1: 39}}, 'C/b/l': {uuid: 'l', box: {x0: 12, y0: 11, x1: 88, y1: 29}},
                         'C/t': {uuid: 't', box: {x0: 0, y0: 100, x1: 100, y1: 140}}}};
          const rebuilt = {m: Object.assign({}, scaled.m, {'C/b/l': {uuid: 'l2', box: {x0: 12, y0: 11, x1: 88, y1: 29}}})};
          const press = R.dropPress(R.snapDiff(a, scaled), 'C/b', a, scaled);
          const toggle = R.dropPress(R.snapDiff(a, rebuilt), 'C/b', a, rebuilt);
          const other = R.dropPress(R.snapDiff(a, scaled), 'C/t', a, scaled);
          const noisy = R.noisyParents(new Set(['Level/enemies/e1', 'Level/coins/c3#2']));
          const d = R.dropUnder({add: ['Level/enemies/e9', 'Canvas/pause/panel/resume'], gone: ['Level/coins/c4'], moved: [], text: ['Level/hud/score'], sprite: []}, noisy);
          return {press, toggle, other, noisy: [...noisy].sort(), d, resume: R.CLOSE.test('Canvas/InGamePause/ResumeRun') && R.CLOSE.test('继续游戏'),
            lv: ['new', 'legacy'].map(p => R.level('blocked_after_close', {engine: '2.x', policy: p})).concat([R.level('blocked_after_close', {engine: '3.x', policy: 'new'})])};''')
        self.assertEqual(got['press']['moved'], [])                              # SCALE transition stuck after a throw
        self.assertEqual(got['toggle']['moved'], ['C/b/l'])                      # a rebuilt child still counts
        self.assertEqual(sorted(got['other']['moved']), ['C/b', 'C/b/l'])         # another node's change still counts
        self.assertEqual(got['noisy'], ['Level/coins', 'Level/enemies'])
        self.assertEqual(got['d']['add'], ['Canvas/pause/panel/resume'])         # a spawned enemy is not the tap's
        self.assertEqual(got['d']['gone'], [])
        self.assertEqual(got['d']['text'], ['Level/hud/score'])
        self.assertEqual(got['lv'], ['block', 'warn', 'warn'])
        self.assertTrue(got['resume'])                                           # an in-game pause popup closes with Resume


PROBE_HARNESS = r'''
globalThis.CFG = { lib: %(lib)s };
const G = await import(%(gates)s);
const listeners = {};
globalThis.window = globalThis;
globalThis.addEventListener = (k, f) => { (listeners[k] = listeners[k] || []).push(f); };
const errs = [];
console.error = (...a) => errs.push(a.join(' '));
class Node {
  constructor(name, parent) { this.name = name; this.parent = parent || null; this.opacity = 255; this.comps = []; this.l = {}; }
  getComponent(K) { return this.comps.find((c) => (typeof K === 'string' ? c.constructor.name === K : c instanceof K)) || null; }
  hasEventListener(t) { return !!(this.l[t] && this.l[t].length); }
  on(t, f) { (this.l[t] = this.l[t] || []).push(f); }
  emit(t, a) { (this.l[t] || []).forEach((f) => f(a)); }
  dispatchEvent(ev) { ev.target = this; ev.currentTarget = this; this.emit(ev.type, ev); }
  getBoundingBoxToWorld() { return this.box || { x: 0, y: 0, width: 10, height: 10 }; }
}
class Button { constructor(node) { this.node = node; this.clickEvents = []; this.interactable = true; } }
class BlockInputEvents {}
class Home { onSkins() {} }
const EventHandler = { emitEvents(events, ev) { events.forEach((h) => { const c = h.target.getComponent(h._componentName); if (c && typeof c[h.handler] === 'function') c[h.handler](ev); }); } };
const scene = new Node('Scene'), canvas = new Node('Canvas', scene), btn = new Node('skins', canvas), mask = new Node('__mask', canvas);
mask.opacity = 0; mask.comps.push(new BlockInputEvents()); mask.box = { x: 0, y: 0, width: 750, height: 1334 };
const b = new Button(btn); btn.comps.push(b); canvas.comps.push(new Home());
b.clickEvents = [{ target: canvas, _componentName: 'Home', handler: 'onSkins' }, { target: canvas, _componentName: 'Home', handler: 'gone' }];
globalThis.cc = { Node, Button, BlockInputEvents, UITransform: undefined, director: { getScene: () => scene }, Component: { EventHandler },
  view: { getVisibleSize: () => ({ width: 750, height: 1334 }) }, error: (...a) => console.error(...a) };
globalThis.tt = { login() {}, showToast() {}, onShow() {}, getSystemInfoSync() { return {}; } };
const installed = eval(G.PROBE_JS);
const P = window.__bsProbe;
const open = () => { P.cur = { t0: Date.now(), hit: null, end: null, cancel: null, emits: [], clicks: [], calls: [], err: null }; };
// 1) a transparent full-screen mask takes the touch
open(); mask.dispatchEvent({ type: 'touchstart' }); const covered = P.cur.hit;
// 2) the button: touch start / end, its clickEvents (one entry points at a missing method), a click listener
open(); btn.dispatchEvent({ type: 'touchstart' }); btn.dispatchEvent({ type: 'touchend' });
cc.Component.EventHandler.emitEvents(b.clickEvents, { currentTarget: btn }); btn.on('click', () => {}); btn.emit('click', b);
const ran = { hit: P.cur.hit.path, end: P.cur.end, emits: P.cur.emits, clicks: P.cur.clicks };
// 3) a callback that throws out of the touch dispatch
open(); btn.on('touchend', () => { throw new Error('boom'); }); let rethrown = false;
try { btn.dispatchEvent({ type: 'touchend' }); } catch (e) { rethrown = e.message === 'boom'; }
const threw = P.cur.err;
// 4) unanswered tt.login, answered tt.login, fire-and-forget showToast, untouched on* / *Sync
open(); tt.login({ success() {} }); let keep; tt.login({ success() {} }); const pendBefore = P.pend.map((x) => x.what);
P.cur.calls = []; const t2 = { success() {} }; const realLogin = tt.login; tt.login(t2);
tt.showToast({ title: 'x' });
const pend1 = P.pend.length;
// 5) background noise: the same logged error in the 3 s before the tap is not this tap's
P.cur = null; cc.error('Error 3804'); open(); cc.error('Error 3804'); const noise = P.cur.err; cc.error('new one'); const fresh = P.cur.err;
// 6) outside a tap window nothing is recorded
P.cur = null; btn.dispatchEvent({ type: 'touchstart' }); tt.login({ success() {} });
console.log(JSON.stringify({ installed, again: eval(G.PROBE_JS), covered, ran, rethrown, threw, pendBefore, pend1, pendAfter: P.pend.length,
  wrapped: Object.keys(tt).filter((k) => tt[k].__bsWrapped).sort(), noise, fresh, errsLogged: errs.length }));
'''


class Probe(unittest.TestCase):
    def test_probe_on_a_fake_engine(self):
        got = node(PROBE_HARNESS % {'gates': json.dumps(GATES.as_uri()), 'lib': json.dumps((RR / 'lib.mjs').as_uri())})
        self.assertTrue(got['installed'] and got['again'])                       # idempotent
        self.assertEqual(got['covered'], {'path': 'Canvas/__mask', 'name': '__mask', 'block': True, 'button': False, 'opacity': 0, 'full': True})
        self.assertEqual(got['ran']['hit'], 'Canvas/skins')
        self.assertEqual(got['ran']['end'], 'Canvas/skins')
        self.assertEqual(got['ran']['emits'], [{'from': 'Canvas/skins', 'n': 2, 'bad': ['Home.gone is not a function']}])
        self.assertEqual(got['ran']['clicks'], [{'path': 'Canvas/skins', 'listeners': True}])
        self.assertTrue(got['rethrown'])                                          # the probe never swallows the game's error
        self.assertEqual(got['threw']['src'], 'callback')
        self.assertTrue(got['threw']['msg'].startswith('boom'))
        self.assertEqual(got['pendBefore'], ['tt.login', 'tt.login'])
        self.assertEqual(got['pend1'], 3)                                         # three logins wait, showToast does not
        self.assertEqual(got['wrapped'], ['login', 'showToast'])                  # on* / *Sync left alone
        self.assertIsNone(got['noise'])
        self.assertEqual(got['fresh']['msg'], 'new one')
        self.assertEqual(got['pendAfter'], 3)                                     # nothing recorded outside a window


class SuiteWiring(unittest.TestCase):
    def test_suite_uses_the_probe_and_the_new_verdicts(self):
        text = SUITE.read_text(encoding='utf-8')
        for needle in ("'blocked_after_close'", 'G.probeStart(', 'G.probeRead(', 'R.diagnose(', 'R.dropPress(', 'R.dropUnder(',
                       'A.play', 'enterGame(', 'GAME_BUDGET', 'notRun', 'afterClose('):
            self.assertIn(needle, text, needle)
        self.assertRegex(text, r"for \(const code of \[[^\]]*'blocked_after_close'")
        meta = json.loads((RR / 'suites' / 'button_sweep.json').read_text(encoding='utf-8'))
        self.assertTrue({'play', 'in_level'} <= set(meta['fields']))
        self.assertGreaterEqual(meta['timeout_s'], 1200)
        gates = GATES.read_text(encoding='utf-8')
        self.assertIn('export const PROBE_JS', gates)
        self.assertNotRegex(gates, r'\|\| [nx]\.getComponent\(cc\.RichText\)')    # trimmed engines: no Error 3804 noise
        probe = re.search(r'export const PROBE_JS = `(.*?)`;', gates, re.S).group(1)
        self.assertNotIn('${', probe)


if __name__ == '__main__':
    unittest.main(verbosity=1)

#!/usr/bin/env python3
"""暂停关窗照搬旧暂停值（甜点消消乐 R39-R47，2026-11-01）：audit_mobile_input 的拦截和提示。

  python3 test_pause_restore_rule.py
"""
import tempfile
import unittest
from pathlib import Path

from audit_mobile_input import audit, risks

# R47 assets/main/index.js 里的原样写法（压缩后一行）
R47_NATIVE = (b't.prototype.handle_continue=function(){var e=this;cc.tween(this.pauseNode).call(function(){'
              b'e.resumeRound(),e.is_pause=e.pauseWasClockPaused}).start()},'
              b't.prototype.handle_pause=function(){this.isOver||this.pauseNode.active||this.pauseClosing||'
              b'(this.pauseWasClockPaused=this.is_pause,this.suspendRound())}')
# R48 的改法：关窗按当前实际状态决定
R48_NATIVE = R47_NATIVE.replace(b'e.is_pause=e.pauseWasClockPaused', b'e.is_pause=e.clockShouldStayPaused()')
SOURCE = '''export class GameView {
    private pauseWasClockPaused = false;
    public handle_continue() {
        this.resumeRound();
        this.is_pause = this.pauseWasClockPaused;
    }
    public handle_pause() {
        if (this.isOver) return;
        this.pauseWasClockPaused = this.is_pause;
        this.suspendRound();
    }
}
'''
# CleosCloud 的写法：只在可玩状态时才存，存的也不是暂停值
GUARDED = (b's.prototype.pause=function(){"running"!==this.state&&"sandbox"!==this.state||'
           b'(this.beforePause=this.state,this.state="paused")},'
           b's.prototype.resume=function(){"paused"===this.state&&(this.state=this.beforePause)}')
# 存之前先判断了 is_pause：已经停着就不存
TESTED = (b'p.open=function(){if(this.is_paused)return;this.wasPaused=this.is_paused;this.is_paused=!0},'
          b'p.close=function(){this.is_paused=this.wasPaused}')
AUDIO = b'a.ad=function(){this.musicWasPaused=this.musicPaused},a.back=function(){this.musicPaused=this.musicWasPaused}'


def rules(found):
    return [(i['rule'], i.get('level'), i['live'], i['saved']) for i in found if i['rule'].startswith('pause_')]


class PauseRestoreRule(unittest.TestCase):
    def test_r47_native_is_blocked(self):
        self.assertEqual(rules(risks('assets/main/index.js', R47_NATIVE, True)),
                         [('pause_close_restores_saved_pause_flag', 'blocking', 'is_pause', 'pauseWasClockPaused')])

    def test_r48_native_passes(self):
        self.assertEqual(rules(risks('assets/main/index.js', R48_NATIVE, True)), [])

    def test_source_reports_restore_and_snapshot_lines(self):
        found = [i for i in risks('assets/GameView.ts', SOURCE.encode()) if i['rule'].startswith('pause_')]
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0]['line'], found[0]['snapshot_line'], found[0]['level']), (5, 9, 'blocking'))

    def test_declared_source_is_review(self):
        declared = SOURCE.replace('        this.pauseWasClockPaused = this.is_pause;',
                                  '        // pause-restore: 打开前已排除广告等待和发牌，见 qa/pause_case.json\n'
                                  '        this.pauseWasClockPaused = this.is_pause;')
        found = [i for i in risks('assets/GameView.ts', declared.encode()) if i['rule'].startswith('pause_')]
        self.assertEqual([(i['rule'], i['level']) for i in found], [('pause_restore_declared', 'review')])
        self.assertIn('qa/pause_case.json', found[0]['declared'])

    def test_guarded_or_non_pause_snapshot_is_review_only(self):
        self.assertEqual(rules(risks('main.js', GUARDED, True)),
                         [('pause_restore_snapshot_needs_runtime_case', 'review', 'state', 'beforePause')])
        self.assertEqual([r[:2] for r in rules(risks('main.js', TESTED, True))],
                         [('pause_restore_snapshot_needs_runtime_case', 'review')])

    def test_audio_and_comparisons_are_ignored(self):
        self.assertEqual(rules(risks('main.js', AUDIO, True)), [])
        compare = b'x.f=function(){return this.is_pause==this.pauseWas||this.pauseWas===this.is_pause}'
        self.assertEqual(rules(risks('main.js', compare, True)), [])

    def test_audit_blocks_source_and_lists_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / 'assets').mkdir()
            (project / 'assets' / 'GameView.ts').write_text(SOURCE, encoding='utf-8')
            result = audit(project, stage='code')
            self.assertEqual(result['status'], 'blocked')
            self.assertEqual([i['rule'] for i in result['known_risks']], ['pause_close_restores_saved_pause_flag'])
            (project / 'assets' / 'GameView.ts').write_text(SOURCE.replace(
                'this.is_pause = this.pauseWasClockPaused;',
                'this.is_pause = this.pauseWasClockPaused; // pause-restore: 已补暂停期间广告结束的短用例'), encoding='utf-8')
            result = audit(project, stage='code')
            self.assertEqual(result['status'], 'static_checks_clear_mobile_pending')
            self.assertEqual([i['rule'] for i in result['review_risks']], ['pause_restore_declared'])


if __name__ == '__main__':
    unittest.main()

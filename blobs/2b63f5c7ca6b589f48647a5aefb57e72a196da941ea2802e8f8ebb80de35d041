"""Negative controls for BGM preview startup, without claiming native-device audio."""
import copy
import json
import subprocess
import unittest
from pathlib import Path
from preview_audio_startup import judge

HERE = Path(__file__).resolve().parent
HOST = HERE.parents[1] / 'cocos-game-check/package-check/scripts/ad_regression/host.js'


def snap(time=0, paused=True, blocked=True):
    return {'schema': 'preview-audio-startup.v1', 'environment': 'browser_native_host',
            'gestures': 0, 'autoRequests': 1, 'previewRecoveries': 0,
            'tracks': [{'src': 'sound/bg.mp3', 'intent': True, 'paused': paused,
                        'volume': 1, 'currentTime': time, 'duration': 10, 'blocked': blocked}]}


def trace():
    a = snap(1, False, False)
    b = snap(1.4, False, False)
    a.update(gestures=1, previewRecoveries=1)
    b.update(gestures=1, previewRecoveries=1)
    return {'schema': 'preview-bgm-smoke.v1', 'before': snap(), 'after': a, 'sample': b,
            'action': {'kind': 'ordinary_play_touch'}}


class Verdict(unittest.TestCase):
    def test_browser_recovery_is_not_device_pass(self):
        r = judge(trace(), True)
        self.assertEqual(r['level'], 'pass')
        self.assertEqual(r['native_auto_request'], 'verified')
        self.assertEqual(r['tiktok_device'], 'unverified')
        self.assertIs(r['platform_passed'], False)

    def test_optimistic_engine_flag_without_time_progress_blocks(self):
        t = trace()
        t['after'] = t['sample'] = snap()
        self.assertEqual(judge(t, True)['level'], 'block')

    def test_no_default_request_cannot_be_fixed_by_preview_unlock(self):
        t = trace()
        t['before']['autoRequests'] = 0
        self.assertEqual(judge(t, True)['code'], 'default_request_missing')

    def test_absent_probe_and_player_mute_remain_unverified(self):
        self.assertEqual(judge(None)['level'], 'warn')
        t = trace()
        t['before']['tracks'][0]['volume'] = 0
        self.assertEqual(judge(t)['code'], 'muted_or_paused')

    def test_prior_interaction_is_not_cold_start(self):
        t = trace()
        t['before']['gestures'] = 1
        self.assertEqual(judge(t, True)['level'], 'block')

    def test_continuous_loop_progress_is_valid(self):
        t = trace()
        t['after']['tracks'][0]['currentTime'] = 9.9
        t['sample']['tracks'][0]['currentTime'] = .2
        self.assertEqual(judge(t, True)['level'], 'pass')


DRIVER = r"""
const assert=require('node:assert/strict'),fs=require('node:fs');
const src=fs.readFileSync(process.argv[1],'utf8');
const events=src.slice(src.indexOf('// ---------- events ----------'),src.indexOf('var hidden = false;'));
const audio=src.slice(src.indexOf('// ---------- audio ----------'),src.indexOf('// ---------- file system manager ----------'));
function target(){const callbacks={};return {addEventListener(k,f){(callbacks[k]??=[]).push(f)},fire(k,e){for(const f of callbacks[k]||[])f({preventDefault(){},touches:[],changedTouches:[],...e})}}}
function run(query=''){
 let denied=true;const elements=[];
 function A(){this.paused=true;this.src='';this.volume=1;this.loop=false;this.currentTime=0;this.duration=10;this.buffered={length:0};const h={};
  this.addEventListener=(k,f)=>(h[k]??=[]).push(f);this.emit=k=>(h[k]||[]).forEach(f=>f());
  this.play=()=>{this.calls=(this.calls||0)+1;if(denied)return Promise.reject({name:'NotAllowedError'});this.paused=false;this.emit('play');return Promise.resolve()};
  this.pause=()=>{this.paused=true;this.emit('pause')};this.removeAttribute=()=>this.src='';this.getAttribute=()=>this.src;elements.push(this);
 }
 const win=target(),main=target();
 const api=new Function('window','main','Q','NAudio','norm','beacon','now',events+'var hidden=false;'+audio+'return {InnerAudio,recoverPreviewAudio,H_,setHidden(x){hidden=x}};')(win,main,new URLSearchParams(query),A,x=>x,()=>{},()=>0);
 const track=new api.InnerAudio();track.src='bg.mp3';track.loop=true;
 return {...api,track,elements,win,main,allow(){denied=false},snapshot(){return win.__audioStartupSnapshot()}};
}
(async()=>{
 const r=run();r.track.play();await Promise.resolve();assert.equal(r.snapshot().autoRequests,1);assert.equal(r.track.paused,true);
 r.allow();r.main.fire('mousedown',{clientX:10,clientY:20});r.win.fire('mouseup',{clientX:10,clientY:20});await Promise.resolve();
 assert.equal(r.track.paused,false);assert.equal(r.snapshot().previewRecoveries,1);const count=r.elements[0].calls;r.recoverPreviewAudio();assert.equal(r.elements[0].calls,count);
 for(const state of ['mute','pause','stop','destroy','hide','interrupt']){
  const x=run();x.track.play();await Promise.resolve();x.allow();
  if(state==='mute')x.track.volume=0;else if(state==='hide')x.setHidden(true);else if(state==='interrupt')x.H_.audioBegin.emit({});else x.track[state]();
  const n=x.elements[0].calls;x.recoverPreviewAudio();assert.equal(x.elements[0].calls,n,state+' must not unlock');
 }
 const late=run();late.track.play();late.track.pause();await Promise.resolve();late.allow();late.recoverPreviewAudio();assert.equal(late.elements[0].calls,1,'late rejection after pause');
 const off=run('preview_audio_recovery=0');off.track.play();await Promise.resolve();off.allow();off.recoverPreviewAudio();assert.equal(off.track.paused,true,'negative control');
 const absent=run();absent.allow();absent.recoverPreviewAudio();assert.equal(absent.elements[0].calls,undefined,'never invent default play');
 console.log(JSON.stringify({passed:true,cases:12}));
})().catch(e=>{console.error(e);process.exitCode=1});
"""


class Host(unittest.TestCase):
    def test_actual_host_recovery_and_guards(self):
        result = subprocess.run(['node', '-e', DRIVER, str(HOST)], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['passed'])


if __name__ == '__main__':
    unittest.main()

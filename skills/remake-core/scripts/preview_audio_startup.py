"""Small preview-only BGM smoke check; native request, browser output and device proof stay separate.

Runs inside the existing home-screenshot Ego page. It neither toggles music nor
calls game methods, records no video/PCM, and makes at most one ordinary PLAY or settings-opener tap; never a music toggle.
The existing R09 output/volume regression remains responsible for full audio QA.
"""
import argparse
import json
from pathlib import Path


EGO_PROBE_JS = r"""
async function collectPreviewAudio(p) {
 const snapshot=()=>p.evaluate(()=>typeof window.__audioStartupSnapshot==='function'?window.__audioStartupSnapshot():
  typeof window.__webAudioStartupSnapshot==='function'?window.__webAudioStartupSnapshot():null);
 const before=await snapshot();
 if(!before)return {schema:'preview-bgm-smoke.v1',before:null,after:null,action:null};
 let action=null;
 const wanted=(before.tracks||[]).some(t=>t.intent&&t.volume>0&&(before.environment!=='browser_web_export'||t.loop===true));
 const moving=(before.tracks||[]).some(t=>t.intent&&t.volume>0&&!t.paused&&t.currentTime>0&&
  (before.environment!=='browser_web_export'||t.loop===true&&t.routeKnown===true&&(!t.contextState||t.contextState==='running')));
 if(!wanted)return {schema:'preview-bgm-smoke.v1',before,after:before,sample:before,action:null};
 if(wanted&&!moving){
  const at=await p.evaluate(()=>{
   const c=window.cc;if(!c||!c.director||!c.director.getScene||!c.Button)return null;
   const scene=c.director.getScene(),found=[];if(!scene)return null;
   function visit(n){
    if(!n.activeInHierarchy||n.opacity===0)return;
    const b=n.getComponent(c.Button);
    if(b&&b.enabled!==false&&b.interactable!==false&&/^(play|playbutton|btnplay|start|startbutton|startgame|start_1|opensettings|settingsbutton)$/i.test(n.name))found.push(n);
    (n.children||[]).forEach(visit);
   }
   visit(scene);const n=found.find(n=>/^playbutton$/i.test(n.name))||
    found.find(n=>/^(play|btnplay|start|startbutton|startgame|start_1)$/i.test(n.name))||found[0];
   // Cocos 2.x Web exports use cc.game.canvas; native browser hosts expose window.canvas.
   if(!n||typeof n.getBoundingBoxToWorld!=='function'||!c.view.getVisibleSize)return null;
   const canvas=c.game&&c.game.canvas||window.canvas;if(!canvas||!canvas.width||!canvas.height)return null;
   const r=Element.prototype.getBoundingClientRect.call(canvas),bb=n.getBoundingBoxToWorld();
   if(!r.width||!r.height)return null;
   const v=c.view,vp=v.getViewportRect(),mx=canvas.width/r.width,my=canvas.height/r.height;
   const x=r.left+(vp.x+(bb.x+bb.width/2)*v.getScaleX())/mx;
   const y=r.top+r.height-(vp.y+(bb.y+bb.height/2)*v.getScaleY())/my;
   return Number.isFinite(x)&&Number.isFinite(y)&&x>=r.left&&x<=r.right&&y>=r.top&&y<=r.bottom?{x,y,node:n.name}:null;
  });
  if(at){
   await p.cdp('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:at.x,y:at.y,id:0,radiusX:1,radiusY:1,force:1}]});
   await p.cdp('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
   action={kind:/^(opensettings|settingsbutton)$/i.test(at.node)?'ordinary_settings_touch':'ordinary_play_touch',...at};
  }
 }
 let after=await snapshot(),sample=after;
 const until=Date.now()+2500;
 while(Date.now()<until){
  await new Promise(r=>setTimeout(r,350));
  sample=await snapshot();
  if((sample?.tracks||[]).some(t=>t.intent&&t.volume>0&&!t.paused&&t.currentTime>0&&
   (sample.environment!=='browser_web_export'||t.loop===true&&t.routeKnown===true&&(!t.contextState||t.contextState==='running'))))break;
 }
 // One additional short sample verifies progression, not an optimistic play flag.
 after=sample;await new Promise(r=>setTimeout(r,350));sample=await snapshot();
 return {schema:'preview-bgm-smoke.v1',before,after,sample,action};
}
"""


def _web_track_playing(track):
    """Only the explicitly observed output path is calibrated, never engine flags."""
    import math
    if not isinstance(track, dict):
        return False
    def positive(value):
        return type(value) in (int, float) and math.isfinite(value) and value > 0
    if (track.get('loop') is not True or track.get('requested') is not True
            or not track.get('src') or not track.get('id') or not track.get('intent')
            or track.get('paused') is not False or track.get('ended') is not False
            or track.get('muted') is not False or track.get('routeKnown') is not True
            or not positive(track.get('volume')) or not positive(track.get('playbackRate'))):
        return False
    if track.get('kind') == 'webaudio':
        return (track.get('started') is True and track.get('active') is True
                and track.get('stopped') is False and track.get('hasBuffer') is True
                and positive(track.get('duration')) and track.get('contextState') == 'running')
    if track.get('kind') == 'html_media':
        return not track.get('routedThroughWebAudio') or track.get('contextState') == 'running'
    return False


def _judge_web(trace, expected_music=None):
    result = {'schema':'preview-bgm-verdict.v1', 'environment':'browser_web_export',
              'web_auto_request':'unverified', 'native_auto_request':'unverified',
              'tiktok_device':'unverified', 'platform_passed':False, 'trace':trace}
    def done(level, code, message):
        result.update(level=level, code=code, message=message)
        return result
    before, after, sample = (trace.get(key) for key in ('before','after','sample'))
    if (before.get('gestures') != 0 or before.get('installedWithEngine') is not False):
        return done('block','not_cold_start','Web 音频观测未在引擎启动前安装，或采样前已有输入，不能核准零输入默认请求。')
    requested = type(before.get('autoRequests')) is int and before['autoRequests'] > 0
    result['web_auto_request'] = 'verified' if requested else 'not_observed'
    if not requested:
        return done('block' if expected_music is True else 'warn','web_default_request_missing',
                    'Web 导出在零输入时未观察到循环 BGM 的实际播放请求；不能推断 Native 或 TikTok 设备结果。')
    defaults = {t.get('src') for t in before.get('tracks',[]) if isinstance(t,dict)
                and t.get('requested') is True and t.get('requestGesture') == 0 and t.get('loop') is True and t.get('src')}
    if not defaults:
        return done('block','web_default_source_missing','零输入请求未绑定真实循环音源，不能核准 Web 播放。')
    if not isinstance(after,dict) or not isinstance(sample,dict):
        return done('block','output_not_sampled','Web BGM 已请求，但缺少后续真实时间采样。')
    if any(s.get('environment') != 'browser_web_export' or s.get('schema') != 'preview-audio-startup.v1' for s in (after,sample)):
        return done('block','web_probe_changed','Web 前后观测环境不一致，不能核准。')
    import math
    for a in after.get('tracks',[]):
        for b in sample.get('tracks',[]):
            if (not _web_track_playing(a) or not _web_track_playing(b) or a['id'] != b['id']
                    or a['src'] != b['src'] or a['src'] not in defaults):
                continue
            # HTML media exposes its own playback clock; WebAudio exposes the
            # real context clock, gated by the observed live source and route.
            try:
                delta = b['currentTime'] - a['currentTime']
                if a['kind'] == 'html_media' and delta < 0 and a.get('duration',0) > 0:
                    delta += a['duration']
                if a.get('routedThroughWebAudio') and not b.get('contextTime',0) - a.get('contextTime',0) > 0.02:
                    continue
                if math.isfinite(delta) and delta > 0.02:
                    return done('pass','web_browser_playback_started',
                                'Web 导出零输入已请求循环 BGM，同一真实音源在有效输出路线中的播放时钟前进。仅 Web 预览通过；Native 与 TikTok 真机不由此验证。')
            except (KeyError,TypeError,ValueError):
                continue
    return done('block' if expected_music is True or trace.get('action') else 'warn',
                'web_output_unverified','Web 音源未证明有效路线中的真实播放推进；需查浏览器限制、context、停止状态、音量或输出路线，不能作为声音通过。')


def judge(trace, expected_music=None):
    before = trace.get('before') if isinstance(trace,dict) else None
    if (isinstance(trace,dict) and trace.get('schema') == 'preview-bgm-smoke.v1'
            and isinstance(before,dict) and before.get('schema') == 'preview-audio-startup.v1'
            and before.get('environment') == 'browser_web_export'):
        return _judge_web(trace,expected_music)
    return _judge_native(trace,expected_music)


def _judge_native(trace, expected_music=None):
    """Do not promote a browser result into a TikTok-device claim."""
    result = {'schema': 'preview-bgm-verdict.v1', 'environment': 'browser_native_host',
              'native_auto_request': 'unverified', 'tiktok_device': 'unverified',
              'platform_passed': False, 'trace': trace}

    def done(level, code, message):
        result.update(level=level, code=code, message=message)
        return result

    if not isinstance(trace, dict) or trace.get('schema') != 'preview-bgm-smoke.v1':
        return done('block' if expected_music is True else 'warn', 'not_measured', 'BGM 启动未测；不能把首页截图或播放标记算成出声通过。')
    before, after, sample = (trace.get(k) for k in ('before', 'after', 'sample'))
    if not isinstance(before, dict) or before.get('schema') != 'preview-audio-startup.v1':
        return done('block' if expected_music is True else 'warn', 'host_not_supported', '当前页面未提供受支持的 BGM 探针；保留未测，不推断测试包无声。')
    if before.get('environment') != 'browser_native_host' or before.get('gestures') != 0:
        return done('block', 'not_cold_start', 'BGM 证据不是零操作冷启动，不能核准默认播放。')
    requested = type(before.get('autoRequests')) is int and before['autoRequests'] > 0
    result['native_auto_request'] = 'verified' if requested else 'not_observed'
    if expected_music is True and not requested:
        return done('block', 'default_request_missing', '预期首页有 BGM，但原生包在点击前没有发起播放；先查默认开关与启动调用。')
    if not requested:
        return done('warn', 'default_request_not_observed', '未观察到首页默认 BGM 请求；可能是静音或该页无配乐，不能宣称自动播放通过。')
    wanted = [t for t in before.get('tracks', []) if t.get('intent') and t.get('volume', 0) > 0]
    if not wanted:
        return done('warn', 'muted_or_paused', '观察到播放请求，但当前静音或已暂停；保留玩家选择，BGM 输出未测。')
    if not isinstance(after, dict) or not isinstance(sample, dict):
        return done('block', 'output_not_sampled', '已发起 BGM 请求，但没有真实播放时间的后续采样，不能交接为声音正常。')
    advanced = False
    for a in after.get('tracks', []):
        for b in sample.get('tracks', []):
            if (a.get('src') and a.get('src') == b.get('src') and not a.get('paused') and not b.get('paused')
                    and a.get('intent') and b.get('intent') and a.get('volume', 0) > 0 and b.get('volume', 0) > 0):
                delta = b.get('currentTime', 0) - a.get('currentTime', 0)
                if delta < 0 and a.get('duration', 0) > 0:
                    delta += a['duration']
                advanced |= delta > 0.02
    if not advanced:
        if not trace.get('action'):
            return done('block' if expected_music is True else 'warn', 'ordinary_input_unavailable', 'BGM 尚未启动且没找到安全的普通 PLAY；需定点补一次普通输入，不能改点音乐按钮代替。')
        return done('block', 'stalled_after_normal_input', '普通 PLAY 后 BGM 真实播放时间仍不前进；阻止试玩交接，定位预览或音频失败。')
    if (sample.get('previewRecoveries') or 0) > 0:
        return done('pass', 'browser_autoplay_recovered', '原生包零操作已请求 BGM；浏览器自动播放受限，普通 PLAY 后已恢复。仅预览通过，TikTok 真机未验证。')
    return done('pass', 'browser_playback_started', '原生包零操作已请求 BGM，预览真实播放时间前进。仅预览通过，TikTok 真机未验证。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', required=True, type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--expect-home-bgm', action='store_true', default=None)
    args = parser.parse_args()
    result = judge(json.loads(args.trace.read_text()), args.expect_home_bgm)
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(encoded + '\n')
    print(encoded)
    return 1 if result['level'] == 'block' else 0


if __name__ == '__main__':
    raise SystemExit(main())

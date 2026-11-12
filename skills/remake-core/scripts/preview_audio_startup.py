"""Small preview-only BGM smoke check; native request, browser output and device proof stay separate.

Runs inside the existing home-screenshot Ego page. It neither toggles music nor
calls game methods, records no video/PCM, and makes at most one safe PLAY tap.
The existing R09 output/volume regression remains responsible for full audio QA.
"""
import argparse
import json
from pathlib import Path


EGO_PROBE_JS = r"""
async function collectPreviewAudio(p) {
 const snapshot=()=>p.evaluate(()=>typeof window.__audioStartupSnapshot==='function'?window.__audioStartupSnapshot():null);
 const before=await snapshot();
 if(!before)return {schema:'preview-bgm-smoke.v1',before:null,after:null,action:null};
 let action=null;
 const wanted=(before.tracks||[]).some(t=>t.intent&&t.volume>0);
 const moving=(before.tracks||[]).some(t=>t.intent&&t.volume>0&&!t.paused&&t.currentTime>0);
 if(!wanted)return {schema:'preview-bgm-smoke.v1',before,after:before,sample:before,action:null};
 if(wanted&&!moving){
  const at=await p.evaluate(()=>{
   const c=window.cc;if(!c||!c.director||!c.director.getScene||!c.Button)return null;
   const scene=c.director.getScene(),found=[];if(!scene)return null;
   function visit(n){
    if(!n.activeInHierarchy||n.opacity===0)return;
    const b=n.getComponent(c.Button);
    if(b&&b.enabled!==false&&b.interactable!==false&&/^(play|playbutton|btnplay|start|startbutton|startgame)$/i.test(n.name))found.push(n);
    (n.children||[]).forEach(visit);
   }
   visit(scene);const n=found.find(n=>/^playbutton$/i.test(n.name))||found[0];
   // This is only the calibrated Cocos 2.x native browser host; 3.x/Web keep an explicit untested result.
   if(!n||typeof n.getBoundingBoxToWorld!=='function'||!c.view.getVisibleSize)return null;
   const canvas=window.canvas,r=Element.prototype.getBoundingClientRect.call(canvas),bb=n.getBoundingBoxToWorld();
   const v=c.view,vp=v.getViewportRect(),mx=canvas.width/r.width,my=canvas.height/r.height;
   const x=r.left+(vp.x+(bb.x+bb.width/2)*v.getScaleX())/mx;
   const y=r.top+r.height-(vp.y+(bb.y+bb.height/2)*v.getScaleY())/my;
   return Number.isFinite(x)&&Number.isFinite(y)&&x>=r.left&&x<=r.right&&y>=r.top&&y<=r.bottom?{x,y,node:n.name}:null;
  });
  if(at){
   await p.cdp('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:at.x,y:at.y,id:0,radiusX:1,radiusY:1,force:1}]});
   await p.cdp('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
   action={kind:'ordinary_play_touch',...at};
  }
 }
 let after=await snapshot(),sample=after;
 const until=Date.now()+2500;
 while(Date.now()<until){
  await new Promise(r=>setTimeout(r,350));
  sample=await snapshot();
  if((sample?.tracks||[]).some(t=>t.intent&&t.volume>0&&!t.paused&&t.currentTime>0))break;
 }
 // One additional short sample verifies progression, not an optimistic play flag.
 after=sample;await new Promise(r=>setTimeout(r,350));sample=await snapshot();
 return {schema:'preview-bgm-smoke.v1',before,after,sample,action};
}
"""


def judge(trace, expected_music=None):
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

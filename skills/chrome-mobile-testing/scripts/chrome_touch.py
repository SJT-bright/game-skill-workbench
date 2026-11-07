#!/usr/bin/env python3
"""Run an Agent-reviewed local touch plan in Ego Lite and retain evidence.

Default browser is Ego Lite (user rules 2026-10-21 / 2026-10-27). Since 2026-10-27 the plan runs through Ego's
OFFICIAL API: the script ego_touch_runner.js is piped to `ego-browser nodejs`, creates its own uniquely named
TaskSpace, uses page.cdp() for the iPhone emulation, touch and network, and finishes only that space. There is no
--cdp-url any more: Ego exposes no DevTools endpoint and its guide forbids attaching Playwright. Two runs with the
same space name used to share one space (taskSpace(name) resumes it), and one run's finish() killed the other:
every run now gets a unique name. All Agent browser tests use Ego Lite. The user's own Chrome trial uses
serve_preview.py --keep.
Ego is ONLY for the agent's own tests (user 2026-10-23): a run never hands its window to the user. --handoff is
refused; the user plays the local preview link the agent gives in Codex (serve_preview.py --keep).

Never waits (user 2026-10-22/23): every run opens its OWN new isolated window, so several runs (other games, other
sessions, the same game) work at the same time and nothing is ever "occupied". Before opening, it sweeps old test
windows (cocos-game-core/scripts/browser_slots.py): gone-owner records retire; completed helpers close only
with matching current identity. Idle/live or unknown Ego ownership stays for current review. It then registers its
own window, heartbeats on every step and closes its own context on exit, also on SIGTERM.
It never queues behind anything. Report ids (same names as mobile-touch-computer-use): browser_route=ego_taskspace,
input_transport=ego_page_cdp, session_id = the numeric Ego spaceId, space_name = the unique name.

--record (or "record": true in the plan) saves frames to <out>/frames/NNNNN_TTTTTTTms.jpg for
scripts/audit_frame_glitches.py. In Ego the frames are sequential screenshots (a few per second, fps in the report):
enough for black screens, frozen screens and wrong pages. Mark one-frame flicker untested if Ego does not capture it.
Record short flows (one flow per run).

Startup/loading timing (scripts/audit_startup_loading.py of cocos-game-core reads these reports):
  plan "timing": true      no screenshots between steps (they would distort timing); navigation does not wait for 'load'
                           v7.5 (Ego route): a low-quality CDP screencast keeps the tab drawing (plan "screencast": false
                           turns it off), the page rAF rate is recorded per second (report frame_rate), and a run with any
                           whole second below 30 fps before the last mark is INVALID (timing_valid false, exit 2)
  plan "network": {"download_kbps": 10000, "upload_kbps": 5000, "latency_ms": 80}   real throttling via CDP
  plan "cache": "cold"|"warm"   cold = cache disabled; warm = one untimed visit first, then the timed visit
  plan "warmup_js": "<js>"      warm only: condition that ends the untimed visit (e.g. home is usable)
  plan "block_urls": ["*hint_button*"]   make those requests fail (stall/404 fault); action {"type":"unblock"} clears
  action {"type":"mark","name":"home_usable","wait_js":"<js returning true>","timeout_ms":30000}
         polls until true and records t_ms since navigation start (entry); timeout = failed run
  plan "init_js": "<js>"         runs before the game's own scripts: stub or break the platform SDK
                                 (e.g. a tt object without showModal, or a showModal that never calls back)
  plan "hang_urls" is unsupported in Ego. Keep the network condition untested if the plan requires it.
  action {"type":"background","ms":12000}  switches to another tab for ms and records the game page's
         document.visibilityState while away (must read "hidden" for the background test to count)
All network requests (url, status, encoded bytes, finish time) are recorded for the first-screen check.

Phone (user 2026-10-22): plan "device": "iphone_15" (default: 393x852, DPR 3, iPhone user agent, touch) |
  "iphone_se" (375x667, the short 9:16 ratio) | "iphone_15_pro_max"; or give viewport/dpr/user_agent yourself.
  Run the phone simulation in Ego Lite.
  This is Chromium with iPhone screen, touch and user agent, not Apple's WebKit.

UI layout and copy are read from the running game, never typed in (user rule 2026-10-21):
  action {"type":"dump_ui","screen":"play_9x19","kind":"gameplay"}   kind: home | page | gameplay | popup
         runs cocos-game-core/scripts/ui_dump.js in the page (Cocos 2.4 / 3.x), saves
         <out>/NNN-ui-dump-<screen>.json next to the screenshot NNN-ui-<screen>.png. Feed the dumps to
         extract_ui_layout.py (docs/ui-layout.json) and audit_copy_quality.py. A dump error stops the run.
         optional "purpose": home | result_win | result_fail | shop | skins | settings (General tab) |
         settings_sound (Sound tab) | map | pause | revive | trial | tutorial | gift | reward | other — audit_page_richness.py needs
         home, result_win, result_fail, settings, settings_sound (and map for a level game; legacy league/checkin remain readable),
         and also reads the screenshot of every dump (gameplay too) for flat-colour backgrounds (user 2026-10-21).
"""
import argparse
import base64
import hashlib
import re
import time
from datetime import datetime, timezone
import json
from pathlib import Path
import os
import platform
import signal
import sys

IPHONE_UA='Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
# Keep the iPhone simulation presets stable across Ego Lite runs.
DEVICES={'iphone_15':{'viewport':{'width':393,'height':852},'dpr':3,'user_agent':IPHONE_UA},          # tall ratio (default)
         'iphone_se':{'viewport':{'width':375,'height':667},'dpr':2,'user_agent':IPHONE_UA},          # short 9:16 ratio
         'iphone_15_pro_max':{'viewport':{'width':430,'height':932},'dpr':3,'user_agent':IPHONE_UA}}
PURPOSES={'home','result_win','result_fail','result_win_repeat','result_fail_repeat','league','shop','skins','settings','settings_sound','map','checkin','pause','revive','trial','tutorial','gift','reward','other'}
from urllib.parse import urlsplit

OBSERVER = """() => {
 window.__chromeTouchEvidence=[];
 for (const type of ['touchstart','touchmove','touchend','touchcancel','pointerdown','pointerup'])
  window.addEventListener(type,e=>{
   if(window.__chromeTouchEvidence.length<4000) window.__chromeTouchEvidence.push({
    type, trusted:e.isTrusted, target:e.target.id||e.target.tagName, pointerType:e.pointerType,
    touches:e.touches?Array.from(e.touches,t=>({id:t.identifier,x:t.clientX,y:t.clientY})):null,
    changed:e.changedTouches?Array.from(e.changedTouches,t=>({id:t.identifier,x:t.clientX,y:t.clientY})):null
   });
  },{capture:true,passive:true});
}"""
HIDE_JS = """() => {
 for (const [k,v] of [['hidden',true],['visibilityState','hidden'],['webkitHidden',true]])
  Object.defineProperty(document,k,{configurable:true,get:()=>v});
 document.dispatchEvent(new Event('visibilitychange'));document.dispatchEvent(new Event('webkitvisibilitychange'));
 window.dispatchEvent(new Event('pagehide'));window.dispatchEvent(new Event('blur'));
}"""
SHOW_JS = """() => {
 for (const k of ['hidden','visibilityState','webkitHidden']) delete document[k];
 document.dispatchEvent(new Event('visibilitychange'));document.dispatchEvent(new Event('webkitvisibilitychange'));
 window.dispatchEvent(new Event('pageshow'));window.dispatchEvent(new Event('focus'));
}"""
MAX_FRAMES=20000   # about 5.5 minutes at 60 fps
# Timing validity (LunasJade D3 problem 4, v7.5): a covered Ego window is throttled to ~1 fps while
# visibilityState stays 'visible', which stretches every frame-driven loading step. Timing runs therefore
# (1) keep a tiny CDP screencast running from the timed navigation on (plan "screencast": false turns it
# off) and (2) record the page's requestAnimationFrame rate; a timed run whose median is below MIN_TIMING_FPS
# is INVALID (status failed, timing_valid false) and cannot be LOAD-03 evidence.
MIN_TIMING_FPS=30
RAF_JS = """(()=>{if(window.__ctRaf)return;const R=window.__ctRaf={frames:0,t0:performance.now(),perSec:[]};let sec=0,cnt=0;
 const f=()=>{const s=Math.floor((performance.now()-R.t0)/1000);while(s>sec){if(R.perSec.length<900)R.perSec.push(cnt);cnt=0;sec++;}R.frames++;cnt++;requestAnimationFrame(f);};
 requestAnimationFrame(f);})();"""
# Prepended to ego_touch_runner.js (after CONFIG) for timing runs: wraps the official taskSpace() so the
# page starts a low-quality screencast right after the timed Page.navigate, and writes fps.json just
# before the runner finishes its own space. Uses only the documented TaskSpace/Page API + page.cdp().
TIMING_PRELUDE = r"""
if (CONFIG.timing) {
  const __ctFs = await import("node:fs/promises");
  const __ctTs = globalThis.taskSpace;
  const __ctNote = { screencast: false, screencast_error: null, warmup: null };
  globalThis.taskSpace = async (...a) => {
    const t = await __ctTs(...a);
    const page0 = t.page.bind(t);
    t.page = (...b) => {
      const p = page0(...b);
      if (p.__ctWrapped) return p;
      p.__ctWrapped = true;
      const cdp = p.cdp.bind(p);
      p.cdp = async (m, params) => {
        const r = await cdp(m, params);
        // Start at the runner's first Page.enable (before about:blank emulation and the timed navigation) and
        // re-assert right after the timed Page.navigate: the throttle bites in the first seconds otherwise.
        if ((m === "Page.enable" || m === "Page.navigate") && CONFIG.screencast) {
          if (m === "Page.navigate") __ctNote.screencast = false;
          for (let i = 0; i < 3 && !__ctNote.screencast; i++) {
            try { await cdp("Page.startScreencast", { format: "jpeg", quality: 5, maxWidth: 120, maxHeight: 240, everyNthFrame: 1 }); __ctNote.screencast = true; __ctNote.screencast_error = null; }
            catch (e) { if (/already active/i.test(String(e))) { __ctNote.screencast = true; break; } __ctNote.screencast_error = String(e).slice(0, 300); await new Promise(r => setTimeout(r, 250)); }
          }
        }
        // Warm-up before the clock starts (the runner sets entry_epoch after its cache setting): a fresh Ego
        // window draws ~1 fps for its first seconds. Wait (max 10 s) until about:blank runs >= 30 fps.
        if (m === "Network.setCacheDisabled" && !__ctNote.warmup) {
          __ctNote.warmup = [];
          for (let i = 0; i < 10; i++) {
            let f = null;
            try { f = (await cdp("Runtime.evaluate", { expression: "new Promise(d=>{let n=0;const t0=performance.now();const f=()=>{n++;if(performance.now()-t0<1000)requestAnimationFrame(f);else d(Math.round(n*1000/(performance.now()-t0)));};requestAnimationFrame(f);})", awaitPromise: true, returnByValue: true })).result.value; } catch (_) {}
            __ctNote.warmup.push(f);
            if (typeof f === "number" && f >= 30) break;
          }
        }
        return r;
      };
      return p;
    };
    const fin = t.finish.bind(t);
    t.finish = async (...f) => {
      let raf = null, error = null;
      try { raf = await t.page("p1").evaluate(() => window.__ctRaf ? { frames: window.__ctRaf.frames, perSec: window.__ctRaf.perSec, ms: Math.round(performance.now() - window.__ctRaf.t0) } : null); }
      catch (e) { error = String(e).slice(0, 300); }
      try { await __ctFs.writeFile(CONFIG.out + "/fps.json", JSON.stringify(Object.assign({ raf, error }, __ctNote))); } catch (_) {}
      return fin(...f);
    };
    return t;
  };
}
"""


def frame_rate(fps_doc, window_ms=None):
    """rAF rate of a timing run. Every whole second from navigation up to window_ms (the last mark; the whole
    run when None) must reach MIN_TIMING_FPS: a covered Ego tab runs ~1 fps exactly during loading and 60 fps
    afterwards, so a run-wide median would hide it (seen 2026-10-29 with the screencast off: 1, 1, 60, 60...).
    Returns (fps used for the verdict, median of whole seconds); (None, None) when unmeasured."""
    raf=(fps_doc or {}).get('raf') or {}
    per=[n for n in (raf.get('perSec') or []) if isinstance(n,int)]
    median=sorted(per)[len(per)//2] if per else None
    if window_ms is not None:per=per[:max(1,-(-int(window_ms)//1000))]
    if per:return min(per),median
    # Shorter than one whole second: average over the page life, if it lived at least 0.2 s.
    frames,ms=raf.get('frames'),raf.get('ms')
    if isinstance(frames,int) and isinstance(ms,(int,float)) and ms>=200:
        avg=round(frames*1000/ms);return avg,avg
    return None,None
READ = """() => ({url:location.href,ua:navigator.userAgent,width:innerWidth,height:innerHeight,
 dpr:devicePixelRatio,maxTouchPoints:navigator.maxTouchPoints,ontouchstart:'ontouchstart' in window,
 canvas:Array.from(document.querySelectorAll('canvas'),c=>{let r=c.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}}),
 cocos:window.cc&&cc.sys?{isMobile:cc.sys.isMobile,capabilities:cc.sys.capabilities}:null,
 bodyText:document.body.innerText.slice(0,12000),events:window.__chromeTouchEvidence||[]})"""


ON_TERM=[lambda:None]


def skill_script_dirs():
    here = Path(__file__).resolve()
    return [here.parents[2] / 'remake-core' / 'scripts',                 # remake package (2026-10-27 split)
            here.parents[2] / 'cocos-game-core' / 'scripts',             # installed skills folder
            here.parents[3] / 'skills' / 'cocos-game-core' / 'scripts']  # unpacked package


def load_slots():
    """browser_slots module of the main skill, or None (the test still runs, only without the sweep)."""
    for d in skill_script_dirs():
        if (d / 'browser_slots.py').is_file():
            sys.path.insert(0, str(d))
            try:
                import browser_slots
                return browser_slots
            except Exception:
                return None
    return None


def ui_dump_js(action):
    here = Path(__file__).resolve()
    candidates = [Path(action['js_file'])] if action.get('js_file') else []
    candidates += [here.parents[2] / 'remake-core' / 'scripts' / 'ui_dump.js',              # remake package (2026-10-27 split)
                   here.parents[2] / 'cocos-game-core' / 'scripts' / 'ui_dump.js',            # installed skills folder
                   here.parents[3] / 'skills' / 'cocos-game-core' / 'scripts' / 'ui_dump.js']  # unpacked package
    for c in candidates:
        if c.is_file():
            return c.read_text(encoding='utf-8')
    raise ValueError('ui_dump.js not found in cocos-game-core; install the full skill package')


# R4O4 (R4N3 没做完的): ui_dump.js answers {error: 引擎还没起来…, retry: true} while the engine is not up (3.x before
# System.import('cc'), a scene still loading). dump_ui then waits and dumps again instead of failing the run at once.
DUMP_TRIES=3
DUMP_RETRY_WAIT_S=1.0
def dump_with_retry(grab,screen,tries=DUMP_TRIES,wait_s=DUMP_RETRY_WAIT_S,sleep=time.sleep):
    """grab() -> the ui_dump result. retry:true -> sleep(wait_s) and grab again, up to `tries` dumps; ValueError with
    the last reason (and how many dumps were tried) when it never becomes a dump. Returns (dump, dumps_tried)."""
    for n in range(1,tries+1):
        dump=grab()
        if isinstance(dump,dict) and not dump.get('error'):return dump,n
        if not(isinstance(dump,dict) and dump.get('retry')) or n==tries:break
        sleep(wait_s)
    why=(dump or {}).get('error','no result') if isinstance(dump,dict) or dump is None else 'no result'
    more=' (tried %d times, %.0f s apart)'%(n,wait_s) if isinstance(dump,dict) and dump.get('retry') else ''
    raise ValueError('dump_ui %s failed: %s%s'%(screen,why,more))

def validate(plan):
    device=plan.get('device','iphone_15' if 'viewport' not in plan else None)
    if device is not None and device not in DEVICES:raise ValueError('device must be one of '+', '.join(sorted(DEVICES)))
    preset=DEVICES.get(device,{})
    for key in ('viewport','dpr','user_agent'):
        if key not in plan and key in preset:plan[key]=preset[key]
    plan['device']=device or 'custom'
    viewport=plan.get('viewport',{'width':393,'height':852})
    if set(viewport) != {'width','height'} or any(type(x) is not int or not 200<=x<=3000 for x in viewport.values()):
        raise ValueError('Invalid viewport')
    dpr=plan.get('dpr',2)
    if type(dpr) not in (int,float) or not 1<=dpr<=4:raise ValueError('Invalid DPR')
    actions=plan.get('actions',[])
    if not isinstance(actions,list) or len(actions)>200:raise ValueError('Invalid action count')
    net=plan.get('network')
    if net is not None and (not isinstance(net,dict) or any(type(net.get(k)) not in (int,float) or net.get(k)<0
                            for k in ('download_kbps','upload_kbps','latency_ms'))):
        raise ValueError('network needs download_kbps, upload_kbps, latency_ms')
    if plan.get('cache','cold') not in {'cold','warm'}:raise ValueError('cache must be cold or warm')
    for action in actions:
        if action.get('type') not in {'tap','drag','cancel','wait','assert_text','snapshot','mark','background','unblock','unhang','dump_ui'}:raise ValueError('Unknown action')
        if action['type']=='dump_ui' and (not re.fullmatch(r'[A-Za-z0-9_.:-]{1,60}' if plan.get('art_capture') else r'[A-Za-z0-9_.-]{1,60}',str(action.get('screen',''))) or
                                          action.get('kind') not in {'home','page','gameplay','popup'}):
            raise ValueError('dump_ui needs screen (letters/digits/_-.) and kind home/page/gameplay/popup')
        if action['type']=='dump_ui' and action.get('purpose','other') not in PURPOSES:
            raise ValueError('dump_ui purpose must be one of '+', '.join(sorted(PURPOSES)))
        if action['type']=='mark' and (not action.get('name') or not action.get('wait_js') or not 0<action.get('timeout_ms',30000)<=120000):
            raise ValueError('mark needs name, wait_js and timeout_ms <= 120000')
        if action['type']=='background' and not 0<action.get('ms',0)<=120000:raise ValueError('background ms must be 1..120000')
        if action['type']=='wait' and not 0<=action.get('ms',0)<=10000:raise ValueError('Wait exceeds bound')
        if action['type'] in {'drag','cancel'}:
            points=action.get('points',[])
            if not 2<=len(points)<=100:raise ValueError('Invalid drag points')
            for point in points:
                if not isinstance(point,list) or len(point)!=2:raise ValueError('Invalid point')
                if any(type(v) not in (int,float) for v in point):raise ValueError('Invalid coordinate')
    return viewport,dpr,actions


def run(args):
    """Retired Chrome test route. Kept as an explicit refusal for old import callers."""
    raise ValueError('EGO_ONLY_TEST_POLICY: Agent browser tests must use run_ego; Chrome is user trial only.')


def run_ego(args):
    """Default route: run the plan in Ego Lite through its official API (ego-browser nodejs)."""
    import secrets, shutil, subprocess
    parsed=urlsplit(args.url)
    if parsed.scheme not in {'http','https'} or parsed.hostname not in {'127.0.0.1','localhost','::1'}:
        raise ValueError('This helper only accepts an authorized local test origin')
    if parsed.username or parsed.password:raise ValueError('Credentials in URL are not accepted')
    plan=json.loads(args.plan.read_text(encoding='utf-8-sig'))
    viewport,dpr,actions=validate(plan)
    if plan.get('hang_urls') or any(a.get('type')=='unhang' for a in actions):
        raise ValueError('hang_urls/unhang need live request interception, which the Ego API does not offer: use init_js to '
                         'stub a callback that never fires, or block_urls for a failing request')
    exe=shutil.which('ego-browser')
    if not exe:
        raise ValueError('ego-browser not found: install/upgrade Ego Lite per the ego-browser Skill (references/install.md), '
                         'then run `ego-browser skill`. Browser tests must stay in Ego; Chrome is user trial only.')
    art_config = None
    if plan.get('art_capture'):
        if not args.project or plan.get('cache')=='warm' or plan.get('timing'):
            raise ValueError('art_capture requires --project, cold cache and an untimed plan')
        project = Path(args.project).resolve()
        cfg = plan['art_capture']
        build = (project / cfg['build']).resolve()
        matrix = json.loads((project/'docs/art/capture-plan.json').read_text(encoding='utf-8'))['cases']
        states = {row['id']:row for row in matrix}
        plan_sha = hashlib.sha256(args.plan.read_bytes()).hexdigest()
        for action in actions:
            if action['type'] == 'dump_ui':
                state = states.get(action.get('case'), {})
                if (state.get('planSha') != plan_sha or state.get('screen') != action['screen'] or
                    state.get('kind') != action['kind']):
                    raise ValueError('unregistered or changed art action recipe for '+str(action.get('case')))
        art_config = {'project':str(project),'build':str(build),
            'out':str((project / (getattr(args,'art_dumps',None) or cfg['out'])).resolve()),'module':(Path(__file__).resolve().parents[2] /
            'remake-core/scripts/art_capture_round.mjs').as_uri()}
    args.out.mkdir(parents=True,exist_ok=False)
    out=args.out.resolve()
    label=(args.name or args.out.name).strip()[:40] or 'touch'
    space_name='touch %s %s %s'%(label,datetime.now().strftime('%Y%m%d-%H%M%S'),secrets.token_hex(3))
    report={'platform':platform.platform(),'started_at':datetime.now(timezone.utc).isoformat(),
            'browser_channel':'ego (official API)','browser_route':'ego_taskspace','input_transport':'ego_page_cdp',
            'headless':False,'viewport_requested':viewport,'dpr_requested':dpr,'device':plan.get('device'),
            'space_name':space_name,'steps':[],'status':'running',
            'boundary':'Browser simulation in Ego Lite; no physical phone, Native or live IAA acceptance.'}
    report_path=out/'report.json'
    def save():report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    slots=load_slots();slot_id=None
    if slots is not None:
        try:
            swept=slots.sweep(close=True)
            report['sweep_before_open']={'freed':len(swept.get('freed',[])),'active_windows':swept.get('active_windows')}
            slot_id=slots.register('touch_run',name=args.name or args.out.name,pid=os.getpid(),project=args.project,url=args.url)
            report['browser_slot']=slot_id
        except Exception as error:
            report['browser_slot_error']=str(error)
    save()
    needs_dump=any(a['type']=='dump_ui' for a in actions)
    timing=bool(plan.get('timing'))
    run_plan=dict(plan,actions=actions)
    if timing:run_plan['init_js']=RAF_JS+('\n'+str(plan['init_js']) if plan.get('init_js') else '')
    config={'plan':run_plan,'out':str(out),'url':args.url,'viewport':viewport,'dpr':dpr,
            'userAgent':plan.get('user_agent',IPHONE_UA),'timing':timing,'screencast':timing and plan.get('screencast',True) is not False,
            'record':bool(args.record or plan.get('record')),'spaceName':space_name,'readJs':READ,'observerJs':OBSERVER,
            'hideJs':HIDE_JS,'showJs':SHOW_JS,'uiDumpJs':ui_dump_js(next(a for a in actions if a['type']=='dump_ui')) if needs_dump else None}
    if art_config:
        config['artCapture'] = art_config
    runner=(Path(__file__).resolve().parent/'ego_touch_runner.js').read_text(encoding='utf-8')
    script='const CONFIG = %s;\n%s%s'%(json.dumps(config,ensure_ascii=False),TIMING_PRELUDE if timing else '',runner)
    budget=60+sum(a.get('ms',0)/1000+a.get('timeout_ms',0)/1000+15 for a in actions)+(150 if plan.get('cache')=='warm' else 0)
    try:
        r=subprocess.run([exe,'nodejs'],input=script,capture_output=True,text=True,encoding='utf-8',timeout=budget)
        report['ego_output']=(r.stdout[-3000:]+'\n'+r.stderr[-3000:]).strip()
        report['ego_exit_code']=r.returncode
    except subprocess.TimeoutExpired:
        report['ego_output']='ego-browser nodejs did not finish within %d s'%budget
    result_path=out/'ego-result.json'
    result=json.loads(result_path.read_text(encoding='utf-8')) if result_path.is_file() else {'status':'failed','error':'no ego-result.json'}
    for key in ('space_id','space_ownership','steps','marks','requests','background','page_errors','ui_dumps','entry_epoch',
                'cache_disabled','network_applied','warmup_done','recording','status','error','space_finished','cleanup_error','api',
                'emulation_observed','emulation_reapplied','emulation_restored'):
        if key in result:report[key]=result[key]
    report['session_id']=result.get('space_id')
    report['timing']=bool(plan.get('timing'));report['cache_mode']=plan.get('cache','cold')
    report['init_js_sha256']=hashlib.sha256(str(plan['init_js']).encode()).hexdigest() if plan.get('init_js') else None
    for step in report.get('steps',[]):
        if step.get('screenshot'):step['screenshot']=Path(step['screenshot']).name
    for dump in report.get('ui_dumps',[]):
        f=out/dump['path']
        if f.is_file():dump['sha256']=hashlib.sha256(f.read_bytes()).hexdigest()
    finished=result.get('space_finished') is True
    if timing:
        fps_path=out/'fps.json'
        fps_doc=json.loads(fps_path.read_text(encoding='utf-8')) if fps_path.is_file() else None
        marks=[v for v in (report.get('marks') or {}).values() if isinstance(v,(int,float))]
        window=max(marks) if marks else None
        low,median=frame_rate(fps_doc,window)
        report['frame_rate']={'lowest_fps_in_window':low,'median_fps':median,'min_fps':MIN_TIMING_FPS,'window_ms':window,
                              'screencast':bool(fps_doc and fps_doc.get('screencast')),
                              'screencast_error':fps_doc and fps_doc.get('screencast_error'),
                              'warmup_fps':fps_doc and fps_doc.get('warmup'),
                              'per_second':((fps_doc or {}).get('raf') or {}).get('perSec',[])[:300]}
        report['timing_valid']=low is not None and low>=MIN_TIMING_FPS
        if not report['timing_valid'] and report.get('status')!='failed':
            report['status']='failed'
            report['error']=('timing run invalid: page ran at %s fps (< %d) before the last mark; it cannot be LOAD-03 '
                             'evidence. Keep the Ego window uncovered / leave the screencast on and re-run.'%(low,MIN_TIMING_FPS))
    report['cleanup_pending']=not finished and result.get('space_id') is not None
    if report.get('status')=='running':report['status']='failed'
    save()
    if slot_id:
        try:
            if report['cleanup_pending']:
                slots.register('ego_space',name=args.name or args.out.name,space_id=result.get('space_id'),project=args.project)
            slots.release(slot_id)
        except Exception:pass
    if report['status']=='failed':
        raise RuntimeError('Ego run failed: %s (report %s)'%(str(report.get('error') or report.get('ego_output',''))[:600],report_path))
    return report_path


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--art-dumps', type=Path, help='art_capture output for this round; keeps the signed action plan unchanged')
    p.add_argument('--url',required=True);p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--headless',action='store_true');p.add_argument('--handoff',action='store_true',help='refused: Ego windows are never handed to the user')
    p.add_argument('--record',action='store_true',help='save sequential Ego screenshots for dynamic glitch analysis')
    p.add_argument('--cdp-url',help='removed 2026-10-27: Ego has no DevTools endpoint; runs go through ego-browser nodejs')
    p.add_argument('--channel',default='chrome',help=argparse.SUPPRESS)
    p.add_argument('--user-approved-chrome',action='store_true',help='retired: all Agent browser tests require Ego; Chrome is user trial only')
    p.add_argument('--name',help='short label shown to other sessions in browser_slots.py list, e.g. "测试线 音量复核"')
    p.add_argument('--project',help='game folder (only a label for the slot list; runs never queue)')
    args=p.parse_args()
    # EGO_ONLY_TEST_POLICY: user 2026-11-06; Chrome is only the user's trial window.
    if args.user_approved_chrome:
        raise SystemExit('测试只允许 Ego（用户 2026-11-06）；--user-approved-chrome 已停用。Chrome 仅供用户试玩链接。')
    if args.handoff:
        raise SystemExit('Not allowed (user 2026-10-23): Ego / test windows are only for the agent\'s own tests and are '
                         'never handed to the user. Give the user the local preview link in Codex instead: '
                         'python <cocos-game-core>/scripts/serve_preview.py --directory <web export> --keep --name "<line> user trial"')
    def _stop(signum,frame):
        # Do not equate a dropped CDP connection with context closure. Preserve a pending record for owner review.
        try:ON_TERM[0]()
        except Exception:pass
        os._exit(143)
    for _sig in (getattr(signal,'SIGTERM',None),getattr(signal,'SIGBREAK',None)):
        if _sig is not None:
            try:signal.signal(_sig,_stop)
            except (OSError,ValueError):pass
    if args.cdp_url:
        raise SystemExit('--cdp-url was removed (2026-10-27): Ego Lite exposes no DevTools endpoint and its guide forbids '
                         'attaching Playwright. Drop --cdp-url: the plan runs through `ego-browser nodejs` automatically.')
    try:print(json.dumps({'report':str(run_ego(args))},ensure_ascii=False))
    except Exception as error:
        print(json.dumps({'status':'failed','error':str(error)},ensure_ascii=False),file=sys.stderr);raise SystemExit(2)

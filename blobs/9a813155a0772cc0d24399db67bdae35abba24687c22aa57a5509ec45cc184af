#!/usr/bin/env python3
"""Run an Agent-reviewed local touch plan in a Chromium browser and retain evidence.

Default browser is Ego Lite (user rule 2026-10-21): pass --cdp-url with Ego's DevTools endpoint
(see `ego-browser skill` for how to get it) and the plan runs in a fresh isolated context inside Ego;
Ego itself is never closed. Launching Google Chrome (no --cdp-url) is only allowed after the user agreed.
Ego is ONLY for the agent's own tests (user 2026-10-23): a run never hands its window to the user. --handoff is
refused; the user plays the local preview link the agent gives in Codex (serve_preview.py --keep).

Never waits (user 2026-10-22/23): every run opens its OWN new isolated window, so several runs (other games, other
sessions, the same game) work at the same time and nothing is ever "occupied". Before opening, it sweeps old test
windows (cocos-game-to-english/scripts/browser_slots.py): gone-owner records retire; completed helpers close only
with matching current identity. Idle/live or unknown Ego ownership stays for current review. It then registers its
own window, heartbeats on every step and closes its own context on exit, also on SIGTERM.
If connecting to Ego fails it immediately retries once on a fresh connection; it never queues behind anything.

--record (or "record": true in the plan) also saves every rendered frame (about 60 per second) to
<out>/frames/NNNNN_TTTTTTTms.jpg for scripts/audit_frame_glitches.py (black flashes, flicker, one-frame pops),
which static screenshots cannot see. Record short flows (one flow per run) to keep the folder small.

Startup/loading timing (scripts/audit_startup_loading.py of cocos-game-to-english reads these reports):
  plan "timing": true      no screenshots between steps (they would distort timing); navigation does not wait for 'load'
  plan "network": {"download_kbps": 10000, "upload_kbps": 5000, "latency_ms": 80}   real throttling via CDP
  plan "cache": "cold"|"warm"   cold = cache disabled; warm = one untimed visit first, then the timed visit
  plan "warmup_js": "<js>"      warm only: condition that ends the untimed visit (e.g. home is usable)
  plan "block_urls": ["*hint_button*"]   make those requests fail (stall/404 fault); action {"type":"unblock"} clears
  action {"type":"mark","name":"home_usable","wait_js":"<js returning true>","timeout_ms":30000}
         polls until true and records t_ms since navigation start (entry); timeout = failed run
  plan "init_js": "<js>"         runs before the game's own scripts: stub or break the platform SDK
                                 (e.g. a tt object without showModal, or a showModal that never calls back)
  plan "hang_urls": ["*logo*"]   those requests never answer (no callback); action {"type":"unhang"} lets
                                 later requests through (the held ones stay pending, like a lost callback)
  action {"type":"background","ms":12000}  switches to another tab for ms and records the game page's
         document.visibilityState while away (must read "hidden" for the background test to count)
All network requests (url, status, encoded bytes, finish time) are recorded for the first-screen check.

Phone (user 2026-10-22): plan "device": "iphone_15" (default: 393x852, DPR 3, iPhone user agent, touch) |
  "iphone_se" (375x667, the short 9:16 ratio) | "iphone_15_pro_max"; or give viewport/dpr/user_agent yourself.
  Ego Lite and Chrome are the same Chromium engine: run the phone simulation once, in one browser (Ego Lite by default).
  This is Chromium with iPhone screen, touch and user agent, not Apple's WebKit.

UI layout and copy are read from the running game, never typed in (user rule 2026-10-21):
  action {"type":"dump_ui","screen":"play_9x19","kind":"gameplay"}   kind: home | page | gameplay | popup
         runs cocos-game-to-english/scripts/ui_dump.js in the page (Cocos 2.4 / 3.x), saves
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
# User 2026-10-22: the final phone simulation is an iPhone in one browser (Ego Lite and Chrome are the same Chromium).
DEVICES={'iphone_15':{'viewport':{'width':393,'height':852},'dpr':3,'user_agent':IPHONE_UA},          # tall ratio (default)
         'iphone_se':{'viewport':{'width':375,'height':667},'dpr':2,'user_agent':IPHONE_UA},          # short 9:16 ratio
         'iphone_15_pro_max':{'viewport':{'width':430,'height':932},'dpr':3,'user_agent':IPHONE_UA}}
PURPOSES={'home','result_win','result_fail','league','shop','skins','settings','settings_sound','map','checkin','pause','revive','trial','tutorial','gift','reward','other'}
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
READ = """() => ({url:location.href,ua:navigator.userAgent,width:innerWidth,height:innerHeight,
 dpr:devicePixelRatio,maxTouchPoints:navigator.maxTouchPoints,ontouchstart:'ontouchstart' in window,
 canvas:Array.from(document.querySelectorAll('canvas'),c=>{let r=c.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}}),
 cocos:window.cc&&cc.sys?{isMobile:cc.sys.isMobile,capabilities:cc.sys.capabilities}:null,
 bodyText:document.body.innerText.slice(0,12000),events:window.__chromeTouchEvidence||[]})"""


ON_TERM=[lambda:None]


def skill_script_dirs():
    here = Path(__file__).resolve()
    return [here.parents[2] / 'cocos-game-to-english' / 'scripts',             # installed skills folder
            here.parents[3] / 'skills' / 'cocos-game-to-english' / 'scripts']  # unpacked package


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
    candidates += [here.parents[2] / 'cocos-game-to-english' / 'scripts' / 'ui_dump.js',            # installed skills folder
                   here.parents[3] / 'skills' / 'cocos-game-to-english' / 'scripts' / 'ui_dump.js']  # unpacked package
    for c in candidates:
        if c.is_file():
            return c.read_text(encoding='utf-8')
    raise ValueError('ui_dump.js not found next to cocos-game-to-english; install the full skill package')


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
        if action['type']=='dump_ui' and (not re.fullmatch(r'[A-Za-z0-9_.-]{1,60}',str(action.get('screen',''))) or
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
    from playwright.sync_api import sync_playwright
    parsed=urlsplit(args.url)
    if parsed.scheme not in {'http','https'} or parsed.hostname not in {'127.0.0.1','localhost','::1'}:
        raise ValueError('This helper only accepts an authorized local test origin')
    if parsed.username or parsed.password:raise ValueError('Credentials in URL are not accepted')
    plan=json.loads(args.plan.read_text(encoding='utf-8-sig'))
    viewport,dpr,actions=validate(plan)
    args.out.mkdir(parents=True,exist_ok=False)
    report={'platform':platform.platform(),'started_at':datetime.now(timezone.utc).isoformat(),
            'browser_channel':'ego (cdp)' if args.cdp_url else args.channel,'input_transport':'playwright_cdp_touch',
            'headless':args.headless and not args.cdp_url,
            'viewport_requested':viewport,'dpr_requested':dpr,'device':plan.get('device'),'steps':[],'status':'running',
            'boundary':'Browser simulation; no physical phone, Native or live IAA acceptance.'}
    report_path=args.out/'report.json'
    def save():report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    slots=load_slots();slot_id=None
    if slots is not None:
        try:
            swept=slots.sweep(close=True)          # close only free old windows; running ones of others stay
            report['sweep_before_open']={'freed':len(swept.get('freed',[])),'active_windows':swept.get('active_windows'),
                                         'soft_cap_windows':swept.get('soft_cap_windows'),'free_ram_mb':swept.get('free_ram_mb')}
            slot_id=slots.register('touch_run',name=args.name or args.out.name,pid=os.getpid(),project=args.project,
                                   url=args.url)
            report['browser_slot']=slot_id
        except Exception as error:
            report['browser_slot_error']=str(error)
    def on_term():
        report.update(status='terminated_cleanup_pending',cleanup_pending=True,
                      error='Helper interrupted; original browser context closure must be verified');save()
        if slot_id:slots.heartbeat(slot_id,state='cleanup_pending',cleanup_pending=True)
    ON_TERM[0]=on_term
    def beat():
        if slot_id:
            try:slots.heartbeat(slot_id)
            except Exception:pass
    save()
    with sync_playwright() as pw:
        browser=None;context=None
        try:
            if args.cdp_url:
                # Ego Lite (or another browser the user named). Never wait: a failed connection is retried once at
                # once on a fresh connection; the run then gets its own new window (context) below.
                try:browser=pw.chromium.connect_over_cdp(args.cdp_url,timeout=20000)
                except Exception as first:
                    report['cdp_retry']=str(first)[:300];save()
                    browser=pw.chromium.connect_over_cdp(args.cdp_url,timeout=20000)
            else:
                if not args.user_approved_chrome:
                    raise ValueError('Default browser is Ego Lite: pass --cdp-url <Ego endpoint>. Launching Chrome needs the '
                                     "user's explicit consent; add --user-approved-chrome only after the user agreed.")
                browser=pw.chromium.launch(channel=None if args.channel=='chromium' else args.channel,headless=args.headless)
            report['browser_version']=browser.version
            ua=plan.get('user_agent',f'Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{browser.version} Mobile Safari/537.36')
            context=browser.new_context(viewport=viewport,device_scale_factor=dpr,is_mobile=True,has_touch=True,user_agent=ua)
            context.add_init_script('(' + OBSERVER + ')()')
            if plan.get('init_js'):
                context.add_init_script(str(plan['init_js']))
            page=context.new_page();page.set_default_timeout(10000)
            cdp=context.new_cdp_session(page)
            recording={'on':bool(args.record or plan.get('record')),'count':0,'t0':None,'dropped':0}
            if recording['on']:
                frame_dir=args.out/'frames';frame_dir.mkdir()
                def on_frame(params):
                    ts=params['metadata']['timestamp']
                    if recording['t0'] is None:recording['t0']=ts
                    if recording['count']<MAX_FRAMES:
                        name=f"{recording['count']:05d}_{int((ts-recording['t0'])*1000):07d}ms.jpg"
                        (frame_dir/name).write_bytes(base64.b64decode(params['data']));recording['count']+=1
                    else:recording['dropped']+=1
                    cdp.send('Page.screencastFrameAck',{'sessionId':params['sessionId']})
                cdp.on('Page.screencastFrame',on_frame)
                cdp.send('Page.startScreencast',{'format':'jpeg','quality':70,'maxWidth':720,'maxHeight':1600,'everyNthFrame':1})
            timing=bool(plan.get('timing'))
            report.update(timing=timing,cache_mode=plan.get('cache','cold'),profile=plan.get('profile'),fault=plan.get('fault'),
                          startup_plan_sha256=plan.get('startup_plan_sha256'),marks={},requests=[],background=[])
            cdp.send('Network.enable')
            reqs={}
            def on_resp(e):
                r=e.get('response',{});reqs[e['requestId']]={'url':r.get('url','')[:300],'status':r.get('status'),'mime':r.get('mimeType')}
            def on_done(e):
                item=reqs.pop(e['requestId'],None)
                if item is not None and len(report['requests'])<5000 and report.get('entry_epoch'):
                    item.update(bytes=int(e.get('encodedDataLength',0)),t_ms=round((time.time()-report['entry_epoch'])*1000))
                    report['requests'].append(item)
            def on_fail(e):
                if len(report['requests'])<5000 and report.get('entry_epoch'):
                    report['requests'].append({'url':'(failed) '+e.get('errorText',''),'failed':True,'blocked':e.get('blockedReason'),
                                               't_ms':round((time.time()-report['entry_epoch'])*1000)})
            cdp.on('Network.responseReceived',on_resp);cdp.on('Network.loadingFinished',on_done);cdp.on('Network.loadingFailed',on_fail)
            if plan.get('block_urls'):
                cdp.send('Network.setBlockedURLs',{'urls':[str(u) for u in plan['block_urls']]})
            report['init_js_sha256']=hashlib.sha256(str(plan['init_js']).encode()).hexdigest() if plan.get('init_js') else None
            hang={'on':bool(plan.get('hang_urls')),'held':[]}
            if hang['on']:
                import fnmatch
                pats=[str(u) for u in plan['hang_urls']]
                def on_paused(e):
                    url=e['request']['url']
                    if hang['on'] and any(fnmatch.fnmatch(url,pt) for pt in pats):
                        hang['held'].append(url[:200])            # never answered: a lost callback
                    else:
                        try:cdp.send('Fetch.continueRequest',{'requestId':e['requestId']})
                        except Exception:pass
                cdp.on('Fetch.requestPaused',on_paused)
                cdp.send('Fetch.enable',{'patterns':[{'urlPattern':'*'}]})
            net=plan.get('network')
            if net:
                cdp.send('Network.emulateNetworkConditions',{'offline':False,'latency':net['latency_ms'],
                         'downloadThroughput':net['download_kbps']*1000/8,'uploadThroughput':net['upload_kbps']*1000/8})
            report['network_applied']=net or None
            if plan.get('cache','cold')=='warm':
                cdp.send('Network.setCacheDisabled',{'cacheDisabled':False})
                page.goto(args.url,wait_until='commit',timeout=60000)
                if plan.get('warmup_js'):page.wait_for_function(plan['warmup_js'],timeout=120000,polling=100)
                else:page.wait_for_load_state('load',timeout=60000)
                report['warmup_done']=True
            else:
                cdp.send('Network.setCacheDisabled',{'cacheDisabled':True})
            report['cache_disabled']=plan.get('cache','cold')=='cold'
            cdp.send('Emulation.setTouchEmulationEnabled',{'enabled':True,'maxTouchPoints':5})
            cdp.send('Emulation.setEmitTouchEventsForMouse',{'enabled':True,'configuration':'mobile'})
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            report['entry_epoch']=time.time()
            response=page.goto(args.url,wait_until='commit' if timing else 'load',timeout=60000)
            report['http_status']=response.status if response else None
            def now_ms():return round((time.time()-report['entry_epoch'])*1000)
            def capture(label,action,shot=True):
                if timing and not shot:
                    report['steps'].append({'label':label,'action':action,'t_ms':now_ms()})
                else:
                    page.screenshot(path=str(args.out/f'{len(report["steps"]):03d}-{label}.png'))
                    report['steps'].append({'label':label,'action':action,'t_ms':now_ms(),'observed':page.evaluate(READ)})
                report['page_errors']=list(errors);save();beat()
            if not timing:capture('initial',{'type':'navigate'})
            for action in actions:
                kind=action['type']
                if kind=='tap':
                    if 'selector' in action:
                        locator=page.locator(action['selector'])
                        if locator.count()!=1:raise ValueError('Tap target must be unique')
                        locator.tap()
                    else:page.touchscreen.tap(action['x'],action['y'])
                elif kind in {'drag','cancel'}:
                    points=action['points']
                    def touch(name,point):
                        cdp.send('Input.dispatchTouchEvent',{'type':name,'touchPoints':[] if point is None else [{'x':point[0],'y':point[1],'id':0}]})
                    touch('touchStart',points[0])
                    for point in points[1:]:touch('touchMove',point)
                    touch('touchCancel' if kind=='cancel' else 'touchEnd',None)
                elif kind=='wait':page.wait_for_timeout(action.get('ms',0))
                elif kind=='assert_text':
                    from playwright.sync_api import expect
                    expect(page.locator(action['selector'])).to_have_text(action['equals'])
                elif kind=='mark':
                    deadline=time.time()+action.get('timeout_ms',30000)/1000
                    while True:
                        try:ok=bool(page.evaluate(action['wait_js']))
                        except Exception:ok=False
                        if ok:report['marks'][action['name']]=now_ms();break
                        if time.time()>deadline:raise ValueError('mark %s not reached within %d ms'%(action['name'],action.get('timeout_ms',30000)))
                        time.sleep(action.get('poll_ms',30)/1000)
                elif kind=='background':
                    other=context.new_page();other.bring_to_front();t_start=now_ms();method='tab_switch'
                    other.wait_for_timeout(min(300,action['ms']))
                    state=page.evaluate('document.visibilityState')
                    if state!='hidden':
                        # Headless or some embedded browsers keep background tabs "visible": emulate the
                        # visibility change the engine listens to (document.hidden + visibilitychange).
                        page.evaluate(HIDE_JS);method='emulated_visibility'
                        state=page.evaluate('document.visibilityState')
                    other.wait_for_timeout(max(0,action['ms']-300))
                    if method=='emulated_visibility':page.evaluate(SHOW_JS)
                    other.close();page.bring_to_front()
                    report['background'].append({'from_ms':t_start,'to_ms':now_ms(),'visibility_while_away':state,'method':method})
                elif kind=='unblock':
                    cdp.send('Network.setBlockedURLs',{'urls':[]})
                elif kind=='dump_ui':
                    dump=page.evaluate(ui_dump_js(action),{'maxNodes':action.get('max_nodes',4000)})
                    if not isinstance(dump,dict) or dump.get('error'):
                        raise ValueError('dump_ui %s failed: %s'%(action['screen'],(dump or {}).get('error','no result')))
                    dump.update(screen=action['screen'],kind=action['kind'],purpose=action.get('purpose','other'),url=page.url,t_ms=now_ms(),
                                producer='chrome_touch.dump_ui',viewport=viewport,plan_dpr=dpr)
                    path=args.out/f'{len(report["steps"]):03d}-ui-dump-{action["screen"]}.json'
                    dump['screenshot']=f'{len(report["steps"]):03d}-ui-{action["screen"]}.png'   # saved by capture() below
                    path.write_text(json.dumps(dump,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
                    report.setdefault('ui_dumps',[]).append({'screen':action['screen'],'kind':action['kind'],'path':path.name,
                        'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'nodes':len(dump.get('nodes',[])),'errors':len(dump.get('errors',[]))})
                elif kind=='unhang':
                    hang['on']=False;report['held_requests']=list(hang['held'])
                capture('ui-'+action['screen'] if kind=='dump_ui' else kind,action,shot=kind in ('snapshot','dump_ui') or not timing)
            if recording['on']:
                page.wait_for_timeout(300);cdp.send('Page.stopScreencast')
                report['recording']={'frames':recording['count'],'first_frame_epoch':recording['t0'],'dropped_after_limit':recording['dropped'],'dir':str(args.out/'frames'),
                                     'next':'python <cocos-game-to-english>/scripts/audit_frame_glitches.py <frames dir> --report <report.json>'}
            report['status']='completed_pending_business_and_visual_review';save()
        except Exception as error:
            report['status']='failed';report['error']=str(error);save();raise
        finally:
            cleanup_errors=[]
            if browser is not None:
                if context is not None:
                    try:context.close()         # only our isolated context; the user's Ego stays open
                    except Exception as error:cleanup_errors.append('context: '+str(error))
                try:browser.close()
                except Exception as error:cleanup_errors.append('browser connection: '+str(error))
            report['cleanup_pending']=bool(cleanup_errors)
            report['cleanup_errors']=cleanup_errors
            save()
            if slot_id:
                try:
                    if cleanup_errors:slots.heartbeat(slot_id,state='cleanup_pending',cleanup_pending=True)
                    else:slots.release(slot_id) # only unregister after successful owned-context cleanup
                except Exception:pass
            if cleanup_errors:raise RuntimeError('Browser cleanup pending; registry retained: '+'; '.join(cleanup_errors))
    return report_path


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',required=True);p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--headless',action='store_true');p.add_argument('--handoff',action='store_true',help='refused: Ego windows are never handed to the user')
    p.add_argument('--record',action='store_true',help='save every rendered frame for dynamic glitch analysis')
    p.add_argument('--cdp-url',help="Ego Lite DevTools endpoint, e.g. http://127.0.0.1:9222 (default route)")
    p.add_argument('--channel',default='chrome',help='only with --user-approved-chrome: chrome, or chromium = bundled Playwright browser')
    p.add_argument('--user-approved-chrome',action='store_true',help='the user explicitly agreed to use Chrome instead of Ego this time')
    p.add_argument('--name',help='short label shown to other sessions in browser_slots.py list, e.g. "测试线 音量复核"')
    p.add_argument('--project',help='game folder (only a label for the slot list; runs never queue)')
    args=p.parse_args()
    if args.handoff:
        raise SystemExit('Not allowed (user 2026-10-23): Ego / test windows are only for the agent\'s own tests and are '
                         'never handed to the user. Give the user the local preview link in Codex instead: '
                         'python <cocos-game-to-english>/scripts/serve_preview.py --directory <web export> --keep --name "<line> user trial"')
    def _stop(signum,frame):
        # Do not equate a dropped CDP connection with context closure. Preserve a pending record for owner review.
        try:ON_TERM[0]()
        except Exception:pass
        os._exit(143)
    for _sig in (getattr(signal,'SIGTERM',None),getattr(signal,'SIGBREAK',None)):
        if _sig is not None:
            try:signal.signal(_sig,_stop)
            except (OSError,ValueError):pass
    try:print(json.dumps({'report':str(run(args))},ensure_ascii=False))
    except Exception as error:
        print(json.dumps({'status':'failed','error':str(error)},ensure_ascii=False),file=sys.stderr);raise SystemExit(2)

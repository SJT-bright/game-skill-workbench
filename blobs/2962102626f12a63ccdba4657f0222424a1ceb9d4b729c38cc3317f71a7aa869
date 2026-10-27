"""Owned persistent Chrome touch preview; close only this context on service exit."""
import argparse,asyncio,json,os,signal,sys,time
from pathlib import Path
async def main(a):
 from playwright.async_api import async_playwright
 result=Path(a.result);profile=Path(a.profile);profile.mkdir(parents=True,exist_ok=True)
 async with async_playwright() as p:
  ctx=await p.chromium.launch_persistent_context(str(profile),channel='chrome',headless=False,viewport={'width':a.width,'height':a.height},screen={'width':a.width,'height':a.height},device_scale_factor=3,is_mobile=True,has_touch=True,user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Version/17.5 Mobile/15E148 Safari/604.1',args=['--window-size='+str(a.width+80)+','+str(a.height+116)])
  try:
   page=ctx.pages[0] if ctx.pages else await ctx.new_page();cd=await ctx.new_cdp_session(page)
   await cd.send('Emulation.setTouchEmulationEnabled',{'enabled':True,'maxTouchPoints':5})
   await cd.send('Emulation.setEmitTouchEventsForMouse',{'enabled':True,'configuration':'mobile'})
   await page.add_init_script("window.__previewTouchEvents=[];['touchstart','touchmove','touchend','touchcancel'].forEach(t=>addEventListener(t,e=>__previewTouchEvents.push({type:e.type,trusted:e.isTrusted,t:performance.now()}),true));")
   await page.goto(a.url,wait_until='domcontentloaded',timeout=20000);await page.wait_for_timeout(500)
   # Device configuration is active for physical mouse input; calibration uses CDP.
   # Chrome mouse-to-touch may defer the down acknowledgement until release.
   # Dispatch the bounded gesture concurrently so down cannot block its own up.
   await cd.send('Input.dispatchMouseEvent',{'type':'mouseMoved','x':8,'y':8})
   press=asyncio.create_task(cd.send('Input.dispatchMouseEvent',{'type':'mousePressed','x':8,'y':8,'button':'left','buttons':1,'clickCount':1}))
   await asyncio.sleep(.1)
   move=asyncio.create_task(cd.send('Input.dispatchMouseEvent',{'type':'mouseMoved','x':12,'y':12,'buttons':1}))
   await asyncio.sleep(.1)
   release=asyncio.create_task(cd.send('Input.dispatchMouseEvent',{'type':'mouseReleased','x':12,'y':12,'button':'left','buttons':0,'clickCount':1}))
   try:await asyncio.wait_for(asyncio.gather(press,move,release),5)
   except asyncio.TimeoutError:pass
   pointer_trace=await page.evaluate('__previewTouchEvents')
   if not any(e['type']=='touchstart' and e['trusted'] for e in pointer_trace) or not any(e['type']=='touchend' and e['trusted'] for e in pointer_trace):raise RuntimeError('Mouse-to-touch calibration failed')
   frames=[]
   for frame in page.frames:
    frames.append(await frame.evaluate("({url:location.href,viewport:[innerWidth,innerHeight],ua:navigator.userAgent,touch:navigator.maxTouchPoints,dpr:devicePixelRatio})"))
   result.write_text(json.dumps({'status':'touch_window_ready','pid':os.getpid(),'url':a.url,'browser':'google_chrome','visible_window_verified':await page.evaluate("document.visibilityState==='visible'"),'mouse_to_touch':True,'input_mode':'chrome_cdp_mouse_to_touch','mouse_conversion_events':pointer_trace,'frames':frames},indent=2))
   while not page.is_closed():
    try:os.kill(a.parent,0)
    except OSError:break
    await asyncio.sleep(1)
  finally:await ctx.close()
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--url',required=True);ap.add_argument('--width',type=int,default=390);ap.add_argument('--height',type=int,default=844);ap.add_argument('--profile',required=True);ap.add_argument('--result',required=True);ap.add_argument('--parent',type=int,required=True);a=ap.parse_args()
 try:asyncio.run(main(a))
 except Exception as e:Path(a.result).write_text(json.dumps({'status':'failed','error':str(e)}));raise

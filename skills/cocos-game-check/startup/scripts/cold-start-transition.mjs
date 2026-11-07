// Run with Ego Lite's official nodejs command. The observer runs before navigation.
import fs from 'node:fs/promises';
import path from 'node:path';

const tick = ms => new Promise(resolve => setTimeout(resolve, ms));

function observe(probe) {
  const result = window.__cocosTransition = {frames:0, changes:[], violations:[], heldFrames:0};
  let prior, director, started = false;
  function sample(source) {
    try {
      const s = probe();
      const key = JSON.stringify(s);
      const row = {frame:result.frames, at:performance.now(), source, ...s};
      if (key !== prior) { result.changes.push(row); prior = key; }
      result.current = row;
      started ||= !!(s.boot || s.loading || s.enginePresented);
      if (started && !s.ready && !s.boot && !s.loading) {
        if (!result.violations.length) result.violations.push(row);
      }
      if (source === 'after-draw' && !s.ready && (s.loading || s.enginePresented) && !s.boot) result.heldFrames++;
    } catch (e) {
      result.observerError = String(e);
    }
  }
  function frame() {
    result.frames++;
    if (!director && window.cc?.director?.on && cc.Director?.EVENT_AFTER_DRAW) {
      director = cc.director;
      director.on(cc.Director.EVENT_AFTER_DRAW, () => sample('after-draw'));
    }
    sample('animation-frame');
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
  addEventListener('touchend', e => { if (e.isTrusted) result.trustedTouch = true; }, true);
}

export async function run({out, cases, probe, label = 'Cocos cold start transition'}) {
  await fs.mkdir(out, {recursive:true});
  const task = await taskSpace(label + ' ' + Date.now());
  const page = task.page('p1');
  const rows = [];
  let controlStopped = false;
  function checkControl(error) {
    const details = String(error?.code || '') + ' ' + String(error?.message || error);
    if (/hard stop|safety timeout|EGO_.*(?:USER_CONTROL|CONTROL_REQUIRED|HANDED_OFF|HARD_STOP)/i.test(details)) {
      controlStopped = true;
      throw error;
    }
  }
  await fs.writeFile(path.join(out,'session.json'), JSON.stringify({space_id:task.spaceId,space_name:task.name}));
  console.log(JSON.stringify({space_id:task.spaceId,space_name:task.name}));
  try {
    await page.cdp('Page.enable',{});
    await page.cdp('Network.enable',{});
    await page.cdp('Network.setCacheDisabled',{cacheDisabled:true});
    await page.cdp('Page.addScriptToEvaluateOnNewDocument',{source:`(${observe.toString()})(${probe})`});
    for (const c of cases) {
      const [width,height] = c.viewport;
      const metrics = {width,height,deviceScaleFactor:1,mobile:true,screenWidth:width,screenHeight:height};
      const view = async () => {
        await page.cdp('Emulation.setDeviceMetricsOverride',metrics);
        await page.cdp('Emulation.setVisibleSize',{width,height});
      };
      await view();
      await page.cdp('Emulation.setTouchEmulationEnabled',{enabled:true,maxTouchPoints:5});
      await page.cdp('Fetch.enable',{patterns:[{urlPattern:c.requiredUrl,requestStage:'Request'}]});
      await page.events();
      const row = {name:c.name,build:c.build,viewport:c.viewport,url:c.url,browser_route:'ego_taskspace',input_transport:'ego_page_cdp',requiredUrl:c.requiredUrl};
      rows.push(row);
      const read = () => page.evaluate(() => window.__cocosTransition || null);
      const until = async (f, desc) => {
        const deadline = Date.now()+25000;
        do { const value = await f(); if (value) return value; await tick(35); } while (Date.now()<deadline);
        throw Error(desc);
      };
      const shot = async kind => {
        const res = await page.cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
        const name = c.name+'-'+kind+'.png';
        await fs.writeFile(path.join(out,name),Buffer.from(res.data,'base64'));
        return name;
      };
      let request;
      try {
        await page.goto(c.url,{waitUntil:'commit'});
        await view();
        request = await until(async () => (await page.events()).find(e => (e.method || e.name)==='Fetch.requestPaused')?.params, 'Required request never paused');
        row.heldAsset = request.request.url;
        const first = await read();
        row.duringHold = await until(async () => {
          const r = await read();
          if (r?.observerError) throw Error(r.observerError);
          if (r?.current?.ready) throw Error('Game reported ready while the required asset was held');
          return r?.heldFrames >= (first?.heldFrames || 0)+12 ? r : null;
        }, 'No evidence of twelve loading/early-home frames while request was held');
        row.duringHoldShot = await shot('during-hold');
        await page.cdp('Fetch.continueRequest',{requestId:request.requestId});
        request = null;
        const ready = await until(async () => {
          const r = await read();
          return r?.current?.ready && !r.current.boot && !r.current.loading && r.current.action ? r : null;
        }, 'The first home never became operable');
        row.beforeInput = ready;
        row.homeShot = await shot('home');
        const {x,y} = ready.current.action;
        if (![x,y].every(Number.isFinite) || x<0 || y<0 || x>=width || y>=height) throw Error('Home input target is outside viewport');
        await page.cdp('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y,id:0}]});
        await page.cdp('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
        row.afterInput = await until(async () => {
          const r = await read();
          return r?.current?.outcome && r.trustedTouch ? r : null;
        }, 'Trusted touch did not reach the expected game state');
        row.verdict = row.beforeInput.violations.some(v => v.legacy) ? 'blocked_legacy_frame'
          : row.beforeInput.violations.length ? 'blocked_uncovered_frame'
          : row.duringHold.current.loading && row.beforeInput.changes.some(s => s.boot) ? 'pass' : 'incomplete';
      } catch (e) {
        checkControl(e);
        row.error = String(e);
        row.verdict = 'incomplete';
      } finally {
        if (!controlStopped) {
          if (request) await page.cdp('Fetch.continueRequest',{requestId:request.requestId});
          await page.cdp('Fetch.disable',{});
        }
        await fs.writeFile(path.join(out,'results.json'),JSON.stringify(rows,null,2));
      }
      console.log(JSON.stringify({name:row.name,verdict:row.verdict,error:row.error,heldAsset:row.heldAsset}));
    }
  } catch (e) {
    checkControl(e);
    throw e;
  } finally {
    if (!controlStopped) {
      await task.finish({keep:[]});
      let absent = false;
      for (let i=0;i<20;i++) {
        absent = !(await listTaskSpaces()).some(s => s.id === task.spaceId);
        if (absent) break;
        await tick(150);
      }
      await fs.writeFile(path.join(out,'closure.json'),JSON.stringify({space_id:task.spaceId,absent}));
      if (!absent) throw Error('Ego TaskSpace is still listed');
    }
  }
  if (rows.some(r => r.verdict !== 'pass')) process.exitCode = 1;
}

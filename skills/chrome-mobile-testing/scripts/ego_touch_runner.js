// ego_touch_runner.js - executed by `ego-browser nodejs` (official Ego Lite API, guide v2.1.0). chrome_touch.py prepends
// `const CONFIG = {...};` and pipes the whole script on stdin. Uses ONLY the documented TaskSpace/Page API plus
// page.cdp(): no Playwright, no external CDP endpoint, no second browser (user 2026-10-27: Ego is the test browser).
//
// Space rules (root cause of "test spaces keep disappearing"): taskSpace(name) RESUMES an existing space with the same
// name, so two runs with the same name shared one space and one run's finish() killed the other. Every run here gets a
// unique name (line + time + random) from chrome_touch.py, creates its own space, and finishes only that space.
const fs = await import("node:fs/promises");
const C = CONFIG;
const plan = C.plan;
const res = {
  space_name: C.spaceName, space_id: null, steps: [], marks: {}, requests: [], background: [], page_errors: [],
  ui_dumps: [], status: "running", api: "ego-browser nodejs (TaskSpace + Page API + page.cdp)", input_transport: "ego_page_cdp",
};
let entryEpoch = null;
let task = null;
let page = null;
const nowMs = () => Math.round(Date.now() - entryEpoch);
const save = async () => fs.writeFile(C.out + "/ego-result.json", JSON.stringify(res, null, 1) + "\n");
const reqs = new Map();
let mono0 = null; // [monotonic seconds, wall ms] of the first network event
function takeEvents(list) {
  for (const e of list || []) {
    const m = e.method || e.name, p = e.params || e.data || {};
    if (m === "Network.requestWillBeSent" && mono0 === null && p.wallTime) mono0 = [p.timestamp, p.wallTime * 1000];
    const tms = (ts) => (mono0 && entryEpoch ? Math.round(mono0[1] + (ts - mono0[0]) * 1000 - entryEpoch) : (entryEpoch ? nowMs() : null));
    if (m === "Network.responseReceived") {
      const r = p.response || {};
      reqs.set(p.requestId, { url: String(r.url || "").slice(0, 300), status: r.status, mime: r.mimeType });
    } else if (m === "Network.loadingFinished") {
      const item = reqs.get(p.requestId);
      reqs.delete(p.requestId);
      if (item && entryEpoch && res.requests.length < 5000) res.requests.push(Object.assign(item, { bytes: Math.round(p.encodedDataLength || 0), t_ms: tms(p.timestamp) }));
    } else if (m === "Network.loadingFailed") {
      if (entryEpoch && res.requests.length < 5000) res.requests.push({ url: "(failed) " + (p.errorText || ""), failed: true, blocked: p.blockedReason, t_ms: tms(p.timestamp) });
    } else if (m === "Runtime.exceptionThrown") {
      const d = p.exceptionDetails || {};
      res.page_errors.push(String((d.exception && d.exception.description) || d.text || "exception").slice(0, 500));
    }
  }
}
async function drain() { try { takeEvents(await page.events()); } catch (_) { /* events() is optional diagnostics */ } }
async function touch(type, point) {
  await page.cdp("Input.dispatchTouchEvent", { type, touchPoints: point ? [{ x: point[0], y: point[1], id: 0 }] : [] });
}
async function evalExpr(expr) { return page.evaluate(String(expr)); }
let shotIndex = 0;
let emulateFn = null;
// Some screenshot paths reset device metrics; restore phone mode right away (no reload) and record it.
async function keepPhone() {
  if (!emulateFn) return;
  const o = await evalExpr("({sw: screen.width, sh: screen.height, dpr: devicePixelRatio})");
  if (!o || o.sw !== C.viewport.width || o.sh !== C.viewport.height || Math.abs(o.dpr - C.dpr) > 0.01) {
    await emulateFn();
    res.emulation_restored = (res.emulation_restored || 0) + 1;
  }
}
async function capture(label, action, shot) {
  await drain();
  if (C.timing && !shot) {
    res.steps.push({ label, action, t_ms: nowMs() });
  } else {
    const file = C.out + "/" + String(res.steps.length).padStart(3, "0") + "-" + label + ".png";
    await page.screenshot({ path: file });
    shotIndex++;
    await keepPhone();
    res.steps.push({ label, action, t_ms: nowMs(), screenshot: file, observed: await evalExpr("(" + C.readJs + ")()") });
  }
  await save();
}
// Optional low-rate recording: Ego exposes no screencast ack loop, so frames are sequential screenshots (fps recorded).
const rec = { on: !!C.record, count: 0, stop: false, t0: null, loop: null };
async function recordLoop() {
  await fs.mkdir(C.out + "/frames", { recursive: true });
  while (!rec.stop && rec.count < 3000) {
    const t = Date.now();
    if (rec.t0 === null) rec.t0 = t;
    await page.screenshot({ path: C.out + "/frames/" + String(rec.count).padStart(5, "0") + "_" + String(t - rec.t0).padStart(7, "0") + "ms.png" });
    rec.count++;
  }
}
let failed = null;
try {
  task = await taskSpace(C.spaceName);
  res.space_id = task.spaceId;
  res.space_ownership = task.ownership;
  await save();
  page = task.page("p1");
  const v = C.viewport;
  await page.cdp("Page.enable", {});
  await page.cdp("Runtime.enable", {});
  await page.cdp("Network.enable", {});
  async function emulate() {
    await page.cdp("Emulation.setDeviceMetricsOverride", { width: v.width, height: v.height, deviceScaleFactor: C.dpr, mobile: true,
      screenWidth: v.width, screenHeight: v.height });
    await page.cdp("Emulation.setUserAgentOverride", { userAgent: C.userAgent });
    await page.cdp("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
    await page.cdp("Emulation.setEmitTouchEventsForMouse", { enabled: true, configuration: "mobile" });
  }
  async function phoneOk() {
    // screen.* is the emulated device; innerWidth may legitimately grow when a page zooms out to fit wide content.
    const o = await evalExpr("({sw: screen.width, sh: screen.height, w: innerWidth, h: innerHeight, dpr: devicePixelRatio, tp: navigator.maxTouchPoints})");
    res.emulation_observed = o;
    return o && o.sw === v.width && o.sh === v.height && Math.abs(o.dpr - C.dpr) < 0.01 && o.tp > 0;
  }
  await emulate();
  emulateFn = emulate;
  // Verify phone mode on a blank document BEFORE the game starts (and before any timed navigation).
  await page.goto("about:blank");
  if (!(await phoneOk())) {
    await emulate();
    res.emulation_reapplied = true;
    if (!(await phoneOk())) throw new Error("phone emulation not applied: page is " + JSON.stringify(res.emulation_observed) + ", wanted " + JSON.stringify(v) + " dpr " + C.dpr);
  }
  await page.cdp("Page.addScriptToEvaluateOnNewDocument", { source: "(" + C.observerJs + ")()" });
  if (plan.init_js) await page.cdp("Page.addScriptToEvaluateOnNewDocument", { source: String(plan.init_js) });
  if (plan.block_urls) await page.cdp("Network.setBlockedURLs", { urls: plan.block_urls.map(String) });
  const net = plan.network;
  if (net) await page.cdp("Network.emulateNetworkConditions", { offline: false, latency: net.latency_ms, downloadThroughput: net.download_kbps * 1000 / 8, uploadThroughput: net.upload_kbps * 1000 / 8 });
  res.network_applied = net || null;
  if ((plan.cache || "cold") === "warm") {
    await page.cdp("Network.setCacheDisabled", { cacheDisabled: false });
    await page.goto(C.url);
    if (plan.warmup_js) await page.waitForFunction(String(plan.warmup_js), undefined, { timeout: 120000 });
    res.warmup_done = true;
  } else {
    await page.cdp("Network.setCacheDisabled", { cacheDisabled: true });
  }
  res.cache_disabled = (plan.cache || "cold") === "cold";
  await drain();
  reqs.clear();
  entryEpoch = Date.now();
  res.entry_epoch = entryEpoch / 1000;
  if (C.timing) await page.cdp("Page.navigate", { url: C.url }); // timing: do not wait for 'load'
  else await page.goto(C.url);
  // Untimed runs: if the browser reset the emulation on navigation, set it again and reload once; still wrong -> stop.
  if (!C.timing && !(await phoneOk())) {
    await emulate();
    res.emulation_reapplied = true;
    await page.reload();
    if (!(await phoneOk())) throw new Error("phone emulation lost after navigation: " + JSON.stringify(res.emulation_observed));
  }
  if (rec.on) rec.loop = recordLoop();
  if (!C.timing) await capture("initial", { type: "navigate" }, true);
  for (const action of plan.actions || []) {
    const kind = action.type;
    if (kind === "tap") {
      let pt = [action.x, action.y];
      if ("selector" in action) {
        const box = await page.evaluate((sel) => {
          const all = document.querySelectorAll(sel);
          if (all.length !== 1) return { count: all.length };
          const r = all[0].getBoundingClientRect();
          return { count: 1, x: r.x + r.width / 2, y: r.y + r.height / 2 };
        }, action.selector);
        if (!box || box.count !== 1) throw new Error("Tap target must be unique: " + action.selector + " matched " + (box && box.count));
        pt = [box.x, box.y];
      }
      await touch("touchStart", pt);
      await touch("touchEnd", null);
    } else if (kind === "drag" || kind === "cancel") {
      await touch("touchStart", action.points[0]);
      for (const p of action.points.slice(1)) await touch("touchMove", p);
      await touch(kind === "cancel" ? "touchCancel" : "touchEnd", null);
    } else if (kind === "wait") {
      await page.waitForTimeout(action.ms || 0);
    } else if (kind === "assert_text") {
      const got = await page.evaluate((sel) => { const n = document.querySelectorAll(sel); return n.length === 1 ? n[0].textContent.trim() : null; }, action.selector);
      if (got !== action.equals) throw new Error("assert_text " + action.selector + ": expected " + JSON.stringify(action.equals) + ", got " + JSON.stringify(got));
    } else if (kind === "mark") {
      const deadline = Date.now() + (action.timeout_ms || 30000);
      for (;;) {
        let ok = false;
        try { ok = !!(await evalExpr(action.wait_js)); } catch (_) { ok = false; }
        if (ok) { res.marks[action.name] = nowMs(); break; }
        if (Date.now() > deadline) throw new Error("mark " + action.name + " not reached within " + (action.timeout_ms || 30000) + " ms");
        await page.waitForTimeout(action.poll_ms || 30);
      }
    } else if (kind === "background") {
      const from = nowMs();
      const other = await task.newPage();
      let method = "tab_switch";
      await other.cdp("Page.bringToFront", {});
      await other.waitForTimeout(Math.min(300, action.ms));
      let state = await evalExpr("document.visibilityState");
      if (state !== "hidden") { await evalExpr("(" + C.hideJs + ")()"); method = "emulated_visibility"; state = await evalExpr("document.visibilityState"); }
      await other.waitForTimeout(Math.max(0, action.ms - 300));
      if (method === "emulated_visibility") await evalExpr("(" + C.showJs + ")()");
      await other.close();
      await page.cdp("Page.bringToFront", {});
      res.background.push({ from_ms: from, to_ms: nowMs(), visibility_while_away: state, method });
    } else if (kind === "unblock") {
      await page.cdp("Network.setBlockedURLs", { urls: [] });
    } else if (kind === "dump_ui") {
      const dump = await evalExpr("(" + C.uiDumpJs + ")(" + JSON.stringify({ maxNodes: action.max_nodes || 4000 }) + ")");
      if (!dump || typeof dump !== "object" || dump.error) throw new Error("dump_ui " + action.screen + " failed: " + ((dump && dump.error) || "no result"));
      const idx = String(res.steps.length).padStart(3, "0");
      Object.assign(dump, { screen: action.screen, kind: action.kind, purpose: action.purpose || "other", url: await page.url(), t_ms: nowMs(),
        producer: "chrome_touch.dump_ui", viewport: C.viewport, plan_dpr: C.dpr, screenshot: idx + "-ui-" + action.screen + ".png" });
      const file = C.out + "/" + idx + "-ui-dump-" + action.screen + ".json";
      await fs.writeFile(file, JSON.stringify(dump, null, 1) + "\n");
      res.ui_dumps.push({ screen: action.screen, kind: action.kind, path: idx + "-ui-dump-" + action.screen + ".json", nodes: (dump.nodes || []).length, errors: (dump.errors || []).length });
    }
    const shot = kind === "snapshot" || kind === "dump_ui" || !C.timing;
    await capture(kind === "dump_ui" ? "ui-" + action.screen : kind, action, shot);
  }
  // Timed runs cannot re-check during loading without disturbing it: check once at the end instead.
  if (C.timing && !(await phoneOk())) throw new Error("phone emulation lost during the timed run: " + JSON.stringify(res.emulation_observed));
  res.status = "completed_pending_business_and_visual_review";
} catch (error) {
  failed = error;
  res.status = "failed";
  res.error = String((error && error.stack) || error).slice(0, 2000);
} finally {
  rec.stop = true;
  if (rec.loop) { try { await rec.loop; } catch (_) {} }
  if (rec.on) res.recording = { frames: rec.count, method: "sequential_screenshots", fps: rec.count && entryEpoch ? Math.round(rec.count / Math.max(1, (Date.now() - entryEpoch) / 1000) * 10) / 10 : 0, dir: C.out + "/frames" };
  if (page) await drain();
  // Our own uniquely named space is always finished, also after a test failure, so failed runs do not pile up.
  // A stop because the user took control is the exception the Ego guide protects: then the space stays.
  const userControl = failed && /control|hand.?off|inactive|unassigned|EGO_TASK_SPACE_NAME_IN_USE/i.test(String(failed));
  if (task && !userControl) {
    try { await task.finish({ keep: [] }); res.space_finished = true; }
    catch (e) { res.space_finished = false; res.cleanup_error = String(e).slice(0, 500); }
  } else {
    res.space_finished = false;
    if (task) res.cleanup_error = "space kept: the run stopped because of user control";
  }
  await save();
  console.log("EGO_TOUCH_DONE " + JSON.stringify({ status: res.status, space_id: res.space_id, space_finished: res.space_finished }));
}

#!/usr/bin/env node
// Stand-in for `ego-browser nodejs` that drives an ordinary Chrome, Edge or Chromium (English pack 10.2.10).
//
// Why: Saul 2026-10-31 — the English Skill is used on other people's computers. The pack's packaging checks (rewarded-ad
// regression, runtime suites, chrome_touch screenshots) were written for Ego Lite and refuse to run without it. They only
// use a small part of Ego's API, so this file provides that part on top of the Chrome DevTools protocol.
//
// You normally do not call this file yourself. browser_env.py (next to it) puts a launcher named ego-browser
// (ego-browser.cmd on Windows) on PATH and sets EGO_BROWSER, then runs the pack's command; the pack's tools call the
// launcher exactly as they call Ego:
//   node cdp_browser.mjs nodejs -e "<code>"    run <code> (top-level await allowed) with globalThis.taskSpace
//   node cdp_browser.mjs nodejs < script.js    the same, script read from stdin (chrome_touch.py does this)
//   node cdp_browser.mjs --check               start the browser once, check WebGL and the frame rate, print JSON
//
// API (the subset of Ego Lite's taskSpace API that the pack's scripts use):
//   const task = await taskSpace(name);  task.page(name) (sync, lazily opened)  await task.newPage()  await task.finish()
//   page.goto(url) page.reload() page.url() page.evaluate(fnOrString, arg) page.waitForFunction(fnOrString, arg, {timeout})
//   page.waitForTimeout(ms) page.screenshot({path}) page.cdp(method, params) page.events()
// Every run starts its own headless browser with a fresh temporary profile (never the user's own profile or windows) and
// removes it at the end. The browser is driven over --remote-debugging-pipe, so it also closes when this process is
// killed (for example by a Python timeout), and no WebSocket support is needed (Node 18 or newer is enough).
// Environment: CDP_BROWSER=<browser executable> picks the browser; CDP_HEADED=1 shows the window (debugging only).
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const CALL_CAP_MS = 15000;       // Ego caps one page call at 15 s; the pack's scripts keep every call short
const COMMAND_CAP_MS = 60000;    // no single protocol command may hang a run forever
const NAV_TIMEOUT_MS = 45000;
const EVENT_BUFFER = 20000;
const PROFILE_PREFIX = 'cdp-browser-';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---------------------------------------------------------------- browser discovery
export function browserCandidates(env = process.env, platform = process.platform) {
  const list = [];
  const own = env.CDP_BROWSER || env.CHROME_PATH;
  if (own) list.push(own);
  if (platform === 'darwin') {
    for (const base of ['/Applications', path.join(os.homedir(), 'Applications')]) {
      list.push(path.join(base, 'Google Chrome.app/Contents/MacOS/Google Chrome'),
        path.join(base, 'Microsoft Edge.app/Contents/MacOS/Microsoft Edge'),
        path.join(base, 'Chromium.app/Contents/MacOS/Chromium'),
        path.join(base, 'Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'));
    }
  } else if (platform === 'win32') {
    const roots = [env.PROGRAMFILES, env['PROGRAMFILES(X86)'], env.LOCALAPPDATA, env.ProgramFiles, env['ProgramFiles(x86)']]
      .filter(Boolean);
    for (const r of [...new Set(roots)]) {
      list.push(path.join(r, 'Google', 'Chrome', 'Application', 'chrome.exe'),
        path.join(r, 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
        path.join(r, 'Chromium', 'Application', 'chrome.exe'));
    }
  } else {
    const dirs = (env.PATH || '').split(path.delimiter).filter(Boolean);
    for (const name of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'microsoft-edge',
      'microsoft-edge-stable']) for (const d of dirs) list.push(path.join(d, name));
  }
  return list;
}

export function findBrowser() {
  for (const c of browserCandidates()) {
    try { if (fs.statSync(c).isFile()) return c; } catch (_) { /* next */ }
  }
  return null;
}

function sweepOldProfiles() {
  const limit = Date.now() - 12 * 3600 * 1000;
  let names = [];
  try { names = fs.readdirSync(os.tmpdir()); } catch (_) { return; }
  for (const n of names) {
    if (!n.startsWith(PROFILE_PREFIX)) continue;
    const p = path.join(os.tmpdir(), n);
    try { if (fs.statSync(p).mtimeMs < limit) fs.rmSync(p, { recursive: true, force: true }); } catch (_) { /* in use */ }
  }
}

// ---------------------------------------------------------------- protocol over the debugging pipe
class Connection {
  constructor(child) {
    this.child = child;
    this.nextId = 0;
    this.pending = new Map();
    this.sessions = new Map();     // sessionId -> Page
    this.closed = null;
    this.stderr = '';
    let buffered = Buffer.alloc(0);
    child.stdio[4].on('data', (chunk) => {
      buffered = Buffer.concat([buffered, chunk]);
      let end;
      while ((end = buffered.indexOf(0)) >= 0) {
        const text = buffered.subarray(0, end).toString('utf8');
        buffered = buffered.subarray(end + 1);
        if (text) this.onMessage(text);
      }
    });
    child.stderr.on('data', (chunk) => { this.stderr = (this.stderr + chunk.toString('utf8')).slice(-4000); });
    const gone = (why) => this.fail(why);
    child.stdio[4].on('close', () => gone('the browser closed the debugging pipe'));
    child.on('exit', (code, signal) => gone('the browser exited (' + (signal || code) + ')'));
    child.on('error', (error) => gone('the browser could not be started: ' + error.message));
  }

  fail(why) {
    if (this.closed) return;
    this.closed = why + (this.stderr.trim() ? ': ' + this.stderr.trim().split('\n').slice(-3).join(' | ') : '');
    for (const p of this.pending.values()) p.reject(new Error(p.method + ': ' + this.closed));
    this.pending.clear();
    for (const page of this.sessions.values()) page.crashed = page.crashed || this.closed;
  }

  send(method, params = {}, sessionId = undefined, capMs = COMMAND_CAP_MS) {
    if (this.closed) return Promise.reject(new Error(method + ': ' + this.closed));
    const id = ++this.nextId;
    const message = { id, method, params: params || {} };
    if (sessionId) message.sessionId = sessionId;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        if (this.pending.delete(id)) reject(new Error(method + ': no answer from the browser within ' + capMs / 1000 + ' s'));
      }, capMs);
      this.pending.set(id, {
        method,
        resolve: (v) => { clearTimeout(timer); resolve(v); },
        reject: (e) => { clearTimeout(timer); reject(e); },
      });
      try { this.child.stdio[3].write(JSON.stringify(message) + '\0'); } catch (e) { this.pending.delete(id); clearTimeout(timer); reject(e); }
    });
  }

  onMessage(text) {
    let m;
    try { m = JSON.parse(text); } catch (_) { return; }
    if (m.id !== undefined) {
      const p = this.pending.get(m.id);
      if (!p) return;
      this.pending.delete(m.id);
      if (m.error) p.reject(new Error(p.method + ': ' + (m.error.message || JSON.stringify(m.error)) + (m.error.data ? ' (' + m.error.data + ')' : '')));
      else p.resolve(m.result || {});
      return;
    }
    if (m.method === 'Target.detachedFromTarget' && m.params) {
      const page = this.sessions.get(m.params.sessionId);
      if (page) page.crashed = page.crashed || 'the page was closed';
      return;
    }
    if (m.sessionId) {
      const page = this.sessions.get(m.sessionId);
      if (page) page.onEvent(m);
    }
  }
}

// ---------------------------------------------------------------- browser process
let browser = null;      // {child, conn, profile, exe, version}

async function launch() {
  if (browser) return browser;
  const exe = findBrowser();
  if (!exe) {
    throw new Error('没找到 Chrome、Edge 或 Chromium。装一个就能跑（Windows 自带 Edge），或者用 CDP_BROWSER=<浏览器程序的完整路径> 指定。');
  }
  sweepOldProfiles();
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), PROFILE_PREFIX));
  const args = [
    process.env.CDP_HEADED ? null : '--headless=new',
    '--remote-debugging-pipe', '--user-data-dir=' + profile, '--no-first-run', '--no-default-browser-check',
    '--disable-extensions', '--disable-sync', '--disable-background-networking', '--disable-component-update',
    '--disable-default-apps', '--disable-features=Translate,MediaRouter', '--mute-audio',
    '--autoplay-policy=no-user-gesture-required', '--disable-background-timer-throttling',
    '--disable-backgrounding-occluded-windows', '--disable-renderer-backgrounding', '--disable-hang-monitor',
    '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox', '--window-size=1280,1000', 'about:blank',
  ].filter(Boolean);
  const child = spawn(exe, args, { stdio: ['ignore', 'ignore', 'pipe', 'pipe', 'pipe'], windowsHide: true });
  const conn = new Connection(child);
  let version;
  try {
    version = await conn.send('Browser.getVersion', {}, undefined, 30000);
  } catch (error) {
    try { child.kill(); } catch (_) { /* gone */ }
    removeProfile(profile);
    throw new Error('浏览器起不来（' + exe + '）：' + error.message);
  }
  browser = { child, conn, profile, exe, version: version.product || '' };
  return browser;
}

function removeProfile(dir) {
  for (let i = 0; i < 5; i++) {
    try { fs.rmSync(dir, { recursive: true, force: true }); return; } catch (_) { /* Windows: files still locked */ }
    const until = Date.now() + 300;
    while (Date.now() < until) { /* short wait without a timer: called during exit */ }
  }
}

async function shutdown() {
  if (!browser) return;
  const { child, conn, profile } = browser;
  browser = null;
  try { await conn.send('Browser.close', {}, undefined, 3000); } catch (_) { /* already closing */ }
  const exited = new Promise((r) => { if (child.exitCode !== null || child.signalCode) r(); else child.once('exit', r); });
  await Promise.race([exited, sleep(3000)]);
  if (child.exitCode === null && !child.signalCode) {
    try { child.kill(); } catch (_) { /* gone */ }
    await Promise.race([exited, sleep(3000)]);
  }
  removeProfile(profile);
}

// ---------------------------------------------------------------- pages
let groupSeq = 0;

function evaluationError(details) {
  const ex = details.exception || {};
  const text = ex.description || details.text || 'exception in the page';
  return new Error(String(text).slice(0, 2000));
}

function valueOf(remote) {
  if (!remote) return undefined;
  if ('unserializableValue' in remote) {
    const u = remote.unserializableValue;
    if (u === 'NaN') return NaN;
    if (u === 'Infinity') return Infinity;
    if (u === '-Infinity') return -Infinity;
    if (u === '-0') return -0;
    if (/^-?\d+n$/.test(u)) return BigInt(u.slice(0, -1));
    return undefined;
  }
  return remote.value;
}

function capped(promise, ms, label) {
  let timer;
  return Promise.race([promise, new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(label + ': the call took longer than ' + ms / 1000 + ' s')), ms);
  })]).finally(() => clearTimeout(timer));
}

class Page {
  constructor(task, name, opened = null) {
    this.task = task;
    this.name = name;
    this.sessionId = null;
    this.targetId = null;
    this.crashed = null;
    this.buffer = [];
    this.waiters = new Set();
    this.lastUrl = 'about:blank';
    this.opening = opened;
  }

  async ready() {
    if (this.crashed) throw new Error('page ' + this.name + ': ' + this.crashed);
    if (this.sessionId) return this;
    if (!this.opening) this.opening = this.open();
    await this.opening;
    return this;
  }

  async open() {
    const b = await launch();
    const { targetId } = await b.conn.send('Target.createTarget', { url: 'about:blank' });
    const { sessionId } = await b.conn.send('Target.attachToTarget', { targetId, flatten: true });
    this.targetId = targetId;
    this.sessionId = sessionId;
    b.conn.sessions.set(sessionId, this);
    await this.raw('Page.enable', {});
    return this;
  }

  raw(method, params) { return browser ? browser.conn.send(method, params || {}, this.sessionId) : Promise.reject(new Error(method + ': the browser is closed')); }

  onEvent(m) {
    const { method, params } = m;
    if (method === 'Page.screencastFrame') {             // ack or Chrome stops sending frames (keepFrames relies on them)
      this.raw('Page.screencastFrameAck', { sessionId: params.sessionId }).catch(() => {});
    } else if (method === 'Page.javascriptDialogOpening') {
      this.raw('Page.handleJavaScriptDialog', { accept: true }).catch(() => {});
    } else if (method === 'Page.frameNavigated' && params && params.frame && !params.frame.parentId) {
      this.lastUrl = params.frame.url + (params.frame.urlFragment || '');
    } else if (method === 'Inspector.targetCrashed') {
      this.crashed = 'the page crashed';
    }
    if (method !== 'Page.screencastFrame') {
      this.buffer.push({ method, params });
      if (this.buffer.length > EVENT_BUFFER) this.buffer.splice(0, this.buffer.length - EVENT_BUFFER);
    }
    for (const w of [...this.waiters]) w(m);
  }

  waitEvent(predicate, ms) {
    let done, timer;
    const promise = new Promise((resolve) => {
      done = (m) => { if (!m || predicate(m)) { this.waiters.delete(done); clearTimeout(timer); resolve(!!m); } };
      this.waiters.add(done);
      timer = setTimeout(() => { this.waiters.delete(done); resolve(false); }, ms);
    });
    return { promise, cancel: () => done && done(null) };
  }

  async cdp(method, params = {}) {
    await this.ready();
    return this.raw(method, params);
  }

  async events() {
    await this.ready();
    const out = this.buffer;
    this.buffer = [];
    return out;
  }

  async goto(url, options = {}) {
    await this.ready();
    const waitUntil = options.waitUntil || 'load';
    const ms = options.timeout || NAV_TIMEOUT_MS;
    const waiting = waitUntil === 'commit' ? null
      : this.waitEvent((m) => m.method === (waitUntil === 'domcontentloaded' ? 'Page.domContentEventFired' : 'Page.loadEventFired'), ms);
    const r = await this.raw('Page.navigate', { url: String(url) });
    if (r.errorText) {
      if (waiting) waiting.cancel();
      throw new Error('goto ' + url + ': ' + r.errorText);
    }
    if (waiting) {
      if (r.loaderId) await waiting.promise;      // a slow page keeps going; the scripts poll for readiness themselves
      else waiting.cancel();                      // same-document navigation fires no load event
    }
    this.lastUrl = String(url);
    return null;
  }

  async reload(options = {}) {
    await this.ready();
    const waiting = this.waitEvent((m) => m.method === 'Page.loadEventFired', options.timeout || NAV_TIMEOUT_MS);
    await this.raw('Page.reload', { ignoreCache: false });
    await waiting.promise;
    return null;
  }

  async url() {
    try { const href = await this.evaluate('location.href'); if (typeof href === 'string') return href; } catch (_) { /* navigating */ }
    return this.lastUrl;
  }

  async evaluate(fn, arg) {
    await this.ready();
    const source = typeof fn === 'function' ? '(' + fn.toString() + ')' : String(fn);
    return capped(this.evaluateNow(source, arg), CALL_CAP_MS, 'page.evaluate');
  }

  async evaluateNow(source, arg) {
    const group = 'cdpb' + (++groupSeq);
    try {
      const r = await this.raw('Runtime.evaluate', { expression: source, objectGroup: group, awaitPromise: true,
        returnByValue: false, userGesture: true });
      if (r.exceptionDetails) throw evaluationError(r.exceptionDetails);
      const obj = r.result || {};
      if (obj.type === 'function') {               // a function, or a string that evaluates to one, is called with arg
        const c = await this.raw('Runtime.callFunctionOn', { objectId: obj.objectId, objectGroup: group,
          functionDeclaration: 'function (a) { return this(a); }', arguments: arg === undefined ? [] : [{ value: arg }],
          awaitPromise: true, returnByValue: true, userGesture: true });
        if (c.exceptionDetails) throw evaluationError(c.exceptionDetails);
        return valueOf(c.result);
      }
      if (obj.objectId) {
        const c = await this.raw('Runtime.callFunctionOn', { objectId: obj.objectId, objectGroup: group,
          functionDeclaration: 'function () { return this; }', returnByValue: true });
        if (c.exceptionDetails) throw evaluationError(c.exceptionDetails);
        return valueOf(c.result);
      }
      return valueOf(obj);
    } finally {
      this.raw('Runtime.releaseObjectGroup', { objectGroup: group }).catch(() => {});
    }
  }

  async waitForFunction(fn, arg, options = {}) {
    const ms = (options && options.timeout) || 30000;
    const every = typeof (options && options.polling) === 'number' ? options.polling : 100;
    const t0 = Date.now();
    let last = null;
    while (Date.now() - t0 < ms) {
      try {
        const v = await this.evaluate(fn, arg);
        if (v) return v;
      } catch (e) { last = e; if (this.crashed) throw e; }
      await sleep(every);
    }
    throw new Error('waitForFunction: not true within ' + ms / 1000 + ' s' + (last ? ' (last error: ' + last.message + ')' : ''));
  }

  async waitForTimeout(ms) { await sleep(Number(ms) || 0); }

  async screenshot(options = {}) {
    await this.ready();
    const r = await this.raw('Page.captureScreenshot', { format: 'png' });
    const data = Buffer.from(r.data || '', 'base64');
    if (options.path) {
      fs.mkdirSync(path.dirname(path.resolve(String(options.path))), { recursive: true });
      fs.writeFileSync(String(options.path), data);
    }
    return data;
  }

  async close() {
    if (!this.targetId || !browser) return;
    try { await browser.conn.send('Target.closeTarget', { targetId: this.targetId }, undefined, 5000); } catch (_) { /* closed */ }
    browser && browser.conn.sessions.delete(this.sessionId);
    this.crashed = this.crashed || 'the page was closed';
  }
}

class Task {
  constructor(name) { this.name = name; this.pages = new Map(); this.extra = []; this.finished = false; }
  page(name = 'p1') {
    if (!this.pages.has(name)) this.pages.set(name, new Page(this, name));
    return this.pages.get(name);
  }
  async newPage() {
    const p = new Page(this, 'extra' + (this.extra.length + 1));
    this.extra.push(p);
    await p.ready();
    return p;
  }
  async finish(options = {}) {
    const keep = new Set((options && options.keep) || []);
    for (const [name, p] of this.pages) if (!keep.has(name) && !keep.has(p)) await p.close();
    for (const p of this.extra) if (!keep.has(p)) await p.close();
    this.finished = true;
    tasks.delete(this.name);
    return { finished: true };
  }
}

const tasks = new Map();
export async function taskSpace(name = 'default') {
  await launch();
  const key = String(name);
  if (!tasks.has(key)) tasks.set(key, new Task(key));
  return tasks.get(key);
}

// ---------------------------------------------------------------- command line
async function readStdin() {
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  return Buffer.concat(chunks).toString('utf8');
}

async function runCode(code) {
  const AsyncFunction = (async function () {}).constructor;
  const require = createRequire(path.join(process.cwd(), 'cdp-browser-entry.js'));
  await new AsyncFunction('require', code)(require);
}

async function check() {
  const out = { ok: false, browser: findBrowser(), headless: !process.env.CDP_HEADED, node: process.version };
  try {
    const b = await launch();
    out.version = b.version;
    const task = await taskSpace('cdp-browser-check');
    const page = task.page('p1');
    await page.goto('data:text/html,<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">'
      + '<title>check</title><canvas id=c></canvas>');
    await page.cdp('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
    const gl = await page.evaluate(() => {
      const c = document.getElementById('c');
      const g = c.getContext('webgl') || c.getContext('experimental-webgl');
      if (!g) return { webgl: false };
      const info = g.getExtension('WEBGL_debug_renderer_info');
      return { webgl: true, renderer: String(info ? g.getParameter(info.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER)) };
    });
    Object.assign(out, gl);
    out.width = await page.evaluate('innerWidth');
    out.fps = await page.evaluate(() => new Promise((done) => {
      let n = 0; const t0 = performance.now();
      const f = () => { n++; if (performance.now() - t0 < 1000) requestAnimationFrame(f); else done(Math.round(n * 1000 / (performance.now() - t0))); };
      requestAnimationFrame(f);
    }));
    await task.finish({ keep: [] });
    out.ok = out.webgl === true && out.width === 390;
    if (!out.webgl) out.problem = '这个浏览器在后台模式下用不了 WebGL，游戏画不出来：换 Chrome 或 Edge 试试，或者设 CDP_HEADED=1';
  } catch (e) {
    out.problem = String(e && e.message || e);
  }
  return out;
}

async function main() {
  const argv = process.argv.slice(2);
  let exit = 0;
  const stop = (code) => { shutdown().finally(() => process.exit(code)); };
  process.on('SIGINT', () => stop(130));
  process.on('SIGTERM', () => stop(143));
  // A script that calls process.exit() itself skips the shutdown above: never leave a browser or a profile behind.
  process.on('exit', () => {
    if (!browser) return;
    try { browser.child.kill(); } catch (_) { /* gone */ }
    removeProfile(browser.profile);
  });
  if (argv[0] === '--check') {
    const r = await check();
    await shutdown();
    console.log(JSON.stringify(r));
    process.exit(r.ok ? 0 : 3);
  }
  if (argv[0] !== 'nodejs') {
    console.log('cdp_browser.mjs: Chrome/Edge/Chromium stand-in for `ego-browser nodejs` (English pack 10.2.10).\n'
      + 'Usage: node cdp_browser.mjs nodejs -e "<code>" | node cdp_browser.mjs nodejs < script.js | node cdp_browser.mjs --check');
    process.exit(argv.length && !['--help', '-h', '--version', 'skill'].includes(argv[0]) ? 2 : 0);
  }
  globalThis.taskSpace = taskSpace;
  const i = argv.indexOf('-e');
  const code = i >= 0 ? (argv[i + 1] || '') : await readStdin();
  try {
    await runCode(code);
  } catch (e) {
    console.error(e && e.stack || String(e));
    exit = 1;
  } finally {
    await shutdown();
  }
  process.exit(exit);
}

const invoked = process.argv[1] && (path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
  || /cdp_browser\.mjs$/.test(process.argv[1]));
if (invoked) main();

// R4N3 (补查2 第 1 组 1b): one engine adapter for ui_dump.js and the page probes.
// 火箭三消 / 弹球传奇 dumps failed with "cc.director not found" (3.x keeps cc in a module until System.import('cc')),
// 奔跑吧巨人 failed on node.convertToWorldSpaceAR (a 2.x call on a 3.x node). adapt(win) finds the engine, says
// which API it has, and gives size/toWorld that work on both; when the engine is not up it returns
// {ready: false, retry: true, reason: '引擎还没起来'} instead of throwing. waitReady(win) retries until the scene is up.
// ui_dump.js carries a byte-identical copy of adapt() between the ENGINE-ADAPTER markers (test_r4n3_engine_adapter.js
// checks it), because it is evaluated in the page as one function. Probes load this file and call adapt / waitReady.
(function (root) {
  // ENGINE-ADAPTER-BEGIN
  const adapt = (win) => {
    const cc = (win && (win.cc || win.__tiktokKitCc)) || (typeof globalThis !== 'undefined' && globalThis.cc) || null;
    const notReady = (why) => ({ ready: false, retry: true, reason: '引擎还没起来：' + why });
    if (!cc) return notReady('页面里还没有 cc' + (win && win.System && win.System.import ? '（3.x 要先 System.import(\'cc\')）' : ''));
    if (!cc.director || typeof cc.director.getScene !== 'function') return notReady('cc.director 还没有');
    let scene = null;
    try { scene = cc.director.getScene(); } catch (e) { return notReady('getScene() 出错 ' + e); }
    if (!scene) return notReady('还没有场景');
    const v3 = String(cc.ENGINE_VERSION || '').charAt(0) === '3';
    const api = (cc.UITransform || v3) ? '3.x' : '2.x';
    const transformOf = (node) => { try { return cc.UITransform && node.getComponent ? node.getComponent(cc.UITransform) : null; } catch (e) { return null; } };
    const size = (node) => {
      const ut = transformOf(node);
      if (ut) return { w: ut.contentSize.width, h: ut.contentSize.height, ax: ut.anchorPoint.x, ay: ut.anchorPoint.y, ut };
      if (api === '3.x') return null;
      return { w: node.width, h: node.height, ax: node.anchorX, ay: node.anchorY };
    };
    const toWorld = (node, x, y) => {
      const ut = transformOf(node);
      if (ut && ut.convertToWorldSpaceAR) { const v = ut.convertToWorldSpaceAR(cc.Vec3 ? new cc.Vec3(x, y, 0) : { x, y, z: 0 }); return [v.x, v.y]; }
      if (typeof node.convertToWorldSpaceAR === 'function') { const v = node.convertToWorldSpaceAR(cc.v2 ? cc.v2(x, y) : { x, y }); return [v.x, v.y]; }
      return null;
    };
    return { ready: true, cc, api, scene, size, toWorld, engine: cc.ENGINE_VERSION || '' };
  };
  // ENGINE-ADAPTER-END
  const waitReady = (win, opts) => {
    opts = opts || {};
    const timeout = opts.timeoutMs == null ? 15000 : opts.timeoutMs, every = opts.everyMs || 250;
    const t0 = Date.now();
    let importing = null;
    return new Promise((resolve) => {
      const tick = () => {
        const r = adapt(win);
        if (r.ready) return resolve(r);
        if (!importing && win && !win.cc && win.System && typeof win.System.import === 'function') {
          importing = Promise.resolve().then(() => win.System.import('cc')).then((m) => { win.__tiktokKitCc = m; }, () => {});
        }
        if (Date.now() - t0 >= timeout) return resolve(Object.assign(r, { retry: false, waitedMs: Date.now() - t0 }));
        setTimeout(tick, every);
      };
      tick();
    });
  };
  const api = { adapt, waitReady };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.__ccEngineAdapter = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : null));

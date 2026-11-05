// R4O4 (R4N3 没做完的, 补查2 第 1 组 1b): the engine adapter for the runtime_regression page probes.
// 火箭三消 / 弹球传奇 probes saw no cc.director (3.x keeps cc in a module until System.import('cc')); 奔跑吧巨人 3.x hit
// node.convertToWorldSpaceAR (a 2.x call on a 3.x node). lib.mjs, geom.mjs, phone.mjs and the suites read the scene and
// convert node points through adapt(win) instead of their own cc.director.getScene() / convertToWorldSpaceAR lines.
// The block between the ENGINE-ADAPTER markers is a byte-identical copy of remake-core/scripts/engine_adapter.js
// (cocos-game-check is installed without remake-core next to it on some machines, so it is copied, not imported);
// test_r4o4_probe_adapter.py checks the copies. In the page it is window.__ccAdapt(window):
//   {ready:false, retry:true, reason:'引擎还没起来：…'} until a scene exists, never a throw.
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

export { adapt };
export const NOT_READY = '引擎还没起来';
export const ADAPT_SRC = adapt.toString();
// 3.x page without a global cc: start System.import('cc') once (like engine_adapter.js waitReady); the next poll sees
// window.__tiktokKitCc.
const IMPORT_CC = "if(!window.cc&&!window.__tiktokKitCc&&!window.__ccImporting&&window.System&&typeof System.import==='function'){"
  + "window.__ccImporting=1;Promise.resolve().then(function(){return System.import('cc');}).then(function(m){window.__tiktokKitCc=m;},function(){window.__ccImporting=0;});}";
// Installs window.__ccAdapt in the page (every call: a reload drops it) and runs fn there with arg a (JSON-embedded,
// so it works with every page.evaluate that takes a string). fn may use window.__ccAdapt(window).
export const INSTALL = 'window.__ccAdapt=(' + ADAPT_SRC + ');' + IMPORT_CC;
export const inPage = (fn, a) => '(function(){' + INSTALL + 'return (' + (typeof fn === 'function' ? fn.toString() : fn) + ')('
  + (a === undefined ? '' : JSON.stringify(a)) + ');})()';
// Same for adapter code that is a function BODY (adapter.ready / home / locate): new Function(code)() after install.
export const bodyInPage = (code) => '(function(){' + INSTALL + 'try { return new Function(' + JSON.stringify(String(code)) + ')(); }'
  + ' catch (e) { return { adapterError: String(e && e.message || e).slice(0, 300) }; }})()';
// Default readiness for waitFor / boot: a function body that is true once the scene is up (2.x and 3.x).
export const READY = 'var E = window.__ccAdapt(window); return E.ready === true ? true : { ok: false, notReady: E.reason };';

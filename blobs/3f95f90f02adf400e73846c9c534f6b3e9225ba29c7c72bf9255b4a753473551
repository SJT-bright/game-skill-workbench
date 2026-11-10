// Run through the official Ego Lite CLI on a private loopback origin.
const C = globalThis.CFG;
const L = await import(C.lib);
const {wrapEgoPage} = await import(new URL('../ego_test_page.mjs', C.lib));
const task = await taskSpace(C.space);
const page = wrapEgoPage(task.page('p1'));
let evidence, failure;

async function waitFor(code, timeoutMs, message) {
  const end = Date.now() + timeoutMs;
  while (Date.now() < end) {
    if (await L.adapterCall(page, code) === true) return;
    const errors = await page.evaluate(() => window.__migrationErrors);
    if (errors?.length) throw new Error(errors.slice(0, 3).join(' / '));
    await L.sleep(300);
  }
  throw new Error(message);
}

try {
  await L.viewport(page, 390, 844, 2, true);
  await page.cdp('Page.addScriptToEvaluateOnNewDocument', {source: [
    'window.__migrationErrors=[];',
    'addEventListener("error", e => { if (e.message) window.__migrationErrors.push(String(e.message)); });',
    'addEventListener("unhandledrejection", e => window.__migrationErrors.push(String(e.reason)));',
  ].join('\n')});
  await page.goto(L.url());
  const node = name => 'cc.find(' + JSON.stringify(name) + ', cc.director.getScene())';
  const home = 'return !!(' + node(C.play) + ')?.activeInHierarchy;';
  const enter = C.ready_node ?
    'return !!(' + node(C.ready_node) + ')?.activeInHierarchy;' :
    'return cc.director.getScene()?.name === ' + JSON.stringify(C.ready_scene) + ';';
  await waitFor(home, 24000, '首页 PLAY 节点未就绪');
  const point = await L.locate(page, 'return ' + node(C.play) + ';');
  if (!point?.onCanvas) throw new Error('PLAY 节点未落在实际画布触点内');
  if (await L.adapterCall(page, enter) === true) throw new Error('开局目标在点击前已出现，请选择可区分的游戏状态');
  await L.touchTap(page, point.x, point.y);
  await waitFor(enter, 15000, '真实点击后未进入配置的玩法状态');
  const state = await page.evaluate(() => ({
    engine: window.cc?.ENGINE_VERSION, scene: window.cc?.director.getScene()?.name,
    errors: window.__migrationErrors
  }));
  if (state.errors?.length) throw new Error(state.errors.slice(0, 3).join(' / '));
  evidence = {browser_route:'ego_taskspace', input_transport:'ego_page_cdp', session_id:task.spaceId,
              home:true, entered:true, engine:state.engine, scene:state.scene};
} catch (error) {
  failure = error;
}
if (failure && /control|hand.?off|inactive|unassigned|hard.?stop|EGO_/i.test(String(failure.code || failure))) {
  console.error('Ego space '+task.spaceId+' stopped under browser control.');
  throw failure;
}
await task.finish({keep:[]});
if ((await listTaskSpaces()).some(s => String(s.id ?? s.spaceId) === String(task.spaceId))) {
  throw new Error('未能核对本轮 Ego 空间已关闭');
}
if (failure) throw failure;
console.log('MIGRATION_EGO '+JSON.stringify({...evidence,space_finished:true}));

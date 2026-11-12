# 弹窗、遮罩与输入锁的实例归属

适用：设计或接入弹窗、加载层、侧栏、暂停页，以及修改它们共用的 UI 管理器、异步加载或关闭逻辑。此类问题可能跨 Android/iOS：画面仍在刷新，但残留的透明节点或未释放的输入令牌截住操作。不能仅凭一张静止截图判断死循环或平台故障。

## 制作时确定归属

每次打开是一段有身份的会话，经过 `opening → visible → closed`。在发起异步请求前登记会话；单例页面在 opening 和 visible 都复用同一请求/实例，不能等资源回来后才防重。需要堆叠时显式允许多实例，每层保持自己的容器、遮罩、输入/暂停令牌和关闭函数。

遮罩属于实际实例，关闭时按保存的对象引用或会话容器释放。`getChildByName('blackBg'+类型名)` 只能找到一个同名节点，不能证明找到本层。固定毫秒数防抖、只隐藏按钮、全局 `inputEnabled=true` 或扫描删除全部遮罩，都不能替代归属；后两种还可能破坏仍在使用的另一层。

关闭先撤销会话，使迟到回调失效，再立即停用输入拦截，最后释放节点与本会话令牌。正常关闭、取消、加载失败、超时、返回首页、切场、closeAll 和 onDestroy 都走同一幂等清理。资源缓存与弹窗实例分开管理；过期资源完成可以留缓存，不能重新挂旧窗口。异常清理不应跳过其余令牌释放。父页销毁时要清理所属子会话；不能只销毁子节点而保留其业务锁。

可复用 [ModalOwner.js](../assets/common-ui/ModalOwner.js)，也可在现有管理器实现同等语义，不强制旧游戏更换 SDK。该参考件要求同一 owner 管理共用输入层，弹窗的独立会话容器互为兄弟节点；跨会话嵌套会拒绝，子确认窗也用独立兄弟容器。挂载后不得擅自改变会话容器的父子关系。由工程注入 Cocos 2.x/3.x 的有效性和销毁接口，owner 所属组件销毁时调用 `dispose()`。

```js
const owner = new ModalOwner({
  isAlive: () => sceneIsAlive(),
  disposeNode: node => node.destroy()
});
async function openShop() {
  const request = owner.begin('shop');
  if (!request.created) return request.session;
  const session = request.session;
  try {
    session.hold(acquireInputToken()); // acquire 返回本令牌的 release；不是全局解锁
    const ui = await createShopContainer(); // 独立 root 下包含 view、可选 blocker
    if (session.mount(ui.root, ui.view, ui.blocker)) {
      bindClose(ui.view, () => session.close());
    } // 已取消的迟到结果由 mount 释放，不接入当前界面
  } catch (error) {
    session.close();
    reportLoadError(error);
  }
  return session;
}
```

`sceneIsAlive / acquireInputToken / createShopContainer / bindClose / reportLoadError` 由工程实现。加载失败时必须有原设计的可操作出口；错误日志不能代替恢复。新 UI 仍先走美工 Skill，本合同只约束行为和生命周期。

## 定点验收与增量范围

新制作、首次完整接入时，按实际页面盘点全部模态路线，在现有页面注册表记录页面与打开/关闭入口，并把真实观察与动作登记到原 runtime adapter 的 `modal_lifecycle`，见[运行适配](../../cocos-game-check/package-check/references/modal-lifecycle.md)。每条路线至少测正常、连续打开、逐层关闭和不刷新重开；异步路线额外覆盖真实慢加载窗口，有真实取消/切场出口时覆盖等待期间退出和迟到完成。加载失败、场景销毁及多种令牌并存的清理按本作实际能力定点补充，不能以单次正常打开代替。

改共享管理器时覆盖它的不同关闭/堆叠机制代表路线，并保留所有消费者的依赖关系；只改图片、不改行为时复用行为证据。旧证据未覆盖这类顺序时列为缺口，不冒充通过，也不自动跑无关关卡、美工、经济或全量矩阵。单个按钮有画面变化、控制器方法调用成功、ZIP 校验通过都不证明输入锁已释放。

预检 `scripts/audit_modal_ownership.py --project 工程 --out 报告.json` 只定位已知按名称销毁遮罩写法；它使用词法标记，不是完整数据流或生命周期证明。无风险输出仍为 `passed:false / source_only`。源码缺失、无法解析与实际操作未覆盖须如实保留。运行证据记录真实节点实例 ID、点击命中和清理结果；浏览器 Native 宿主结果与真机、真实平台广告结果分别写明。真机已有异常时，修复后在对应系统补原复现链，不能以本地通过替代。

## 诊断顺序

先记录引擎帧数、暂停状态、触摸命中对象、活动窗口和遮罩的实例 ID 与层级、未完成请求及输入/暂停令牌。帧数增长但触摸命中残留遮罩，优先查会话归属；无节点残留但锁未归零，查令牌释放；帧数不动再查异常/主线程阻塞。使用冷加载与实际连续触摸复现，用只移除已确认孤儿的诊断副本验证因果，不把运行时强制清罩当正式修复。

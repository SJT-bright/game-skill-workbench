# 弹窗、遮罩与输入锁的实例归属

适用：设计或修改实际拦截输入的弹窗、加载层、暂停页及共用 UI 管理器。仅替换图片、文字或不拦截输入的普通侧栏时，沿用原行为证据。此类问题可能跨 Android/iOS：画面仍在刷新，但残留的透明节点或未释放的输入令牌截住操作。不能仅凭一张静止截图判断死循环或平台故障。

## 制作时确定归属

每次打开是一段有身份的会话，经过 `opening → visible → closed`。在发起异步请求前登记会话；单例页面在 opening 和 visible 都复用同一请求/实例，不能等资源回来后才防重。需要堆叠时显式允许多实例，每层保持自己的容器、遮罩、输入/暂停令牌和关闭函数。

遮罩属于实际实例，关闭时按保存的对象引用或会话容器释放。`getChildByName('blackBg'+类型名)` 只能找到一个同名节点，不能证明找到本层。固定毫秒数防抖、只隐藏按钮、全局 `inputEnabled=true` 或扫描删除全部遮罩，都不能替代归属；后两种还可能破坏仍在使用的另一层。

关闭先撤销会话，使迟到回调失效，再立即停用输入拦截，最后释放节点与本会话令牌。正常关闭、取消、加载失败、超时、返回首页、切场、closeAll 和 onDestroy 都走同一幂等清理。资源缓存与弹窗实例分开管理；过期资源完成可以留缓存，不能重新挂旧窗口。异常清理不应跳过其余令牌释放。父页销毁时要清理所属子会话；不能只销毁子节点而保留其业务锁。

优先在现有 UI 管理器落实同等语义，复用已有 RunSession、输入锁和暂停令牌，不能另建一套全局暂停/输入开关。新项目缺少对应管理时可选用 [ModalOwner.js](../assets/common-ui/ModalOwner.js)，不强制旧游戏换 SDK，也不自动复制到游戏。参考件的共用输入层由同一 owner 管理，独立会话容器互为兄弟；跨会话嵌套会拒绝。挂载后不得改变这些容器的父子关系；现有框架支持嵌套时保留它的依赖清理，不强行改成此参考件。由工程注入 Cocos 2.x/3.x 的有效性和销毁接口，所属组件销毁时调用 `dispose()`。

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

新制作把防重和清理落实在公共管理器，首件的真实打开/关闭中加入连续操作与不刷新重开。同一管理器、加载方式和关闭清理完全相同的页面共用一个机制代表件；单例/堆叠、同步/异步、不同退出机制分别选代表。页面覆盖仍按原逐按钮规则执行，生命周期不逐页面重复乘算。已有实际用例覆盖同样的操作顺序且依赖未变时直接复用，不再叠加专项。

新机制首件、相关修改或卡住排查才显式使用[独立 modal_lifecycle 专项](../../cocos-game-check/package-check/references/modal-lifecycle.md)，把本次代表路线放在工程专项适配文件，不修改原广告适配器或通用套件。异步机制额外覆盖真实慢加载窗口，有实际等待中取消/离场入口时覆盖迟到完成；同步或预加载机制不跑慢加载。异常、场景销毁和多令牌清理并入本作已有对应用例，证据明确关联，不能把未执行写成已通过。

改共享管理器时覆盖它的不同关闭/堆叠机制代表路线，并保留所有消费者的依赖关系；只改图片、不改行为时复用行为证据。旧证据未覆盖这类顺序时列为缺口，不冒充通过，也不自动跑无关关卡、美工、经济或全量矩阵。单个按钮有画面变化、控制器方法调用成功、ZIP 校验通过都不证明输入锁已释放。

源码扫描 `scripts/audit_modal_ownership.py --project 工程 --out 报告.json` 只在排查相关管理器或已知卡住时按需执行，不加入默认 preflight、CI 或出包。它定位已知按名称销毁遮罩写法，不是完整数据流或生命周期证明；无命中仍为 `passed:false / source_only`，命中先审实际归属，不直接裁定旧游戏失败。运行证据记录真实节点实例 ID、点击命中和清理结果；浏览器 Native 宿主与真机、真实广告分别记。真机已有异常时，修复后补对应系统的原复现链。

## 诊断顺序

先记录引擎帧数、暂停状态、触摸命中对象、活动窗口和遮罩的实例 ID 与层级、未完成请求及输入/暂停令牌。帧数增长但触摸命中残留遮罩，优先查会话归属；无节点残留但锁未归零，查令牌释放；帧数不动再查异常/主线程阻塞。使用冷加载与实际连续触摸复现，用只移除已确认孤儿的诊断副本验证因果，不把运行时强制清罩当正式修复。

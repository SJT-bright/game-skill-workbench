# modal_lifecycle：按需验证真实弹窗清理

制作原则见[实例归属](../../../remake-core/references/modal-input-ownership.md)。本专项位于 `package-check/optional-suites/modal-lifecycle/`，没有进入默认 `scripts/runtime_regression/suites/`；安装补丁不改变默认预检、旧套件判定、整包工具哈希和自动出包范围。

## 何时执行与如何复用

新机制首件、修改共用管理器/异步加载/关闭机制或排查卡住时使用。相同管理器、加载方式和关闭清理的页面共用一个代表件，单例/堆叠、同步/异步及不同退出机制各按实际分组；不能把实现不同的页面合成一组。原逐按钮覆盖仍执行，生命周期不逐页面乘算。已有真实用例覆盖同样顺序且依赖未变时直接关联旧证据，不再运行专项；单次按钮响应不能当作等价覆盖。

只换图片、文字、普通侧栏或重发未改包时，不触发本专项。共享检查器的对照校准和辅助件单测在 Skill 维护时做，不作为每个游戏的新增制作步骤。源码风险扫描也仅供按需诊断。

## 专项适配与运行

将本次代表件的真实动作/观察放在工程专项 JSON，**不往原广告/runtime 适配器增加新字段**。专项配置只由独立目录加载，不调整默认 writer。命令使用原运行器和原增量授权：

```sh
python3 -B <skills>/cocos-game-check/package-check/optional-suites/modal-lifecycle/run_modal_lifecycle.py \
  --package <实际Native目录> --adapter <工程>/qa/modal-lifecycle.json \
  --out <本次专项结果.json>
```

该命令只证明所选专项；结果挂入原阶段的检查记录，不当作原游戏全量通过或 writer 通用回归的替代。未运行、未登记或覆盖不足时保留缺口。当前套件按既有 `@suite` 节点调度，内部案例分别留证，不修改通用调度器。

```json
{
  "home": "return gameUI.isHomeReady() === true;",
  "modal_lifecycle": [{
    "id": "shop-manager",
    "open": {"tap": "Canvas/Home/ShopButton"},
    "close": {"tap_js": "return gameUI.topShop().closeButton;"},
    "async_open": true,
    "slow_query": "pkgms=600",
    "state_js": "return {views:gameUI.shopInstances().map(n=>n.uuid),blockers:gameUI.shopBlockers().map(n=>n.uuid)};",
    "settled_js": "return gameUI.pendingShopRequests() === 0;"
  }]
}
```

示例 `gameUI` 需替换成本作真实实现。`state_js` 枚举活动实例及孤儿遮罩的真实唯一 ID，不能只读管理器登记的窗口，也不能填固定空数组/布尔。默认单例；实际允许堆叠时显式 `allow_multiple:true`，关闭动作命中当前顶层。`prepare` 只准备真实可达状态和观察钩子，不能调用打开/关闭方法代替玩家操作。

`async_open` 必须据实际实现填写。同步/预加载机制为 false，跑 normal/burst；异步为 true，增加 slow_burst，`slow_query` 延迟实际使用的分包/请求。慢窗口没有实际到达时不判通过。`settled_js` 等全部相关请求及挂载/清理完成；成功后立即继续，没有固定秒数的保底等待。可选 `burst_gap_ms` 默认 180ms 是复现点击间隔，不是每步等待；`ready_timeout_ms` 默认 10 秒为失败上限，正常不会等满。

有实际等待中可触摸的取消/离场控件时填 `cancel`，才跑 cancel_late。没有则不增加玩家功能；现有场景销毁、异常和外部取消验证挂原对应用例，不复制整套矩阵。支持 `query/device`，默认 iphone14 仅是坐标条件。

通过要求：真实触摸打开和逐层关闭，最终窗口/本机制遮罩清零；同一运行实例不刷新重开并再关闭仍干净。每次重开等真实异步结束，不能过早写通过，也不能 JS 强制 destroy 代替关闭。轨迹保留实例 ID、触摸命中和阶段，写入 `modal-lifecycle-trace.json`。宿主、辅助件离线验证与安卓/iOS 真机结果分别标明。

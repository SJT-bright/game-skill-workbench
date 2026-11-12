# modal_lifecycle：真实触摸与弹窗清理

设计和制作规则见[实例归属](../../../remake-core/references/modal-input-ownership.md)。在工程原有 runtime adapter 加 `modal_lifecycle` 数组后，现有运行器和 writer 将其列为适用套件。完整制作应登记实际模态路线；没有此字段只表示尚未登记，不能声称通过。此项不自动扫描、修改或重测其他游戏。

每条路线包括以下字段，动作与 `phone.mjs` 相同，JS 为函数体。下例的 `gameUI` 仅说明接口形状，必须换成本作真实实现，不能给空数组、固定布尔或人工写入的测试状态来通过。

```json
{
  "home": "return gameUI.isHomeReady() === true;",
  "modal_lifecycle": [{
    "id": "shop",
    "open": {"tap": "Canvas/Home/ShopButton"},
    "close": {"tap_js": "return gameUI.topShop().closeButton;"},
    "async_open": true,
    "slow_query": "pkgms=600",
    "state_js": "return {views:gameUI.shopInstances().map(n=>n.uuid),blockers:gameUI.shopBlockers().map(n=>n.uuid)};",
    "settled_js": "return gameUI.pendingShopRequests() === 0;",
    "burst_gap_ms": 180,
    "ready_timeout_ms": 10000
  }]
}
```

- `state_js` 返回当前活动的真实 view/blocker 实例 ID 数组；包括孤儿遮罩，不能只遍历仍在管理器登记的窗口。名字和数量不能作为身份。默认要求单例，实际允许多层时显式 `allow_multiple:true`；关闭动作必须命中当前最上层。
- `async_open` 必须明确。同步或已预加载路线设 false，仍跑 normal/burst；真实异步设 true，额外跑 slow_burst。`slow_query` 要控制实际使用的分包、资源或业务请求，例如本宿主的 `pkgms`；浏览器本地缓存不能掩盖冷路径。第二次触摸前若第一个窗口已显示，慢加载窗口没有覆盖，判未通过，先修适配/故障注入。不能为了通过把异步路线改标同步。
- `settled_js` 观察与该路线有关的全部请求、实例挂载与清理完成；不能只看首个窗口可见。每次打开，包括同一实例内的重开，都等实际完成后核清理。无异步时读取本作实际闲置状态。`prepare` 只准备真实可达状态或只读观察钩子，不能直接调用打开/关闭方法来替代玩家操作。
- 有等待中实际可触摸的取消或离场入口时填 `cancel`，运行 cancel_late。没有该控件就记录该路径不适用，不为测试增加玩家功能；已有场景销毁/外部取消路径需用工程已有定点用例覆盖。此套件不证明所有广告、异常恢复或场景切换。
- 支持 `query / device`；默认 iphone14。手机尺寸是坐标条件，不是 iOS/Android 真机结果。每条 case 的输入与实例状态写入 `modal-lifecycle-trace.json`，结果写实际 case ID `路线/normal|burst|slow_burst|cancel_late`。

通过要求：真实打开和关闭改变实际实例数，允许堆叠时每次关闭恰好少一层，最终窗口与本路线的所有遮罩均清零；同一运行实例不刷新重开、再关闭仍无残留。按真实点击后的结果判定，不能拿 JS 手动 destroy 作为通过路径。

使用原命令 `runtime_regression.py run --package <Native目录> --adapter <原adapter.json> --suites modal_lifecycle`，并遵守原增量 scope。当前调度把本套件作为一个 `@suite` 原子节点；内部案例分别留证。为了保留原套件规则身份，本次没有改通用调度器和旧判定。局部返工需在项目现有依赖计划里明确受影响路线及有效旧证据；不要用临时删 adapter 路线伪造完整覆盖。原工具报告的未覆盖项按实际保留。

检查器维护时至少校准一个已知失败链和一个正确对照，包含正常单次操作，确保既会拒绝原问题，也能放行正确实现。辅助件单元测试与受控离线调度模拟不等于 Native 游戏结果。
